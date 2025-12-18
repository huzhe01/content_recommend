# Stock Trading Bot

A stock trading bot API built with FastAPI that provides automated trading strategies, portfolio management, and real-time stock data.

## Features

- **Real-time Stock Data**: Fetch current stock prices and historical data using yfinance
- **Trading Strategies**: Multiple built-in strategies including:
  - SMA Crossover (Simple Moving Average)
  - RSI (Relative Strength Index)
  - MACD (Moving Average Convergence Divergence)
  - Bollinger Bands
- **Portfolio Management**: Track positions, cash balance, and P&L
- **Trade Execution**: Simulate buy/sell orders
- **Trading Signals**: Generate buy/sell signals based on selected strategies
- **Automated Trading Bot**: Start/stop automated trading with configurable parameters

## Installation

```bash
cd trading_bot
poetry install
```

## Running the Server

```bash
poetry run fastapi dev app/main.py
```

The server will start at http://localhost:8000

## API Endpoints

### Stock Data
- `GET /api/stocks/{symbol}` - Get current stock data
- `GET /api/stocks/{symbol}/history` - Get historical stock data

### Portfolio
- `GET /api/portfolio` - Get current portfolio status
- `POST /api/portfolio/reset` - Reset portfolio with initial cash

### Trading
- `POST /api/trade` - Execute a trade (buy/sell)
- `GET /api/trades` - Get trade history

### Signals & Strategies
- `GET /api/signals/{symbol}` - Get trading signals for a symbol
- `GET /api/strategies` - List available trading strategies

### Bot Control
- `GET /api/bot/status` - Get bot status
- `POST /api/bot/start` - Start the trading bot
- `POST /api/bot/stop` - Stop the trading bot
- `POST /api/bot/check` - Check signals for watched symbols

## Example Usage

### Get Stock Data
```bash
curl http://localhost:8000/api/stocks/AAPL
```

### Execute a Trade
```bash
curl -X POST http://localhost:8000/api/trade \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","action":"buy","quantity":10}'
```

### Start Trading Bot
```bash
curl -X POST http://localhost:8000/api/bot/start \
  -H "Content-Type: application/json" \
  -d '{"symbols":["AAPL","GOOGL","MSFT"],"strategy":"sma_crossover","auto_trade":false}'
```

### Get Trading Signal
```bash
curl http://localhost:8000/api/signals/AAPL?strategy=rsi
```

## Note

This is a prototype/proof-of-concept implementation using in-memory storage. Data will be lost when the server restarts. For production use, consider adding persistent database storage.

## API Documentation

Once the server is running, visit http://localhost:8000/docs for interactive API documentation (Swagger UI).
