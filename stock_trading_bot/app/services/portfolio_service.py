import uuid
from datetime import datetime
from typing import Optional
from app.models import Trade, TradeAction, Position, Portfolio, TradeRequest
from app.services.stock_service import stock_service


class PortfolioService:
    def __init__(self, initial_cash: float = 100000.0):
        self.cash_balance = initial_cash
        self.positions: dict[str, dict] = {}
        self.trades: list[Trade] = []

    def get_portfolio(self) -> Portfolio:
        positions = []
        total_unrealized_pnl = 0.0
        
        for symbol, pos_data in self.positions.items():
            if pos_data["quantity"] <= 0:
                continue
                
            current_price = stock_service.get_current_price(symbol)
            if current_price is None:
                current_price = pos_data["average_price"]
            
            market_value = pos_data["quantity"] * current_price
            cost_basis = pos_data["quantity"] * pos_data["average_price"]
            unrealized_pnl = market_value - cost_basis
            unrealized_pnl_percent = (unrealized_pnl / cost_basis * 100) if cost_basis > 0 else 0
            
            position = Position(
                symbol=symbol,
                quantity=pos_data["quantity"],
                average_price=round(pos_data["average_price"], 2),
                current_price=round(current_price, 2),
                market_value=round(market_value, 2),
                unrealized_pnl=round(unrealized_pnl, 2),
                unrealized_pnl_percent=round(unrealized_pnl_percent, 2)
            )
            positions.append(position)
            total_unrealized_pnl += unrealized_pnl
        
        total_positions_value = sum(p.market_value for p in positions)
        total_value = self.cash_balance + total_positions_value
        
        return Portfolio(
            cash_balance=round(self.cash_balance, 2),
            total_value=round(total_value, 2),
            positions=positions,
            total_unrealized_pnl=round(total_unrealized_pnl, 2)
        )

    def execute_trade(self, trade_request: TradeRequest) -> Optional[Trade]:
        symbol = trade_request.symbol.upper()
        
        if trade_request.price:
            price = trade_request.price
        else:
            price = stock_service.get_current_price(symbol)
            if price is None:
                return None
        
        total_value = price * trade_request.quantity
        
        if trade_request.action == TradeAction.BUY:
            if total_value > self.cash_balance:
                return None
            
            self.cash_balance -= total_value
            
            if symbol in self.positions:
                existing = self.positions[symbol]
                total_quantity = existing["quantity"] + trade_request.quantity
                total_cost = (existing["quantity"] * existing["average_price"]) + total_value
                self.positions[symbol] = {
                    "quantity": total_quantity,
                    "average_price": total_cost / total_quantity
                }
            else:
                self.positions[symbol] = {
                    "quantity": trade_request.quantity,
                    "average_price": price
                }
        
        elif trade_request.action == TradeAction.SELL:
            if symbol not in self.positions or self.positions[symbol]["quantity"] < trade_request.quantity:
                return None
            
            self.cash_balance += total_value
            self.positions[symbol]["quantity"] -= trade_request.quantity
            
            if self.positions[symbol]["quantity"] == 0:
                del self.positions[symbol]
        
        trade = Trade(
            id=str(uuid.uuid4()),
            symbol=symbol,
            action=trade_request.action,
            quantity=trade_request.quantity,
            price=round(price, 2),
            total_value=round(total_value, 2),
            timestamp=datetime.now()
        )
        self.trades.append(trade)
        
        return trade

    def get_trades(self) -> list[Trade]:
        return self.trades

    def get_position(self, symbol: str) -> Optional[dict]:
        symbol = symbol.upper()
        return self.positions.get(symbol)

    def reset(self, initial_cash: float = 100000.0):
        self.cash_balance = initial_cash
        self.positions = {}
        self.trades = []


portfolio_service = PortfolioService()
