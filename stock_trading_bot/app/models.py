from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class TradeAction(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TradeRequest(BaseModel):
    symbol: str
    action: TradeAction
    quantity: int
    price: Optional[float] = None


class Trade(BaseModel):
    id: str
    symbol: str
    action: TradeAction
    quantity: int
    price: float
    total_value: float
    timestamp: datetime


class Position(BaseModel):
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    market_value: float
    unrealized_pnl: float
    unrealized_pnl_percent: float


class Portfolio(BaseModel):
    cash_balance: float
    total_value: float
    positions: list[Position]
    total_unrealized_pnl: float


class StockData(BaseModel):
    symbol: str
    current_price: float
    open_price: float
    high_price: float
    low_price: float
    volume: int
    previous_close: float
    change: float
    change_percent: float
    timestamp: datetime


class StockHistory(BaseModel):
    symbol: str
    data: list[dict]


class TradingSignal(BaseModel):
    symbol: str
    signal: str
    strategy: str
    confidence: float
    current_price: float
    timestamp: datetime
    details: dict


class Strategy(BaseModel):
    name: str
    description: str
    parameters: dict


class BotStatus(BaseModel):
    is_running: bool
    strategy: Optional[str]
    watched_symbols: list[str]
    last_check: Optional[datetime]
    total_trades: int
