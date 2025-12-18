from datetime import datetime
from typing import Optional
from app.models import BotStatus, TradeRequest, TradeAction
from app.services.strategy_service import strategy_service
from app.services.portfolio_service import portfolio_service


class TradingBotService:
    def __init__(self):
        self.is_running = False
        self.current_strategy = "sma_crossover"
        self.watched_symbols: list[str] = []
        self.last_check: Optional[datetime] = None
        self.auto_trade = False
        self.trade_amount = 1000.0

    def start(self, symbols: list[str], strategy: str = "sma_crossover", auto_trade: bool = False, trade_amount: float = 1000.0) -> BotStatus:
        self.is_running = True
        self.watched_symbols = [s.upper() for s in symbols]
        self.current_strategy = strategy
        self.auto_trade = auto_trade
        self.trade_amount = trade_amount
        self.last_check = datetime.now()
        return self.get_status()

    def stop(self) -> BotStatus:
        self.is_running = False
        return self.get_status()

    def get_status(self) -> BotStatus:
        return BotStatus(
            is_running=self.is_running,
            strategy=self.current_strategy if self.is_running else None,
            watched_symbols=self.watched_symbols,
            last_check=self.last_check,
            total_trades=len(portfolio_service.trades)
        )

    def check_signals(self) -> list[dict]:
        if not self.is_running:
            return []
        
        results = []
        self.last_check = datetime.now()
        
        for symbol in self.watched_symbols:
            signal = strategy_service.get_signal(symbol, self.current_strategy)
            if signal:
                result = {
                    "symbol": symbol,
                    "signal": signal.signal,
                    "confidence": signal.confidence,
                    "current_price": signal.current_price,
                    "details": signal.details,
                    "trade_executed": False
                }
                
                if self.auto_trade and signal.confidence >= 0.6:
                    trade = self._execute_signal(symbol, signal.signal, signal.current_price)
                    if trade:
                        result["trade_executed"] = True
                        result["trade"] = {
                            "id": trade.id,
                            "action": trade.action,
                            "quantity": trade.quantity,
                            "price": trade.price,
                            "total_value": trade.total_value
                        }
                
                results.append(result)
        
        return results

    def _execute_signal(self, symbol: str, signal: str, price: float) -> Optional[any]:
        if signal == "BUY":
            quantity = int(self.trade_amount / price)
            if quantity > 0:
                trade_request = TradeRequest(
                    symbol=symbol,
                    action=TradeAction.BUY,
                    quantity=quantity,
                    price=price
                )
                return portfolio_service.execute_trade(trade_request)
        
        elif signal == "SELL":
            position = portfolio_service.get_position(symbol)
            if position and position["quantity"] > 0:
                trade_request = TradeRequest(
                    symbol=symbol,
                    action=TradeAction.SELL,
                    quantity=position["quantity"],
                    price=price
                )
                return portfolio_service.execute_trade(trade_request)
        
        return None

    def add_symbol(self, symbol: str) -> BotStatus:
        symbol = symbol.upper()
        if symbol not in self.watched_symbols:
            self.watched_symbols.append(symbol)
        return self.get_status()

    def remove_symbol(self, symbol: str) -> BotStatus:
        symbol = symbol.upper()
        if symbol in self.watched_symbols:
            self.watched_symbols.remove(symbol)
        return self.get_status()

    def set_strategy(self, strategy: str) -> BotStatus:
        if strategy in strategy_service.strategies:
            self.current_strategy = strategy
        return self.get_status()


bot_service = TradingBotService()
