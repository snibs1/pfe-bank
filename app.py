from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from config import Config
from models import db, Simulation
import joblib
import requests
from sqlalchemy import func, text
from urllib.parse import urljoin
import numpy as np
import os
import random
from datetime import datetime, timedelta
import csv
from io import StringIO
from sqlalchemy import func

app = Flask(__name__)
app.config.from_object(Config)

# ربط التطبيق مع قاعدة البيانات
db.init_app(app)

# Airflow connection (from environment)
AIRFLOW_HOST = os.environ.get('AIRFLOW_HOST', 'http://localhost:8080')
AIRFLOW_USER = os.environ.get('AIRFLOW_USER', 'admin')
AIRFLOW_PASS = os.environ.get('AIRFLOW_PASS', 'admin')

def trigger_airflow_dag(dag_id='daily_loan_batch_processing', conf=None):
    """Trigger an Airflow DAG run via REST API (best-effort)."""
    try:
        api_url = urljoin(AIRFLOW_HOST, f'/api/v1/dags/{dag_id}/dagRuns')
        resp = requests.post(api_url, auth=(AIRFLOW_USER, AIRFLOW_PASS), json={'conf': conf or {}} , timeout=10)
        if resp.status_code in (200, 201):
            return True, resp.json()
        return False, resp.text
    except Exception as e:
        return False, str(e)

# --- تحميل موديلات الذكاء الاصطناعي ---
model = None
scaler = None
try:
    model_path = os.path.join(app.config['BASE_DIR'], 'loan_prediction_model.pkl')
    scaler_path = os.path.join(app.config['BASE_DIR'], 'data_scaler.pkl')
    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)
    with app.app_context():
        db.create_all()
    app.logger.info("✅ NB BANK: System Ready & AI Models Loaded")
except Exception as e:
    model = None
    scaler = None
    app.logger.error(f"❌ ML model load failed: {e}")

# --- ROUTES ---

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    user = request.form.get('username')
    pwd = request.form.get('password')
    if user == "admin" and pwd == "1234":
        return redirect(url_for('dashboard'))
    flash("Identifiants incorrects", "danger")
    return redirect(url_for('login_page'))

@app.route('/dashboard')
def dashboard():
    total_clients = Simulation.query.count()
    high_risk_count = Simulation.query.filter(Simulation.risk_score > 50).count()
    
    total_volume = db.session.query(func.sum(Simulation.loan_amount)).scalar() or 0
    total_volume_millions = total_volume / 1000000
    
    accuracy = 91.2
    recent_sims = Simulation.query.order_by(Simulation.date_added.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                         recent_sims=recent_sims,
                         total_clients=total_clients,
                         high_risk_count=high_risk_count,
                         total_volume=total_volume_millions,
                         accuracy=accuracy)

@app.route('/simulation')
def simulation():
    return render_template('simulation.html')

@app.route('/pipeline')
def pipeline():
    total_processed = Simulation.query.count()
    # جلب عدد الطلبات المنتظرة في Staging (غير معالجة)
    try:
        res = db.session.execute(text("SELECT COUNT(*) FROM staging_applications WHERE processed = FALSE"))
        staging_count = int(res.fetchone()[0])
    except Exception:
        staging_count = 0

    # عرض آخر السجلات المعالجة في الـ production
    recent_batches = Simulation.query.order_by(Simulation.date_added.desc()).limit(10).all()

    # جلب أحدث السجلات من جدول staging لعرضها في الواجهة
    try:
        staging_res = db.session.execute(text("SELECT id, client_name, cin, uploaded_at FROM staging_applications ORDER BY uploaded_at DESC LIMIT 10"))
        recent_staging = [dict(row) for row in staging_res.fetchall()]
    except Exception:
        recent_staging = []

    return render_template('pipeline.html', 
                         total_processed=total_processed,
                         staging_count=staging_count,
                         recent_batches=recent_batches,
                         recent_staging=recent_staging)

