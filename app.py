from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import joblib
import numpy as np
import os

app = Flask(__name__)
app.secret_key = 'nb_bank_2026_secure_key'


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
try:
    model = joblib.load(os.path.join(BASE_DIR, 'loan_prediction_model.pkl'))
    scaler = joblib.load(os.path.join(BASE_DIR, 'data_scaler.pkl'))
    print("✅ NB BANK: Models Loaded Successfully")
except Exception as e:
    print(f"❌ Error Loading Models: {e}")

@app.route('/')
def login_page():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    
    user = request.form.get('username')
    pwd = request.form.get('password')
    if user == "admin" and pwd == "1234":
        return redirect(url_for('dashboard'))
    flash("Invalid Credentials. Please try again.", "danger")
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
            1, 
            0, 
            1  
        ]

        features = np.array([model_inputs])
        
        
        if scaler.n_features_in_ > len(model_inputs):
            padding = np.zeros((1, scaler.n_features_in_ - len(model_inputs)))
            features = np.hstack([features, padding])
            
        features_scaled = scaler.transform(features)
        
        
        prediction = model.predict(features_scaled)[0]
        proba = model.predict_proba(features_scaled)[0][1] * 100 

        
        reason = "Credit History Analysis"
        if float(data.get('debt_to_income_ratio', 0)) > 40:
            reason = "High Debt-to-Income Ratio"
        elif float(data.get('credit_score', 0)) < 600:
            reason = "Insufficient Credit Score"

        return jsonify({
            'status': 'Approved' if prediction == 0 else 'Rejected',
            'risk_score': round(proba, 2),
            'reason': reason
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)