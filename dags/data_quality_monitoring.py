"""
NB BANK - Data Quality Monitoring Pipeline
Checks data quality every 6 hours
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import psycopg2
import pandas as pd

# Database connection
DB_CONFIG = {
    'host': 'db',
    'database': 'bank_warehouse',
    'user': 'admin',
    'password': 'pfe_password'
}

default_args = {
    'owner': 'nb_bank_data_quality',
    'depends_on_past': False,
    'start_date': datetime(2026, 2, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'data_quality_monitoring',
    default_args=default_args,
    description='Monitor data quality issues in production database',
    schedule_interval='0 */6 * * *',  # Every 6 hours
    catchup=False,
    tags=['quality', 'monitoring', 'validation'],
)

def check_missing_values(**context):
    """Check for missing critical values"""
    print("🔍 Checking for missing values...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Check each critical column
    checks = {
        'client_name': "SELECT COUNT(*) FROM simulations WHERE client_name IS NULL OR client_name = ''",
        'cin': "SELECT COUNT(*) FROM simulations WHERE cin IS NULL OR cin = ''",
        'annual_income': "SELECT COUNT(*) FROM simulations WHERE annual_income IS NULL",
        'credit_score': "SELECT COUNT(*) FROM simulations WHERE credit_score IS NULL",
        'loan_amount': "SELECT COUNT(*) FROM simulations WHERE loan_amount IS NULL",
    }
    
    issues = {}
    total_issues = 0
    
    for column, query in checks.items():
        cursor.execute(query)
        count = cursor.fetchone()[0]
        if count > 0:
            issues[column] = count
            total_issues += count
            print(f"   ⚠️  {column}: {count} missing values")
    
    cursor.close()
    conn.close()
    
    if total_issues == 0:
        print("   ✅ No missing values detected")
    else:
        print(f"\n⚠️  Total missing values: {total_issues}")
    
    context['ti'].xcom_push(key='missing_values', value=total_issues)
    
    return f"Missing values: {total_issues}"


def check_duplicates(**context):
    """Check for duplicate CINs"""
    print("🔍 Checking for duplicate CINs...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = cursor.execute("""
        SELECT cin, COUNT(*) as cnt 
        FROM simulations 
        WHERE cin IS NOT NULL 
        GROUP BY cin 
        HAVING COUNT(*) > 1
    """)
    
    duplicates = cursor.fetchall()
    dup_count = len(duplicates)
    
    if dup_count > 0:
        print(f"   ⚠️  Found {dup_count} duplicate CINs:")
        for cin, count in duplicates[:5]:  # Show first 5
            print(f"      - {cin}: {count} occurrences")
    else:
        print("   ✅ No duplicate CINs found")
    
    cursor.close()
    conn.close()
    
    context['ti'].xcom_push(key='duplicates', value=dup_count)
    
    return f"Duplicates: {dup_count}"


def check_outliers(**context):
    """Check for statistical outliers"""
    print("🔍 Checking for outliers...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Get data
    df = pd.read_sql("SELECT annual_income, loan_amount, credit_score FROM simulations", conn)
    conn.close()
    
    outliers = {}
    
    # Check each numeric column
    for col in ['annual_income', 'loan_amount', 'credit_score']:
        mean = df[col].mean()
        std = df[col].std()
        outlier_mask = abs(df[col] - mean) > (3 * std)
        count = outlier_mask.sum()
        
        if count > 0:
            outliers[col] = count
            print(f"   ⚠️  {col}: {count} outliers detected")
    
    total_outliers = sum(outliers.values())
    
    if total_outliers == 0:
        print("   ✅ No statistical outliers detected")
    
    context['ti'].xcom_push(key='outliers', value=total_outliers)
    
    return f"Outliers: {total_outliers}"


def generate_quality_report(**context):
    """Generate summary report"""
    print("=" * 80)
    print("📊 DATA QUALITY REPORT")
    print("=" * 80)
    
    missing = context['ti'].xcom_pull(key='missing_values', task_ids='check_missing')
    duplicates = context['ti'].xcom_pull(key='duplicates', task_ids='check_duplicates')
    outliers = context['ti'].xcom_pull(key='outliers', task_ids='check_outliers')
    
    print(f"\n📋 Summary:")
    print(f"   Missing Values: {missing}")
    print(f"   Duplicate CINs: {duplicates}")
    print(f"   Statistical Outliers: {outliers}")
    
    total_issues = missing + duplicates + outliers
    
    if total_issues == 0:
        print(f"\n✅ Data quality: EXCELLENT")
    elif total_issues < 10:
        print(f"\n⚠️  Data quality: GOOD (minor issues)")
    else:
        print(f"\n❌ Data quality: NEEDS ATTENTION")
    
    print("=" * 80)
    
    return f"Quality check complete: {total_issues} issues"


# Define tasks
missing_task = PythonOperator(
    task_id='check_missing',
    python_callable=check_missing_values,
    dag=dag,
)

duplicates_task = PythonOperator(
    task_id='check_duplicates',
    python_callable=check_duplicates,
    dag=dag,
)

outliers_task = PythonOperator(
    task_id='check_outliers',
    python_callable=check_outliers,
    dag=dag,
)

report_task = PythonOperator(
    task_id='generate_report',
    python_callable=generate_quality_report,
    dag=dag,
)

# All checks run in parallel, then generate report
[missing_task, duplicates_task, outliers_task] >> report_task