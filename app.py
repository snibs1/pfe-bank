from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from config import Config
from models import db, Simulation
import joblib
import numpy as np
import os

app = Flask(__name__)
# تحميل الإعدادات من ملف config.py
app.config.from_object(Config)

# ربط التطبيق مع قاعدة البيانات
db.init_app(app)

# --- تحميل موديلات الذكاء الاصطناعي ---
try:
    model = joblib.load(os.path.join(app.config['BASE_DIR'], 'loan_prediction_model.pkl'))
    scaler = joblib.load(os.path.join(app.config['BASE_DIR'], 'data_scaler.pkl'))
    
    # إنشاء ملف الداتابيز (bank_data.db) إيلا ماكانش كاين
    with app.app_context():
        db.create_all()
        
    print("✅ NB BANK: System Ready & AI Models Loaded")
except Exception as e:
    print(f"❌ Critical Error: {e}")

# --- ROUTES (الصفحات) ---

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
    # كنجيبو آخر 5 عمليات باش يبانو فـ Dashboard
    recent_sims = Simulation.query.order_by(Simulation.date_added.desc()).limit(5).all()
    return render_template('dashboard.html', recent_sims=recent_sims)

@app.route('/simulation')
def simulation():
    return render_template('simulation.html')

# --- الصفحات الجديدة (CRM & PDF) ---

@app.route('/requests')
def requests_list():
    # كنجيبو كاع الكليان مرتبين من الجديد للقديم
    all_clients = Simulation.query.order_by(Simulation.date_added.desc()).all()
    return render_template('requests.html', clients=all_clients)

@app.route('/client/<int:id>')
def client_detail(id):
    # صفحة تفاصيل الكليان (باش تخرج PDF)
    client = Simulation.query.get_or_404(id)
    return render_template('client_detail.html', client=client)

# --- CORE AI ENGINE (المحرك) ---

@app.route('/predict', methods=['POST'])
def predict():
    try:
        data = request.form
        
        # 1. تحضير المعلومات للموديل (XGBoost)
        # الترتيب هنا ضروووري يكون نفس الترتيب باش تدرب الموديل
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
            1, 0, 1 # القيم الافتراضية
        ]

        # 2. معالجة البيانات (Scaling)
        features = np.array([model_inputs])
        if scaler.n_features_in_ > len(model_inputs):
            padding = np.zeros((1, scaler.n_features_in_ - len(model_inputs)))
            features = np.hstack([features, padding])
            
        features_scaled = scaler.transform(features)
        
        # 3. التوقع (Prediction)
        prediction = model.predict(features_scaled)[0]
        proba = model.predict_proba(features_scaled)[0][1] * 100 
        final_status = 'Approved' if prediction == 0 else 'Rejected'

        # 4. حفظ المعلومات كاملة فـ Database (باش تخرج فـ PDF)
        new_entry = Simulation(
            client_name=data.get('client_name', 'Client Inconnu'),
            cin=data.get('cin', 'N/A'),
            phone=data.get('phone', 'N/A'),
            annual_income=float(data.get('annual_income', 0)),
            credit_score=int(data.get('credit_score', 0)),
            loan_amount=float(data.get('loan_amount', 0)),
            loan_term=int(data.get('loan_term', 0)),
            interest_rate=float(data.get('interest_rate', 0)),
            risk_score=round(proba, 2),
            status=final_status
        )
        
        db.session.add(new_entry)
        db.session.commit()

        # 5. إرجاع النتيجة للصفحة
        reason = "Ratio d'endettement critique (>40%)" if float(data.get('debt_to_income_ratio', 0)) > 40 else "Score de crédit insuffisant"
        
        return jsonify({
            'status': final_status,
            'risk_score': round(proba, 2),
            'reason': reason
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)