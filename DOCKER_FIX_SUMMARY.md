# Docker Connection Fix Summary

## Problem
The `models-collector-1` Docker container was failing with the following error:
```
psycopg2.OperationalError: connection to server at "localhost" (::1), port 5432 failed
```

This occurred because the Python scripts were hardcoded to connect to `localhost:5432`, which doesn't work inside Docker containers. Inside Docker, services communicate using their service names as hostnames (e.g., `timescaledb` instead of `localhost`).

## Root Cause
1. **okx_websocket_collector.py** - Hardcoded `DB_CONFIG` with `host: 'localhost'`
2. **inference_api.py** - Hardcoded `DB_URL = "postgresql://postgres:password@localhost:5432/okx_trading"`
3. **docker-compose.yml** - Set `DB_HOST=timescaledb` in environment but the Python scripts weren't reading it

## Solution
Updated all files to use environment variables with sensible defaults for local development:

### 1. okx_websocket_collector.py
- Added `import os` to read environment variables
- Updated `DB_CONFIG` to use `os.getenv()` with fallback defaults:
  ```python
  DB_CONFIG = {
      'host': os.getenv('DB_HOST', 'localhost'),
      'database': os.getenv('DB_NAME', 'okx_trading'),
      'user': os.getenv('DB_USER', 'postgres'),
      'password': os.getenv('DB_PASSWORD', 'your_password'),
      'port': int(os.getenv('DB_PORT', '5432'))
  }
  ```
- Updated API credentials to also use environment variables:
  ```python
  api_key=os.getenv('OKX_API_KEY', 'YOUR_API_KEY'),
  ```

### 2. inference_api.py
- Added `import os` to read environment variables
- Updated database URL construction to use environment variables:
  ```python
  db_host = os.getenv('DB_HOST', 'localhost')
  db_name = os.getenv('DB_NAME', 'okx_trading')
  db_user = os.getenv('DB_USER', 'postgres')
  db_password = os.getenv('DB_PASSWORD', 'password')
  db_port = os.getenv('DB_PORT', '5432')
  
  DB_URL = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
  ```

### 3. docker-compose.yml
- **collector service** - Added missing environment variables:
  ```yaml
  environment:
    - DB_HOST=timescaledb
    - DB_NAME=okx_trading
    - DB_USER=postgres
    - DB_PASSWORD=your_password
    - DB_PORT=5432
    - OKX_API_KEY=${OKX_API_KEY}
    - OKX_SECRET_KEY=${OKX_SECRET_KEY}
    - OKX_PASSPHRASE=${OKX_PASSPHRASE}
  ```

- **api service** - Added database environment variables:
  ```yaml
  environment:
    - DB_HOST=timescaledb
    - DB_NAME=okx_trading
    - DB_USER=postgres
    - DB_PASSWORD=your_password
    - DB_PORT=5432
  ```

## How It Works Now

1. **In Docker**: Services communicate using service names
   - Collector connects to `timescaledb:5432` (service-to-service communication within Docker network)
   - API connects to `timescaledb:5432`

2. **Locally**: Scripts default to localhost
   - Collector: `localhost:5432`
   - API: `localhost:5432`
   - Can override with environment variables if needed

## Testing

To verify the fix works:

```bash
# Start all services
docker-compose up -d

# Check collector logs
docker-compose logs collector

# Should see "Connected to database" without connection refused errors
```

## Additional Notes

- The database password should be changed from `your_password` in production
- Consider using a `.env` file with actual credentials instead of hardcoding in docker-compose.yml
- The fallback values ensure the scripts work for local development without environment variables

