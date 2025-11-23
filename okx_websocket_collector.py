import asyncio
import websockets
import json
import hmac
import base64
import time
from datetime import datetime
from typing import List, Dict
import psycopg2
from psycopg2.extras import execute_batch
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OKXWebSocketCollector:
    def __init__(self, api_key: str, secret_key: str, passphrase: str, db_config: Dict):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        self.db_config = db_config
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.private_ws_url = "wss://ws.okx.com:8443/ws/v5/private"
        self.conn = None
        self.buffer = []
        self.buffer_size = 100
        
    def _get_signature(self, timestamp: str, method: str, request_path: str, body: str = ""):
        """Generate signature for private endpoints"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode()
    
    async def connect_db(self):
        """Connect to PostgreSQL/TimescaleDB"""
        self.conn = psycopg2.connect(**self.db_config)
        logger.info("Connected to database")
        
    async def create_tables(self):
        """Create necessary tables with TimescaleDB hypertables"""
        cursor = self.conn.cursor()
        
        # Trades table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS okx_trades (
                timestamp TIMESTAMPTZ NOT NULL,
                instrument_id VARCHAR(50) NOT NULL,
                trade_id VARCHAR(50),
                side VARCHAR(10),
                price NUMERIC(20, 8),
                size NUMERIC(20, 8),
                PRIMARY KEY (timestamp, instrument_id, trade_id)
            );
        """)
        
        # Order book snapshots
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS okx_orderbook (
                timestamp TIMESTAMPTZ NOT NULL,
                instrument_id VARCHAR(50) NOT NULL,
                bid_price NUMERIC(20, 8),
                bid_size NUMERIC(20, 8),
                ask_price NUMERIC(20, 8),
                ask_size NUMERIC(20, 8),
                level INTEGER,
                PRIMARY KEY (timestamp, instrument_id, level)
            );
        """)
        
        # OHLCV data (aggregated)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS okx_ohlcv (
                timestamp TIMESTAMPTZ NOT NULL,
                instrument_id VARCHAR(50) NOT NULL,
                open NUMERIC(20, 8),
                high NUMERIC(20, 8),
                low NUMERIC(20, 8),
                close NUMERIC(20, 8),
                volume NUMERIC(20, 8),
                PRIMARY KEY (timestamp, instrument_id)
            );
        """)
        
        # Create TimescaleDB hypertables for time-series optimization
        try:
            cursor.execute("SELECT create_hypertable('okx_trades', 'timestamp', if_not_exists => TRUE);")
            cursor.execute("SELECT create_hypertable('okx_orderbook', 'timestamp', if_not_exists => TRUE);")
            cursor.execute("SELECT create_hypertable('okx_ohlcv', 'timestamp', if_not_exists => TRUE);")
        except Exception as e:
            logger.warning(f"Hypertables might already exist: {e}")
        
        self.conn.commit()
        cursor.close()
        logger.info("Tables created successfully")
    
    async def flush_buffer(self):
        """Batch insert buffered data to database"""
        if not self.buffer:
            return
            
        cursor = self.conn.cursor()
        try:
            execute_batch(cursor, """
                INSERT INTO okx_trades (timestamp, instrument_id, trade_id, side, price, size)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, self.buffer)
            self.conn.commit()
            logger.info(f"Inserted {len(self.buffer)} trades")
            self.buffer = []
        except Exception as e:
            logger.error(f"Error inserting data: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    async def handle_trade_message(self, data: Dict):
        """Process incoming trade data"""
        for trade in data.get('data', []):
            timestamp = datetime.fromtimestamp(int(trade['ts']) / 1000)
            self.buffer.append((
                timestamp,
                trade['instId'],
                trade['tradeId'],
                trade['side'],
                float(trade['px']),
                float(trade['sz'])
            ))
            
        if len(self.buffer) >= self.buffer_size:
            await self.flush_buffer()
    
    async def subscribe_trades(self, instruments: List[str]):
        """Subscribe to real-time trade data"""
        async with websockets.connect(self.ws_url) as ws:
            subscribe_msg = {
                "op": "subscribe",
                "args": [{"channel": "trades", "instId": inst} for inst in instruments]
            }
            await ws.send(json.dumps(subscribe_msg))
            logger.info(f"Subscribed to trades for {instruments}")
            
            while True:
                try:
                    message = await ws.recv()
                    data = json.loads(message)
                    
                    if 'event' in data:
                        logger.info(f"Event: {data}")
                        continue
                        
                    if data.get('arg', {}).get('channel') == 'trades':
                        await self.handle_trade_message(data)
                        
                except websockets.exceptions.ConnectionClosed:
                    logger.error("WebSocket connection closed, reconnecting...")
                    await asyncio.sleep(5)
                    break
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
    
    async def subscribe_orderbook(self, instruments: List[str]):
        """Subscribe to order book updates"""
        async with websockets.connect(self.ws_url) as ws:
            subscribe_msg = {
                "op": "subscribe",
                "args": [{"channel": "books", "instId": inst} for inst in instruments]
            }
            await ws.send(json.dumps(subscribe_msg))
            logger.info(f"Subscribed to orderbook for {instruments}")
            
            while True:
                try:
                    message = await ws.recv()
                    data = json.loads(message)
                    
                    if data.get('arg', {}).get('channel') == 'books':
                        await self.handle_orderbook_message(data)
                        
                except websockets.exceptions.ConnectionClosed:
                    logger.error("WebSocket connection closed, reconnecting...")
                    await asyncio.sleep(5)
                    break
    
    async def handle_orderbook_message(self, data: Dict):
        """Process orderbook data"""
        cursor = self.conn.cursor()
        try:
            for book_data in data.get('data', []):
                timestamp = datetime.fromtimestamp(int(book_data['ts']) / 1000)
                instrument_id = data['arg']['instId']
                
                # Insert top 5 levels of bids and asks
                for i, (bid_price, bid_size, _, _) in enumerate(book_data.get('bids', [])[:5]):
                    cursor.execute("""
                        INSERT INTO okx_orderbook (timestamp, instrument_id, bid_price, bid_size, level)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (timestamp, instrument_id, float(bid_price), float(bid_size), i))
                
                for i, (ask_price, ask_size, _, _) in enumerate(book_data.get('asks', [])[:5]):
                    cursor.execute("""
                        INSERT INTO okx_orderbook (timestamp, instrument_id, ask_price, ask_size, level)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                    """, (timestamp, instrument_id, float(ask_price), float(ask_size), i))
            
            self.conn.commit()
        except Exception as e:
            logger.error(f"Error processing orderbook: {e}")
            self.conn.rollback()
        finally:
            cursor.close()
    
    async def run(self, instruments: List[str]):
        """Main runner - manages multiple subscriptions"""
        await self.connect_db()
        await self.create_tables()
        
        # Run trades and orderbook subscriptions concurrently
        await asyncio.gather(
            self.subscribe_trades(instruments),
            self.subscribe_orderbook(instruments)
        )

# Usage
if __name__ == "__main__":
    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'okx_trading'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'your_password'),
        'port': int(os.getenv('DB_PORT', '5432'))
    }
    
    collector = OKXWebSocketCollector(
        api_key=os.getenv('OKX_API_KEY', 'YOUR_API_KEY'),
        secret_key=os.getenv('OKX_SECRET_KEY', 'YOUR_SECRET_KEY'),
        passphrase=os.getenv('OKX_PASSPHRASE', 'YOUR_PASSPHRASE'),
        db_config=DB_CONFIG
    )
    
    instruments = ['BTC-USDT', 'ETH-USDT', 'SOL-USDT']
    asyncio.run(collector.run(instruments))