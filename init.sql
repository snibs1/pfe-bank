-- إنشاء قاعدة بيانات Airflow
CREATE DATABASE airflow_db;

-- الاتصال بقاعدة بيانات البنك
\c bank_warehouse;

-- جدول تطبيقات القروض (Staging) للـ Batch Processing
CREATE TABLE IF NOT EXISTS staging_applications (
    id SERIAL PRIMARY KEY,
    client_name VARCHAR(100),
    cin VARCHAR(20),
    phone VARCHAR(20),
    annual_income FLOAT,
    debt_to_income_ratio FLOAT,
    credit_score INTEGER,
    loan_amount FLOAT,
    loan_term INTEGER,
    interest_rate FLOAT,
    gender VARCHAR(20),
    marital_status VARCHAR(50),
    education_level VARCHAR(50),
    employment_status VARCHAR(50),
    loan_purpose VARCHAR(50),
    processed BOOLEAN DEFAULT FALSE,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- جدول المحاكاة النهائي (Production)
CREATE TABLE IF NOT EXISTS simulations (
    id SERIAL PRIMARY KEY,
    client_name VARCHAR(100),
    cin VARCHAR(20),
    phone VARCHAR(20),
    annual_income FLOAT,
    credit_score INTEGER,
    loan_amount FLOAT,
    loan_term INTEGER,
    interest_rate FLOAT,
    risk_score FLOAT,
    status VARCHAR(20),
    date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);