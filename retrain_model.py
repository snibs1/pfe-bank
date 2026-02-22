"""
Retrain and save ML model with current environment packages.
Run this to regenerate loan_prediction_model.pkl and data_scaler.pkl
"""

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb
import joblib
import os

print("=" * 80)
print("RETRAINING MODEL WITH CURRENT ENVIRONMENT")
print("=" * 80)

# Load training data
try:
    df = pd.read_csv("train.csv")
    print(f"✅ Loaded training data: {len(df)} records")
except Exception as e:
    print(f"❌ Cannot load train.csv: {e}")
    print("Place your train.csv in the project root and retry.")
    exit(1)

# Prepare features and target
X = pd.get_dummies(df.drop('loan_paid_back', axis=1), drop_first=True)
y = df['loan_paid_back']

print(f"📊 Features shape: {X.shape}")
print(f"📊 Target shape: {y.shape}")

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=101)
print(f"✅ Train/test split: {len(X_train)} / {len(X_test)}")

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
print(f"✅ Features scaled (scaler.n_features_in_ = {scaler.n_features_in_})")

# Train LightGBM
model = lgb.LGBMClassifier(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=5,
    random_state=42,
    verbose=-1
)

model.fit(X_train_scaled, y_train)
print(f"✅ LightGBM model trained")

# Evaluate
from sklearn.metrics import classification_report, accuracy_score
y_pred = model.predict(X_test_scaled)
acc = accuracy_score(y_test, y_pred)
print(f"✅ Test accuracy: {acc:.4f}")
print("\nClassification Report:")
print(classification_report(y_test, y_pred))

# Save model and scaler
model_path = 'loan_prediction_model.pkl'
scaler_path = 'data_scaler.pkl'

joblib.dump(model, model_path)
joblib.dump(scaler, scaler_path)

print(f"\n✅ Model saved to {model_path}")
print(f"✅ Scaler saved to {scaler_path}")

# Verify
loaded_model = joblib.load(model_path)
loaded_scaler = joblib.load(scaler_path)
test_pred = loaded_model.predict(loaded_scaler.transform(X_test_scaled))
print(f"✅ Verification: loaded model accuracy = {accuracy_score(y_test, test_pred):.4f}")

print("\n" + "=" * 80)
print("✅ RETRAINING COMPLETE - Use the new .pkl files in deployment")
print("=" * 80)
