from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import joblib
import pandas as pd
from feature_engineering import FeatureEngineer
from typing import Dict, List
import os

app = FastAPI(title="OKX Trading ML API")

# Build database URL from environment variables
db_host = os.getenv('DB_HOST', 'localhost')
db_name = os.getenv('DB_NAME', 'okx_trading')
db_user = os.getenv('DB_USER', 'postgres')
db_password = os.getenv('DB_PASSWORD', 'password')
db_port = os.getenv('DB_PORT', '5432')

DB_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
feature_engineer = FeatureEngineer(DB_URL)

# Feature columns definition
FEATURE_COLUMNS = [
    'open', 'high', 'low', 'close', 'volume', 'sma_20', 'ema_12', 'ema_26', 'macd', 'macd_signal',
    'rsi', 'stoch', 'bb_high', 'bb_low', 'atr', 'volume_sma', 'volume_ratio',
    'returns', 'log_returns', 'volatility', 'momentum_5', 'momentum_10'
]

# Load models on startup
classification_model = joblib.load('models/direction_model.pkl')
regression_model = joblib.load('models/return_model.pkl')

class PredictionRequest(BaseModel):
    instrument: str
    lookback_periods: int = 100

class PredictionResponse(BaseModel):
    instrument: str
    predicted_direction: int
    predicted_return: float
    confidence: float
    timestamp: str

@app.post("/predict", response_model=PredictionResponse)
async def predict_price(request: PredictionRequest):
    """Generate real-time prediction for instrument"""
    try:
        df = feature_engineer.load_ohlcv(
            request.instrument,
            'NOW() - INTERVAL \'1 day\'',
            'NOW()'
        )
        df = feature_engineer.generate_technical_indicators(df)
        latest_features = df.iloc[-1:][FEATURE_COLUMNS]
        direction_pred = classification_model.predict(latest_features)[0]
        direction_proba = classification_model.predict_proba(latest_features)[0]
        return_pred = regression_model.predict(latest_features)[0]
        confidence = max(direction_proba)
        return PredictionResponse(
            instrument=request.instrument,
            predicted_direction=int(direction_pred),
            predicted_return=float(return_pred),
            confidence=float(confidence),
            timestamp=str(df.index[-1])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
