from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from pydantic import BaseModel

from app.models import TradeRequest, TradeAction
from app.services.stock_service import stock_service
from app.services.strategy_service import strategy_service
from app.services.portfolio_service import portfolio_service
from app.services.bot_service import bot_service

app = FastAPI(
    title="Stock Trading Bot API",
    description="A stock trading bot API with automated trading strategies",
    version="1.0.0"
)

# Disable CORS. Do not remove this for full-stack development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)


class BotStartRequest(BaseModel):
    symbols: list[str]
    strategy: str = "sma_crossover"
    auto_trade: bool = False
    trade_amount: float = 1000.0


class PortfolioResetRequest(BaseModel):
    initial_cash: float = 100000.0


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {
        "message": "Stock Trading Bot API",
        "version": "1.0.0",
        "endpoints": {
            "stocks": "/api/stocks/{symbol}",
            "stock_history": "/api/stocks/{symbol}/history",
            "portfolio": "/api/portfolio",
            "trade": "/api/trade",
            "trades": "/api/trades",
            "signals": "/api/signals/{symbol}",
            "strategies": "/api/strategies",
            "bot_status": "/api/bot/status",
            "bot_start": "/api/bot/start",
            "bot_stop": "/api/bot/stop",
            "bot_check": "/api/bot/check"
        }
    }


@app.get("/api/stocks/{symbol}")
async def get_stock(symbol: str):
    stock_data = stock_service.get_stock_data(symbol)
    if not stock_data:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    return stock_data


@app.get("/api/stocks/{symbol}/history")
async def get_stock_history(symbol: str, period: str = "1mo", interval: str = "1d"):
    history = stock_service.get_stock_history(symbol, period, interval)
    if not history:
        raise HTTPException(status_code=404, detail=f"Stock history for {symbol} not found")
    return history


@app.get("/api/portfolio")
async def get_portfolio():
    return portfolio_service.get_portfolio()


@app.post("/api/portfolio/reset")
async def reset_portfolio(request: PortfolioResetRequest):
    portfolio_service.reset(request.initial_cash)
    return {"message": "Portfolio reset successfully", "initial_cash": request.initial_cash}


@app.post("/api/trade")
async def execute_trade(trade_request: TradeRequest):
    trade = portfolio_service.execute_trade(trade_request)
    if not trade:
        if trade_request.action == TradeAction.BUY:
            raise HTTPException(status_code=400, detail="Insufficient funds or invalid stock symbol")
        else:
            raise HTTPException(status_code=400, detail="Insufficient shares or position not found")
    return trade


@app.get("/api/trades")
async def get_trades():
    return {"trades": portfolio_service.get_trades()}


@app.get("/api/signals/{symbol}")
async def get_signal(symbol: str, strategy: str = "sma_crossover"):
    signal = strategy_service.get_signal(symbol, strategy)
    if not signal:
        raise HTTPException(status_code=404, detail=f"Could not generate signal for {symbol}")
    return signal


@app.get("/api/strategies")
async def get_strategies():
    return {"strategies": strategy_service.get_strategies()}


@app.get("/api/bot/status")
async def get_bot_status():
    return bot_service.get_status()


@app.post("/api/bot/start")
async def start_bot(request: BotStartRequest):
    if not request.symbols:
        raise HTTPException(status_code=400, detail="At least one symbol is required")
    return bot_service.start(
        symbols=request.symbols,
        strategy=request.strategy,
        auto_trade=request.auto_trade,
        trade_amount=request.trade_amount
    )


@app.post("/api/bot/stop")
async def stop_bot():
    return bot_service.stop()


@app.post("/api/bot/check")
async def check_bot_signals():
    if not bot_service.is_running:
        raise HTTPException(status_code=400, detail="Bot is not running")
    return {"signals": bot_service.check_signals()}


@app.post("/api/bot/symbol/{symbol}")
async def add_symbol(symbol: str):
    return bot_service.add_symbol(symbol)


@app.delete("/api/bot/symbol/{symbol}")
async def remove_symbol(symbol: str):
    return bot_service.remove_symbol(symbol)


@app.put("/api/bot/strategy/{strategy}")
async def set_strategy(strategy: str):
    if strategy not in strategy_service.strategies:
        raise HTTPException(status_code=400, detail=f"Strategy {strategy} not found")
    return bot_service.set_strategy(strategy)
