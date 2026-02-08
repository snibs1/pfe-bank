import os
import joblib
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'nb_bank_secret_key'


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    model = joblib.load(os.path.join(BASE_DIR, 'loan_prediction_model.pkl'))
    scaler = joblib.load(os.path.join(BASE_DIR, 'data_scaler.pkl'))
    print("✅ Models Loaded Successfully")
except:
    print("❌ Error: Model files not found!")

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    if request.form.get('username') == "admin" and request.form.get('password') == "1234":
        return redirect(url_for('dashboard'))
    flash("Identifiant incorrect", "danger")
    return redirect(url_for('login_page'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/simulation')
def simulation():
    return render_template('simulation.html')

@app.route('/predict', methods=['POST'])
def predict():
    try:
        
        data = [
            float(request.form.get('annual_income')),
            float(request.form.get('debt_to_income_ratio')),
            float(request.form.get('credit_score')),
            float(request.form.get('loan_amount')),
            float(request.form.get('interest_rate')),
            
            1 if request.form.get('gender') == 'Male' else 0,
            1 if request.form.get('marital_status') == 'Married' else 0,
            1 if request.form.get('education_level') == 'Graduate' else 0,
            1 if request.form.get('employment_status') == 'Employed' else 0,
            1 if request.form.get('loan_purpose') == 'Business' else 0,
            1, 
            0  
        ]
        
        
        features = np.array([data])
        
        if scaler.n_features_in_ > len(data):
            padding = np.zeros((1, scaler.n_features_in_ - len(data)))
            features = np.hstack([features, padding])

        features_scaled = scaler.transform(features)
        prediction = model.predict(features_scaled)[0]
        
        try:
            prob = model.predict_proba(features_scaled)[0][1] * 100
        except:
            prob = 85 if prediction == 1 else 15

        return jsonify({'status': 'Approved' if prediction == 0 else 'Rejected', 'risk_score': round(prob, 2)})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)