"""
Tests for OKX WebSocket data collector.
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from okx_websocket_collector import OKXWebSocketCollector

@pytest.fixture
def ws_collector():
    """Create WebSocket collector instance."""
    db_config = {
        'host': 'localhost',
        'database': 'test_db',
        'user': 'test_user',
        'password': 'test_pass',
        'port': 5432
    }
    return OKXWebSocketCollector(
        api_key='test_key',
        secret_key='test_secret',
        passphrase='test_pass',
        db_config=db_config
    )

def test_signature_generation(ws_collector):
    """Test HMAC signature generation for authentication."""
    timestamp = '1234567890'
    method = 'GET'
    path = '/api/v5/account/balance'
    
    signature = ws_collector._get_signature(timestamp, method, path)
    
    assert signature is not None
    assert isinstance(signature, str)
    assert len(signature) > 0

@pytest.mark.asyncio
async def test_handle_trade_message(ws_collector, sample_trade_data):
    """Test trade message processing."""
    # Mock database connection
    ws_collector.conn = Mock()
    ws_collector.buffer = []
    
    # Simulate trade message
    trade_message = {
        'data': [
            {
                'instId': 'BTC-USDT',
                'tradeId': '12345',
                'side': 'buy',
                'px': '45000.50',
                'sz': '0.1',
                'ts': str(int(datetime.now().timestamp() * 1000))
            }
        ]
    }
    
    await ws_collector.handle_trade_message(trade_message)
    
    # Check buffer was populated
    assert len(ws_collector.buffer) == 1
    assert ws_collector.buffer[0][1] == 'BTC-USDT'

@pytest.mark.asyncio
@patch('okx_websocket_collector.execute_batch')
async def test_buffer_flush(mock_execute_batch, ws_collector):
    """Test that buffer flushes correctly when reaching threshold."""
    ws_collector.conn = Mock()
    ws_collector.buffer = [(datetime.now(), 'BTC-USDT', '123', 'buy', 45000, 0.1)] * 100
    ws_collector.buffer_size = 100
    
    # Mock cursor
    mock_cursor = Mock()
    ws_collector.conn.cursor.return_value = mock_cursor
    
    # Mock execute_batch to not raise exceptions
    mock_execute_batch.return_value = None

    await ws_collector.flush_buffer()
    
    # Buffer should be empty after flush
    assert len(ws_collector.buffer) == 0
    assert ws_collector.conn.commit.called
    assert mock_execute_batch.called

def test_websocket_url_configuration(ws_collector):
    """Test WebSocket URLs are properly configured."""
    assert ws_collector.ws_url.startswith('wss://')
    assert 'okx.com' in ws_collector.ws_url
    assert ws_collector.private_ws_url.startswith('wss://')
