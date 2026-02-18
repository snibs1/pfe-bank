from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from config import Config
from models import db, Simulation
import joblib
import numpy as np
import os
import random
from datetime import datetime, timedelta

app = Flask(__name__)

app.config.from_object(Config)


db.init_app(app)


try:
    model = joblib.load(os.path.join(app.config['BASE_DIR'], 'loan_prediction_model.pkl'))
    scaler = joblib.load(os.path.join(app.config['BASE_DIR'], 'data_scaler.pkl'))
    
    
    with app.app_context():
        db.create_all()
        
    print("✅ NB BANK: System Ready & AI Models Loaded")
except Exception as e:
    print(f"❌ Critical Error: {e}")



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
    
    
    total_volume = db.session.query(db.func.sum(Simulation.loan_amount)).scalar() or 0
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



@app.route('/requests')
def requests_list():
    
    all_clients = Simulation.query.order_by(Simulation.date_added.desc()).all()
    return render_template('requests.html', clients=all_clients)

@app.route('/generate_test_clients', methods=['POST'])
def generate_test_clients():
    
    first_names = ['Ahmed', 'Fatima', 'Mohammed', 'Khadija', 'Youssef', 'Amina', 'Hassan', 'Zineb', 'Omar', 'Salma']
    last_names = ['Benani', 'Alaoui', 'Idrissi', 'Fassi', 'Tazi', 'Benjelloun', 'Chraibi', 'Lahlou', 'Berrada', 'Squalli']
    
    
    for i in range(10):
        
        annual_income = random.randint(200000, 1000000)
        credit_score = random.randint(500, 850)
        debt_to_income_ratio = random.uniform(15, 45)
        loan_amount = random.randint(50000, 500000)
        loan_term = random.choice([12, 24, 36, 48, 60, 72, 84])
        interest_rate = random.uniform(4.5, 8.5)
        
        
        model_inputs = [
            annual_income,
            debt_to_income_ratio,
            credit_score,
            loan_amount,
            interest_rate,
            random.randint(0, 1),  
            random.randint(0, 1),  
            random.randint(0, 1),  
            random.randint(0, 1),  
            random.randint(0, 1),  
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
        
        
        client = Simulation(
            client_name=f"{random.choice(first_names)} {random.choice(last_names)}",
            cin=f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=2))}{random.randint(100000, 999999)}",
            phone=f"+212 6{random.randint(10, 99)} {random.randint(100, 999)} {random.randint(100, 999)}",
            annual_income=annual_income,
            credit_score=credit_score,
            loan_amount=loan_amount,
            loan_term=loan_term,
            interest_rate=round(interest_rate, 2),
            risk_score=round(proba, 2),
            status=final_status,
            date_added=datetime.now() - timedelta(days=random.randint(0, 30))
        )
        
        db.session.add(client)
    
    db.session.commit()
    
    return jsonify({'success': True, 'message': '10 clients générés avec succès'})

@app.route('/client/<int:id>')
def client_detail(id):
    
    client = Simulation.query.get_or_404(id)
    return render_template('client_detail.html', client=client)



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
            risk_score=round(proba, 2),
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

if __name__ == '__main__':
    app.run(debug=True)