# تعديل الرابط ليتوافق مع fetch('/batch_process') في الـ HTML
@app.route('/batch_process', methods=['POST'])
def batch_process():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '' or not file.filename.endswith('.csv'):
        return jsonify({'success': False, 'error': 'Invalid file format'}), 400
    
    try:
        stream = StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_data = csv.DictReader(stream)
        inserted = 0
        staging_ids = []

        for row in csv_data:
            # insert raw row into staging_applications for Airflow ETL to pick up
            sql = text("""
                INSERT INTO staging_applications
                (client_name, cin, phone, annual_income, debt_to_income_ratio, credit_score,
                 loan_amount, loan_term, interest_rate, gender, marital_status, education_level,
                 employment_status, loan_purpose, processed, uploaded_at)
                VALUES (:client_name, :cin, :phone, :annual_income, :dti, :credit_score,
                        :loan_amount, :loan_term, :interest_rate, :gender, :marital_status,
                        :education_level, :employment_status, :loan_purpose, FALSE, NOW())
                RETURNING id
            """)

            params = {
                'client_name': row.get('client_name', 'Batch Client'),
                'cin': row.get('cin'),
                'phone': row.get('phone'),
                'annual_income': float(row.get('annual_income') or 0),
                'dti': float(row.get('debt_to_income_ratio') or 0),
                'credit_score': int(row.get('credit_score') or 0),
                'loan_amount': float(row.get('loan_amount') or 0),
                'loan_term': int(row.get('loan_term') or 36),
                'interest_rate': float(row.get('interest_rate') or 5),
                'gender': row.get('gender'),
                'marital_status': row.get('marital_status'),
                'education_level': row.get('education_level'),
                'employment_status': row.get('employment_status'),
                'loan_purpose': row.get('loan_purpose')
            }

            result = db.session.execute(sql, params)
            new_id = result.fetchone()[0]
            staging_ids.append(int(new_id))
            inserted += 1

        db.session.commit()

        # trigger airflow DAG to process the staging rows (best-effort)
        try:
            ok, info = trigger_airflow_dag(conf={'staging_ids': staging_ids})
        except Exception as e:
            ok, info = False, str(e)

        return jsonify({'success': True, 'inserted': inserted, 'staging_ids': staging_ids, 'dag_triggered': ok, 'dag_info': info})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


# Backwards-compatible endpoint used by the frontend upload widget
@app.route('/batch_upload', methods=['POST'])
def batch_upload():
    # reuse existing batch processing logic
    return batch_process()

@app.route('/predict', methods=['POST'])
def predict():
    try:
        if model is None or scaler is None:
            return jsonify({'error': 'ML model or scaler not loaded on server'}), 500
        data = request.form
        model_inputs = [
            float(data.get('annual_income', 0)),
            float(data.get('debt_to_income_ratio', 0)),
            float(data.get('credit_score', 0)),
            float(data.get('loan_amount', 0)),
            float(data.get('interest_rate', 0)),
            1 if data.get('gender') == 'Male' else 0,
            1 if data.get('marital_status') == 'Married' else 0,
            1 if data.get('education_level') == 'Graduate' else 0,
            1 if data.get('employment_status') == 'Employed' else 0,
            1 if data.get('loan_purpose') == 'Business' else 0,
            1, 0, 1
        ]

        features = np.array([model_inputs])
        if scaler.n_features_in_ > len(model_inputs):
            padding = np.zeros((1, scaler.n_features_in_ - len(model_inputs)))
            features = np.hstack([features, padding])
            
        features_scaled = scaler.transform(features)
        # model.predict_proba[:,1] is probability of class '1' (loan_paid_back = Yes)
        # In the training notebook 1 = loan paid back (good). Convert to risk of default.
        proba_paid = model.predict_proba(features_scaled)[0][1] * 100
        risk_of_default = round(100.0 - proba_paid, 2)
        final_status = 'Approved' if proba_paid >= 50 else 'Rejected'

        new_entry = Simulation(
            client_name=data.get('client_name', 'Client Inconnu'),
            cin=data.get('cin', 'N/A'),
            phone=data.get('phone', 'N/A'),
            annual_income=float(data.get('annual_income', 0)),
            credit_score=int(data.get('credit_score', 0)),
            loan_amount=float(data.get('loan_amount', 0)),
            loan_term=int(data.get('loan_term', 0)),
            interest_rate=float(data.get('interest_rate', 0)),
            risk_score=float(risk_of_default), # probability of default (0-100)
            status=final_status
        )
        
        db.session.add(new_entry)
        db.session.commit()

        reason = "Ratio d'endettement critique (>40%)" if float(data.get('debt_to_income_ratio', 0)) > 40 else "Score de crédit insuffisant"
        
        return jsonify({
            'status': final_status,
            'risk_score': risk_of_default,
            'reason': reason
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/requests')
def requests_list():
    all_clients = Simulation.query.order_by(Simulation.date_added.desc()).all()
    return render_template('requests.html', clients=all_clients)

@app.route('/test_etl', methods=['POST'])
def test_etl():
    """Manual ETL trigger endpoint for testing (runs ETL tasks directly via Airflow trigger)."""
    try:
        ok, info = trigger_airflow_dag(dag_id='daily_loan_batch_processing', conf={})
        if ok:
            return jsonify({'success': True, 'message': 'ETL DAG triggered successfully', 'details': info})
        else:
            return jsonify({'success': False, 'error': 'Failed to trigger DAG', 'details': info}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)