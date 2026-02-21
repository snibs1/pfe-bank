from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from config import Config
from models import db, Simulation
import joblib
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

# --- تحميل موديلات الذكاء الاصطناعي ---
try:
    model = joblib.load(os.path.join(app.config['BASE_DIR'], 'loan_prediction_model.pkl'))
    scaler = joblib.load(os.path.join(app.config['BASE_DIR'], 'data_scaler.pkl'))
    
    with app.app_context():
        db.create_all()
        
    print("✅ NB BANK: System Ready & AI Models Loaded")
except Exception as e:
    print(f"❌ Critical Error: {e}")

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
    # جلب عدد الطلبات المنتظرة في Staging (اختياري إيلا بغيتي تبينها)
    staging_count = 0 
    recent_batches = Simulation.query.order_by(Simulation.date_added.desc()).limit(10).all()
    
    return render_template('pipeline.html', 
                         total_processed=total_processed,
                         staging_count=staging_count,
                         recent_batches=recent_batches)

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
        processed = 0
        
        for row in csv_data:
            # تحضير المدخلات للموديل
            model_inputs = [
                float(row.get('annual_income', 0)),
                float(row.get('debt_to_income_ratio', 30)),
                float(row.get('credit_score', 0)),
                float(row.get('loan_amount', 0)),
                float(row.get('interest_rate', 5)),
                1 if row.get('gender') == 'Male' else 0,
                1 if row.get('marital_status') == 'Married' else 0,
                1 if row.get('education_level') == 'Graduate' else 0,
                1 if row.get('employment_status') == 'Employed' else 0,
                1 if row.get('loan_purpose') == 'Business' else 0,
                1, 0, 1
            ]
            
            features = np.array([model_inputs])
            if scaler.n_features_in_ > len(model_inputs):
                padding = np.zeros((1, scaler.n_features_in_ - len(model_inputs)))
                features = np.hstack([features, padding])
            
            features_scaled = scaler.transform(features)
            prediction = model.predict(features_scaled)[0]
            proba = model.predict_proba(features_scaled)[0][1] * 100
            
            # حفظ في Postgres مع تحويل numpy.float64 إلى float عادي
            new_entry = Simulation(
                client_name=row.get('client_name', 'Batch Client'),
                cin=row.get('cin', 'N/A'),
                phone=row.get('phone', 'N/A'),
                annual_income=float(row.get('annual_income', 0)),
                credit_score=int(row.get('credit_score', 0)),
                loan_amount=float(row.get('loan_amount', 0)),
                loan_term=int(row.get('loan_term', 36)),
                interest_rate=float(row.get('interest_rate', 5)),
                risk_score=float(round(proba, 2)), # تحويل ضروري لـ Postgres
                status='Approved' if prediction == 0 else 'Rejected'
            )
            db.session.add(new_entry)
            processed += 1
            
        db.session.commit()
        return jsonify({'success': True, 'message': f'Successfully processed {processed} applications'})
        
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
        prediction = model.predict(features_scaled)[0]
        proba = model.predict_proba(features_scaled)[0][1] * 100
        final_status = 'Approved' if prediction == 0 else 'Rejected'

        new_entry = Simulation(
            client_name=data.get('client_name', 'Client Inconnu'),
            cin=data.get('cin', 'N/A'),
            phone=data.get('phone', 'N/A'),
            annual_income=float(data.get('annual_income', 0)),
            credit_score=int(data.get('credit_score', 0)),
            loan_amount=float(data.get('loan_amount', 0)),
            loan_term=int(data.get('loan_term', 0)),
            interest_rate=float(data.get('interest_rate', 0)),
            risk_score=float(round(proba, 2)), # تحويل ضروري لـ Postgres
            status=final_status
        )
        
        db.session.add(new_entry)
        db.session.commit()

        reason = "Ratio d'endettement critique (>40%)" if float(data.get('debt_to_income_ratio', 0)) > 40 else "Score de crédit insuffisant"
        
        return jsonify({
            'status': final_status,
            'risk_score': round(proba, 2),
            'reason': reason
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/requests')
def requests_list():
    all_clients = Simulation.query.order_by(Simulation.date_added.desc()).all()
    return render_template('requests.html', clients=all_clients)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)