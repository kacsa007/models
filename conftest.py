"""
Pytest configuration and shared fixtures for the OKX trading ML pipeline.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from unittest.mock import Mock, patch, AsyncMock
import os
import joblib
from sklearn.ensemble import RandomForestClassifier

@pytest.fixture(scope='session', autouse=True)
def setup_test_models():
    """Create dummy models before any tests run."""
    os.makedirs('models', exist_ok=True)

    # Only create if they don't exist
    if not os.path.exists('models/direction_model.pkl') or not os.path.exists('models/return_model.pkl'):
        print("\n⚙ Creating dummy ML models for testing...")

        # Create minimal dummy models
        clf_model = RandomForestClassifier(n_estimators=5, max_depth=3, random_state=42)
        X_train = np.random.rand(50, 22)  # 22 features
        y_train = np.random.randint(0, 2, 50)
        clf_model.fit(X_train, y_train)

        reg_model = RandomForestClassifier(n_estimators=5, max_depth=3, random_state=42)
        reg_model.fit(X_train, y_train)

        joblib.dump(clf_model, 'models/direction_model.pkl')
        joblib.dump(reg_model, 'models/return_model.pkl')
        print("✓ Test models created successfully\n")

@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(start='2025-01-01', periods=100, freq='1h')
    data = {
        'timestamp': dates,
        'open': np.random.uniform(40000, 50000, 100),
        'high': np.random.uniform(50000, 55000, 100),
        'low': np.random.uniform(35000, 40000, 100),
        'close': np.random.uniform(40000, 50000, 100),
        'volume': np.random.uniform(100, 1000, 100)
    }
    df = pd.DataFrame(data)
    df.set_index('timestamp', inplace=True)
    return df

@pytest.fixture
def sample_trade_data():
    """Generate sample trade data for testing."""
    return [
        {
            'timestamp': datetime.now(),
            'instrument_id': 'BTC-USDT',
            'trade_id': '12345',
            'side': 'buy',
            'price': 45000.50,
            'size': 0.1
        },
        {
            'timestamp': datetime.now(),
            'instrument_id': 'ETH-USDT',
            'trade_id': '12346',
            'side': 'sell',
            'price': 3000.25,
            'size': 1.5
        }
    ]

@pytest.fixture
def sample_orderbook_data():
    """Generate sample orderbook data for testing."""
    return {
        'bids': [(45000.00, 0.5, 0, 0), (44999.50, 1.0, 0, 0), (44999.00, 2.0, 0, 0)],
        'asks': [(45001.00, 0.3, 0, 0), (45001.50, 0.8, 0, 0), (45002.00, 1.5, 0, 0)],
        'timestamp': int(datetime.now().timestamp() * 1000)
    }

@pytest.fixture
def mock_db_engine():
    """Mock database engine for testing."""
    return create_engine('sqlite:///:memory:')

@pytest.fixture
def feature_columns():
    """Define expected feature columns."""
    return [
        'open', 'high', 'low', 'close', 'volume', 
        'sma_20', 'ema_12', 'ema_26', 'macd', 'macd_signal',
        'rsi', 'stoch', 'bb_high', 'bb_low', 'atr', 
        'volume_sma', 'volume_ratio', 'returns', 'log_returns', 
        'volatility', 'momentum_5', 'momentum_10'
    ]
