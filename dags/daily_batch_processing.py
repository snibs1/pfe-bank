"""
NB BANK - Daily Batch Processing Pipeline
ETL: Extract → Transform → Load
Runs every day at 2 AM
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import pandas as pd
import psycopg2
import numpy as np
import joblib

# Database connection parameters
DB_CONFIG = {
    'host': 'db',
    'database': 'bank_warehouse',
    'user': 'admin',
    'password': 'pfe_password'
}

# Default arguments for the DAG
default_args = {
    'owner': 'nb_bank_data_engineering',
    'depends_on_past': False,
    'start_date': datetime(2026, 2, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# Create the DAG
dag = DAG(
    'daily_loan_batch_processing',
    default_args=default_args,
    description='Daily ETL pipeline for loan application batch processing',
    schedule_interval='0 2 * * *',  # 2 AM every day
    catchup=False,
    tags=['etl', 'batch', 'ml', 'production'],
)

def extract_new_applications(**context):
    """
    EXTRACT: Get unprocessed applications from staging table
    """
    print("=" * 80)
    print("🔵 EXTRACT PHASE: Getting new loan applications from staging...")
    print("=" * 80)
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Get unprocessed applications
    query = """
        SELECT * FROM staging_applications 
        WHERE processed = FALSE
        ORDER BY uploaded_at ASC
    """
    
    df = pd.read_sql(query, conn)
    conn.close()
    
    record_count = len(df)
    print(f"✅ Extracted {record_count} new applications from staging")
    
    if record_count == 0:
        print("⚠️  No new applications to process. Pipeline will skip remaining tasks.")
        return None
    
    # Save to XCom (pass data to next task)
    context['ti'].xcom_push(key='raw_applications', value=df.to_json(orient='records'))
    
    return f"Extracted {record_count} applications"


def validate_and_clean_data(**context):
    """
    TRANSFORM STEP 1: Data Quality Checks & Cleaning
    """
    print("=" * 80)
    print("🟡 TRANSFORM PHASE 1: Data Validation & Cleaning...")
    print("=" * 80)
    
    # Get data from previous task
    raw_json = context['ti'].xcom_pull(key='raw_applications', task_ids='extract_task')
    
    if raw_json is None:
        print("⚠️  No data to validate. Skipping.")
        return "No data"
    
    df = pd.read_json(raw_json, orient='records')
    initial_count = len(df)
    
    print(f"📊 Initial record count: {initial_count}")
    
    # Quality Check 1: Remove duplicates based on CIN
    df = df.drop_duplicates(subset=['cin'], keep='first')
    duplicates_removed = initial_count - len(df)
    print(f"   ✓ Duplicates removed: {duplicates_removed}")
    
    # Quality Check 2: Remove rows with missing critical values
    critical_columns = ['annual_income', 'credit_score', 'loan_amount', 'client_name']
    before_null = len(df)
    df = df.dropna(subset=critical_columns)
    nulls_removed = before_null - len(df)
    print(f"   ✓ Records with missing values removed: {nulls_removed}")
    
    # Quality Check 3: Validate data ranges
    before_validation = len(df)
    df = df[df['credit_score'].between(300, 850)]
    df = df[df['annual_income'] > 0]
    df = df[df['loan_amount'] > 0]
    df = df[df['interest_rate'] > 0]
    invalid_removed = before_validation - len(df)
    print(f"   ✓ Invalid range records removed: {invalid_removed}")
    
    # Quality Check 4: Handle outliers (3 standard deviations)
    numeric_cols = ['annual_income', 'loan_amount']
    for col in numeric_cols:
        mean = df[col].mean()
        std = df[col].std()
        df = df[np.abs(df[col] - mean) <= (3 * std)]
    outliers_removed = before_validation - len(df)
    print(f"   ✓ Outliers removed: {outliers_removed}")
    
    cleaned_count = len(df)
    total_removed = initial_count - cleaned_count
    
    print(f"\n📈 Cleaning Summary:")
    print(f"   Initial records: {initial_count}")
    print(f"   Valid records: {cleaned_count}")
    print(f"   Total removed: {total_removed} ({total_removed/initial_count*100:.1f}%)")
    
    # Save cleaned data
    context['ti'].xcom_push(key='cleaned_applications', value=df.to_json(orient='records'))
    context['ti'].xcom_push(key='quality_stats', value={
        'initial': initial_count,
        'final': cleaned_count,
        'duplicates': duplicates_removed,
        'nulls': nulls_removed,
        'invalid': invalid_removed
    })
    
    return f"Cleaned {cleaned_count} records"


def feature_engineering_and_ml_prediction(**context):
    """
    TRANSFORM STEP 2: Feature Engineering + ML Predictions
    """
    print("=" * 80)
    print("🟢 TRANSFORM PHASE 2: Feature Engineering & ML Predictions...")
    print("=" * 80)
    
    # Get cleaned data
    clean_json = context['ti'].xcom_pull(key='cleaned_applications', task_ids='validate_task')
    
    if clean_json is None:
        print("⚠️  No data to process. Skipping.")
        return "No data"
    
    df = pd.read_json(clean_json, orient='records')
    
    print(f"📊 Processing {len(df)} applications through ML model...")
    
    # Load ML model and scaler
    model = joblib.load('/opt/airflow/models/loan_prediction_model.pkl')
    scaler = joblib.load('/opt/airflow/models/data_scaler.pkl')
    
    predictions = []
    
    for idx, row in df.iterrows():
        # Feature Engineering
        model_inputs = [
            float(row['annual_income']),
            float(row.get('debt_to_income_ratio', 30)),
            float(row['credit_score']),
            float(row['loan_amount']),
            float(row.get('interest_rate', 5.0)),
            1 if row.get('gender', 'Male') == 'Male' else 0,
            1 if row.get('marital_status', 'Single') == 'Married' else 0,
            1 if row.get('education_level', 'High School') == 'Graduate' else 0,
            1 if row.get('employment_status', 'Unemployed') == 'Employed' else 0,
            1 if row.get('loan_purpose', 'Personal') == 'Business' else 0,
            1, 0, 1  # Fixed features
        ]
        
        # Scale features
        features = np.array([model_inputs])
        if scaler.n_features_in_ > len(model_inputs):
            padding = np.zeros((1, scaler.n_features_in_ - len(model_inputs)))
            features = np.hstack([features, padding])
        
        features_scaled = scaler.transform(features)
        
        # Predict
        prediction = model.predict(features_scaled)[0]
        proba = model.predict_proba(features_scaled)[0][1] * 100
        final_status = 'Approved' if prediction == 0 else 'Rejected'
        
        predictions.append({
            'staging_id': int(row['id']),
            'client_name': row['client_name'],
            'cin': row['cin'],
            'phone': row.get('phone', 'N/A'),
            'annual_income': float(row['annual_income']),
            'credit_score': int(row['credit_score']),
            'loan_amount': float(row['loan_amount']),
            'loan_term': int(row.get('loan_term', 60)),
            'interest_rate': float(row.get('interest_rate', 5.0)),
            'risk_score': round(proba, 2),
            'status': final_status
        })
    
    approved = sum(1 for p in predictions if p['status'] == 'Approved')
    rejected = len(predictions) - approved
    
    print(f"\n📊 ML Prediction Results:")
    print(f"   Total processed: {len(predictions)}")
    print(f"   ✅ Approved: {approved} ({approved/len(predictions)*100:.1f}%)")
    print(f"   ❌ Rejected: {rejected} ({rejected/len(predictions)*100:.1f}%)")
    
    # Save predictions
    context['ti'].xcom_push(key='predictions', value=predictions)
    
    return f"Processed {len(predictions)} predictions"


def load_to_production_database(**context):
    """
    LOAD: Save results to production database
    """
    print("=" * 80)
    print("🔵 LOAD PHASE: Saving results to production database...")
    print("=" * 80)
    
    # Get predictions
    predictions = context['ti'].xcom_pull(key='predictions', task_ids='ml_task')
    
    if predictions is None or len(predictions) == 0:
        print("⚠️  No predictions to load. Skipping.")
        return "No data"
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    loaded = 0
    staging_ids = []
    
    for pred in predictions:
        try:
            # Insert into simulations table
            cursor.execute("""
                INSERT INTO simulations 
                (client_name, cin, phone, annual_income, credit_score, 
                 loan_amount, loan_term, interest_rate, risk_score, status, date_added)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            """, (
                pred['client_name'],
                pred['cin'],
                pred['phone'],
                pred['annual_income'],
                pred['credit_score'],
                pred['loan_amount'],
                pred['loan_term'],
                pred['interest_rate'],
                pred['risk_score'],
                pred['status']
            ))
            
            loaded += 1
            staging_ids.append(pred['staging_id'])
            
        except Exception as e:
            print(f"❌ Error loading record: {e}")
    
    # Mark staging records as processed
    if staging_ids:
        cursor.execute("""
            UPDATE staging_applications 
            SET processed = TRUE 
            WHERE id = ANY(%s)
        """, (staging_ids,))
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"\n✅ Successfully loaded {loaded} records to production database")
    print(f"✅ Marked {len(staging_ids)} staging records as processed")
    
    return f"Loaded {loaded} records"


# Define tasks
extract_task = PythonOperator(
    task_id='extract_task',
    python_callable=extract_new_applications,
    dag=dag,
)

validate_task = PythonOperator(
    task_id='validate_task',
    python_callable=validate_and_clean_data,
    dag=dag,
)

ml_task = PythonOperator(
    task_id='ml_task',
    python_callable=feature_engineering_and_ml_prediction,
    dag=dag,
)

load_task = PythonOperator(
    task_id='load_task',
    python_callable=load_to_production_database,
    dag=dag,
)

# Define ETL pipeline flow
extract_task >> validate_task >> ml_task >> load_task