import pandas as pd
import numpy as np
from sqlalchemy import create_engine
from typing import List
import ta  # Technical Analysis library

class FeatureEngineer:
    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
    
    def load_ohlcv(self, instrument: str, start_time: str, end_time: str) -> pd.DataFrame:
        """Load OHLCV data from database"""
        query = f"""
            SELECT timestamp, open, high, low, close, volume
            FROM okx_ohlcv
            WHERE instrument_id = '{instrument}'
            AND timestamp BETWEEN '{start_time}' AND '{end_time}'
            ORDER BY timestamp
        """
        df = pd.read_sql(query, self.engine)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df.set_index('timestamp', inplace=True)
        return df
    
    def generate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators as features"""
        # Check if we have enough data for indicators
        min_periods = 26  # EMA 26 is the longest window we use

        if len(df) < min_periods:
            # For small datasets, add NaN columns
            df['sma_20'] = np.nan
            df['ema_12'] = np.nan
            df['ema_26'] = np.nan
            df['macd'] = np.nan
            df['macd_signal'] = np.nan
            df['rsi'] = np.nan
            df['stoch'] = np.nan
            df['bb_high'] = np.nan
            df['bb_low'] = np.nan
            df['atr'] = np.nan
            df['volume_sma'] = np.nan
            df['volume_ratio'] = np.nan
            df['returns'] = df['close'].pct_change()
            df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
            df['volatility'] = np.nan
            df['momentum_5'] = np.nan
            df['momentum_10'] = np.nan
            return df

        # Trend indicators
        df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
        df['ema_12'] = ta.trend.ema_indicator(df['close'], window=12)
        df['ema_26'] = ta.trend.ema_indicator(df['close'], window=26)
        df['macd'] = ta.trend.macd(df['close'])
        df['macd_signal'] = ta.trend.macd_signal(df['close'])
        
        # Momentum indicators
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
        df['stoch'] = ta.momentum.stoch(df['high'], df['low'], df['close'])
        
        # Volatility indicators
        df['bb_high'] = ta.volatility.bollinger_hband(df['close'])
        df['bb_low'] = ta.volatility.bollinger_lband(df['close'])
        df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'])
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # Price action features
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        df['volatility'] = df['returns'].rolling(window=20).std()
        
        # Price momentum
        df['momentum_5'] = df['close'] - df['close'].shift(5)
        df['momentum_10'] = df['close'] - df['close'].shift(10)
        
        return df
    
    def create_orderbook_features(self, instrument: str, timestamp: str) -> dict:
        """Extract features from order book data"""
        query = f"""
            SELECT * FROM okx_orderbook
            WHERE instrument_id = '{instrument}'
            AND timestamp = '{timestamp}'
            ORDER BY level
        """
        df = pd.read_sql(query, self.engine)
        
        # Calculate order book imbalance
        total_bid_volume = df['bid_size'].sum()
        total_ask_volume = df['ask_size'].sum()
        imbalance = (total_bid_volume - total_ask_volume) / (total_bid_volume + total_ask_volume)
        
        # Spread
        best_bid = df.iloc[0]['bid_price']
        best_ask = df.iloc[0]['ask_price']
        spread = (best_ask - best_bid) / best_bid
        
        # Mid price
        mid_price = (best_bid + best_ask) / 2
        
        return {
            'imbalance': imbalance,
            'spread': spread,
            'mid_price': mid_price,
            'bid_depth': total_bid_volume,
            'ask_depth': total_ask_volume
        }
    
    def prepare_ml_dataset(self, df: pd.DataFrame, target_horizon: int = 5) -> pd.DataFrame:
        """Prepare dataset for ML with target variable"""
        # Create target: future price movement
        df['target'] = df['close'].shift(-target_horizon)
        df['target_return'] = (df['target'] - df['close']) / df['close']
        df['target_direction'] = (df['target_return'] > 0).astype(int)
        
        # Remove NaN values
        df = df.dropna()
        
        return df
