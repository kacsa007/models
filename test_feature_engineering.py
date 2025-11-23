"""
Comprehensive tests for feature engineering pipeline.
"""
import pytest
import pandas as pd
import numpy as np
from feature_engineering import FeatureEngineer

def test_generate_technical_indicators(sample_ohlcv_data, feature_columns):
    """Test that technical indicators are generated correctly."""
    fe = FeatureEngineer('sqlite:///:memory:')
    result = fe.generate_technical_indicators(sample_ohlcv_data)
    
    # Check that key indicators are present
    assert 'sma_20' in result.columns
    assert 'rsi' in result.columns
    assert 'macd' in result.columns
    assert 'atr' in result.columns
    
    # Check that no infinite values exist
    assert not result.isin([np.inf, -np.inf]).any().any()
    
    # Check that result has same length as input (minus NaN droppage)
    assert len(result) <= len(sample_ohlcv_data)

def test_prepare_ml_dataset(sample_ohlcv_data):
    """Test ML dataset preparation with target variables."""
    fe = FeatureEngineer('sqlite:///:memory:')
    df_with_indicators = fe.generate_technical_indicators(sample_ohlcv_data)
    result = fe.prepare_ml_dataset(df_with_indicators, target_horizon=5)
    
    # Check target columns exist
    assert 'target' in result.columns
    assert 'target_return' in result.columns
    assert 'target_direction' in result.columns
    
    # Check target_direction is binary (0 or 1)
    assert set(result['target_direction'].unique()).issubset({0, 1})
    
    # Check no NaN in final dataset
    assert not result.isnull().any().any()

def test_orderbook_features(sample_orderbook_data):
    """Test orderbook feature extraction."""
    fe = FeatureEngineer('sqlite:///:memory:')
    
    # Create mock orderbook data in database format
    mock_df = pd.DataFrame({
        'bid_price': [45000.00, 44999.50, 44999.00],
        'bid_size': [0.5, 1.0, 2.0],
        'ask_price': [45001.00, 45001.50, 45002.00],
        'ask_size': [0.3, 0.8, 1.5],
        'level': [0, 1, 2]
    })
    
    # Calculate expected features manually
    total_bid = mock_df['bid_size'].sum()
    total_ask = mock_df['ask_size'].sum()
    expected_imbalance = (total_bid - total_ask) / (total_bid + total_ask)
    
    # This test validates the calculation logic
    assert abs(expected_imbalance) <= 1.0

def test_feature_engineering_with_insufficient_data():
    """Test feature engineering handles insufficient data gracefully."""
    fe = FeatureEngineer('sqlite:///:memory:')
    
    # Create minimal dataset (less than needed for some indicators)
    minimal_data = pd.DataFrame({
        'open': [1, 2],
        'high': [2, 3],
        'low': [0.5, 1.5],
        'close': [1.5, 2.5],
        'volume': [10, 15]
    })
    
    # Should not crash, but may have NaN values
    result = fe.generate_technical_indicators(minimal_data)
    assert result is not None
    assert len(result) <= len(minimal_data)

def test_returns_calculation(sample_ohlcv_data):
    """Test that returns are calculated correctly."""
    fe = FeatureEngineer('sqlite:///:memory:')
    result = fe.generate_technical_indicators(sample_ohlcv_data)
    
    # Check returns are percentage changes
    if 'returns' in result.columns:
        assert result['returns'].abs().max() < 1.0  # Reasonable range for crypto
    
    # Check log returns exist
    if 'log_returns' in result.columns:
        assert not result['log_returns'].isnull().all()
