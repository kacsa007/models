# OKX Real-Time ML Trading Pipeline

A production-ready machine learning pipeline for cryptocurrency trading that ingests real-time market data from OKX exchange via WebSockets, stores it in TimescaleDB, and generates ML-based price predictions.

## Features

- **Real-time Data Ingestion**: WebSocket connections to OKX for live trades and orderbook data
- **Time-Series Database**: TimescaleDB for efficient storage and querying of market data
- **Feature Engineering**: 20+ technical indicators (RSI, MACD, Bollinger Bands, etc.)
- **ML Models**: XGBoost classifiers and regressors for price direction and return prediction
- **FastAPI Service**: RESTful API for real-time predictions
- **Docker Compose**: Full-stack orchestration with database, collector, and API services
- **Comprehensive Testing**: Unit, integration, and end-to-end tests with pytest
- **CI/CD**: GitHub Actions workflow for automated testing and deployment

## Architecture

```
┌─────────────┐
│ OKX Exchange│
│  WebSocket  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│   Data Collector│
│  (WebSockets)   │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  TimescaleDB    │
│  (PostgreSQL)   │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│Feature Engineer │
│  (Indicators)   │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  ML Models      │
│  (XGBoost)      │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  FastAPI        │
│  (Predictions)  │
└─────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.10+
- OKX API credentials (for live data)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/kacsa007/models.git
cd models
```

2. Create `.env` file from template:
```bash
cp .env.example .env
# Edit .env with your OKX API credentials
```

3. Start services with Docker Compose:
```bash
docker-compose up -d
```

4. Verify services are running:
```bash
curl http://localhost:8000/health
```

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

2. Run tests:
```bash
pytest
```

3. Start data collector:
```bash
python okx_websocket_collector.py
```

4. Train models:
```bash
python train_model.py
```

5. Start API server:
```bash
python inference_api.py
```

## API Endpoints

### Health Check
```bash
GET /health
```

### Price Prediction
```bash
POST /predict
{
  "instrument": "BTC-USDT",
  "lookback_periods": 100
}
```

Response:
```json
{
  "instrument": "BTC-USDT",
  "predicted_direction": 1,
  "predicted_return": 0.023,
  "confidence": 0.78,
  "timestamp": "2025-11-23T20:00:00"
}
```

## Testing

Run all tests:
```bash
pytest
```

Run only unit tests:
```bash
pytest -m "not integration"
```

Run with coverage:
```bash
pytest --cov=. --cov-report=html
```

## Project Structure

```
.
├── okx_websocket_collector.py   # Real-time data ingestion
├── feature_engineering.py       # Technical indicator generation
├── train_model.py               # ML model training
├── inference_api.py             # FastAPI prediction service
├── runner.py                    # Orchestration script
├── docker-compose.yml           # Docker services configuration
├── Dockerfile                   # Container image
├── requirements.txt             # Python dependencies
├── tests/
│   ├── conftest.py             # Shared test fixtures
│   ├── test_feature_engineering.py
│   ├── test_inference_api.py
│   ├── test_websocket_collector.py
│   ├── test_train_model.py
│   └── test_integration.py
├── .github/
│   └── workflows/
│       └── ci.yml              # CI/CD pipeline
└── README.md

```

## Configuration

### Environment Variables

See `.env.example` for all configuration options.

### Database Schema

The pipeline creates three main tables:
- `okx_trades`: Real-time trade data
- `okx_orderbook`: Order book snapshots
- `okx_ohlcv`: Aggregated OHLCV candlestick data

All tables are TimescaleDB hypertables optimized for time-series queries.

## Model Training

The pipeline uses two models:
1. **Classification Model**: Predicts price direction (up/down)
2. **Regression Model**: Predicts magnitude of price change

Features include:
- Moving averages (SMA, EMA)
- Momentum indicators (RSI, Stochastic)
- Volatility metrics (ATR, Bollinger Bands)
- Volume indicators
- Price action features

## Monitoring

- API health: `GET /health`
- Database metrics: Connect to TimescaleDB and query `pg_stat_database`
- Logs: Available via Docker logs or application logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

MIT License

## Acknowledgments

- OKX for providing WebSocket API
- TimescaleDB for time-series database
- XGBoost for ML models
- FastAPI for API framework
