import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import accuracy_score, f1_score, mean_squared_error
import joblib
import xgboost as xgb
from feature_engineering import FeatureEngineer

class TradingModelTrainer:
    def __init__(self, db_url: str):
        self.feature_engineer = FeatureEngineer(db_url)
        self.classification_model = None
        self.regression_model = None
    
    def prepare_training_data(self, instrument: str, start_time: str, end_time: str):
        """Load and prepare data for training"""
        df = self.feature_engineer.load_ohlcv(instrument, start_time, end_time)
        df = self.feature_engineer.generate_technical_indicators(df)
        df = self.feature_engineer.prepare_ml_dataset(df, target_horizon=5)
        
        # Feature columns
        feature_cols = [col for col in df.columns if col not in ['target', 'target_return', 'target_direction']]
        
        X = df[feature_cols]
        y_direction = df['target_direction']
        y_return = df['target_return']
        
        return X, y_direction, y_return
    
    def train_direction_model(self, X, y):
        """Train classification model for price direction"""
        # Use TimeSeriesSplit for proper cross-validation
        tscv = TimeSeriesSplit(n_splits=5)
        
        # XGBoost for classification
        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=7,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        
        scores = []
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
            
            model.fit(X_train, y_train)
            pred = model.predict(X_val)
            score = accuracy_score(y_val, pred)
            scores.append(score)
            print(f"Fold accuracy: {score:.4f}")
        
        print(f"Average CV accuracy: {np.mean(scores):.4f}")
        
        # Train on full dataset
        model.fit(X, y)
        self.classification_model = model
        
        return model
    
    def train_return_model(self, X, y):
        """Train regression model for price returns"""
        model = xgb.XGBRegressor(
            n_estimators=200,
            max_depth=7,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42
        )
        
        model.fit(X, y)
        self.regression_model = model
        
        return model
    
    def save_models(self, classification_path: str, regression_path: str):
        """Save trained models"""
        joblib.dump(self.classification_model, classification_path)
        joblib.dump(self.regression_model, regression_path)
        print(f"Models saved to {classification_path} and {regression_path}")
    
    def load_models(self, classification_path: str, regression_path: str):
        """Load pre-trained models"""
        self.classification_model = joblib.load(classification_path)
        self.regression_model = joblib.load(regression_path)
        print("Models loaded successfully")

# Usage
if __name__ == "__main__":
    DB_URL = "postgresql://postgres:password@localhost:5432/okx_trading"
    
    trainer = TradingModelTrainer(DB_URL)
    X, y_direction, y_return = trainer.prepare_training_data(
        'BTC-USDT',
        '2024-01-01',
        '2025-11-23'
    )
    
    print("Training direction model...")
    trainer.train_direction_model(X, y_direction)
    
    print("Training return model...")
    trainer.train_return_model(X, y_return)
    
    trainer.save_models('models/direction_model.pkl', 'models/return_model.pkl')
