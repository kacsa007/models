"""
Tests for ML model training pipeline.
"""
import pytest
import pandas as pd
import numpy as np
from unittest.mock import Mock, patch
from train_model import TradingModelTrainer

@pytest.fixture
def mock_trainer():
    """Create mock trainer instance."""
    with patch('train_model.FeatureEngineer'):
        trainer = TradingModelTrainer('sqlite:///:memory:')
        return trainer

def test_prepare_training_data(mock_trainer, sample_ohlcv_data):
    """Test training data preparation."""
    # Mock feature engineer
    mock_trainer.feature_engineer.load_ohlcv = Mock(return_value=sample_ohlcv_data)
    mock_trainer.feature_engineer.generate_technical_indicators = Mock(return_value=sample_ohlcv_data)
    
    # Add required columns for ML dataset
    sample_ohlcv_data['target'] = sample_ohlcv_data['close'].shift(-5)
    sample_ohlcv_data['target_return'] = 0.01
    sample_ohlcv_data['target_direction'] = 1
    sample_ohlcv_data = sample_ohlcv_data.dropna()
    
    mock_trainer.feature_engineer.prepare_ml_dataset = Mock(return_value=sample_ohlcv_data)
    
    X, y_direction, y_return = mock_trainer.prepare_training_data('BTC-USDT', '2024-01-01', '2025-01-01')
    
    assert X is not None
    assert y_direction is not None
    assert y_return is not None
    assert len(X) == len(y_direction) == len(y_return)

def test_model_training_shapes(mock_trainer, sample_ohlcv_data):
    """Test that models accept correct input shapes."""
    # Create minimal feature set
    X = sample_ohlcv_data[['open', 'high', 'low', 'close', 'volume']].dropna()
    y = pd.Series([1] * len(X))
    
    # Training should not crash with valid data
    model = mock_trainer.train_direction_model(X, y)
    assert model is not None

def test_model_save_and_load(mock_trainer, tmp_path):
    """Test model serialization."""
    # Create dummy models
    from sklearn.ensemble import RandomForestClassifier
    mock_trainer.classification_model = RandomForestClassifier(n_estimators=5)
    mock_trainer.regression_model = RandomForestClassifier(n_estimators=5)
    
    # Fit with dummy data
    X = np.random.rand(10, 5)
    y = np.random.randint(0, 2, 10)
    mock_trainer.classification_model.fit(X, y)
    mock_trainer.regression_model.fit(X, y)
    
    # Save models
    clf_path = tmp_path / "clf.pkl"
    reg_path = tmp_path / "reg.pkl"
    mock_trainer.save_models(str(clf_path), str(reg_path))
    
    # Check files exist
    assert clf_path.exists()
    assert reg_path.exists()
    
    # Load models
    mock_trainer.load_models(str(clf_path), str(reg_path))
    assert mock_trainer.classification_model is not None
    assert mock_trainer.regression_model is not None
