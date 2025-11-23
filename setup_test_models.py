#!/usr/bin/env python3
"""
Generate dummy ML models for testing purposes.
This script is run during CI/CD to create model files when they don't exist.
"""
import joblib
from sklearn.ensemble import RandomForestClassifier
import numpy as np
import os

def create_dummy_models():
    """Create minimal dummy models for testing."""
    # Create models directory
    os.makedirs('models', exist_ok=True)
    
    # Check if models already exist
    if os.path.exists('models/direction_model.pkl') and os.path.exists('models/return_model.pkl'):
        print("Models already exist, skipping creation.")
        return
    
    print("Creating dummy ML models for testing...")
    
    # Create and train minimal dummy models
    # Classification model (direction prediction)
    clf_model = RandomForestClassifier(n_estimators=5, max_depth=3, random_state=42)
    X_train = np.random.rand(50, 22)  # 22 features to match FEATURE_COLUMNS
    y_train = np.random.randint(0, 2, 50)
    clf_model.fit(X_train, y_train)
    
    # Regression model (return prediction)
    reg_model = RandomForestClassifier(n_estimators=5, max_depth=3, random_state=42)
    reg_model.fit(X_train, y_train)
    
    # Save models
    joblib.dump(clf_model, 'models/direction_model.pkl')
    joblib.dump(reg_model, 'models/return_model.pkl')
    
    print(f"✓ Created models/direction_model.pkl")
    print(f"✓ Created models/return_model.pkl")
    print("Dummy models ready for testing.")

if __name__ == "__main__":
    create_dummy_models()
