"""
Comprehensive tests for FastAPI inference endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock
import numpy as np
from inference_api import app, FEATURE_COLUMNS

client = TestClient(app)

def test_health_check():
    """Test health check endpoint."""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.json() == {'status': 'healthy'}

def test_predict_endpoint_success(monkeypatch):
    """Test successful prediction endpoint."""
    import inference_api

    # Mock load_models to do nothing
    monkeypatch.setattr(inference_api, 'load_models', lambda: None)

    # Create mock models
    mock_clf_model = Mock()
    mock_reg_model = Mock()
    mock_clf_model.predict.return_value = np.array([1])
    mock_clf_model.predict_proba.return_value = np.array([[0.3, 0.7]])
    mock_reg_model.predict.return_value = np.array([0.05])

    # Set models on the module
    monkeypatch.setattr(inference_api, 'classification_model', mock_clf_model)
    monkeypatch.setattr(inference_api, 'regression_model', mock_reg_model)

    # Mock feature_engineer methods
    # Create a proper mock for DataFrame slicing
    mock_features = np.array([[1.0] * len(FEATURE_COLUMNS)])
    mock_iloc_result = Mock()
    mock_iloc_result.__getitem__ = Mock(return_value=mock_features)

    mock_iloc = Mock()
    mock_iloc.__getitem__ = Mock(return_value=mock_iloc_result)

    mock_df = Mock()
    mock_df.iloc = mock_iloc
    mock_df.index = [Mock(__str__=lambda self: '2025-11-23 20:00:00')]

    mock_fe = Mock()
    mock_fe.load_ohlcv.return_value = mock_df
    mock_fe.generate_technical_indicators.return_value = mock_df
    
    monkeypatch.setattr(inference_api, 'feature_engineer', mock_fe)

    response = client.post(
        '/predict',
        json={'instrument': 'BTC-USDT', 'lookback_periods': 100}
    )
    
    if response.status_code != 200:
        error_detail = response.json() if response.headers.get('content-type') == 'application/json' else response.text
        pytest.fail(f"Expected 200, got {response.status_code}. Error: {error_detail}")

    assert response.status_code == 200
    assert response.status_code == 200
    data = response.json()
    assert 'instrument' in data
    assert 'predicted_direction' in data
    assert 'predicted_return' in data
    assert 'confidence' in data
    assert data['instrument'] == 'BTC-USDT'
    assert data['predicted_direction'] in [0, 1]

def test_predict_endpoint_invalid_instrument():
    """Test prediction with invalid input."""
    response = client.post(
        '/predict',
        json={'instrument': '', 'lookback_periods': 100}
    )
    # May return 500 or validation error depending on implementation
    assert response.status_code in [422, 500]

def test_predict_endpoint_missing_fields():
    """Test prediction with missing required fields."""
    response = client.post('/predict', json={})
    assert response.status_code == 422  # Validation error
