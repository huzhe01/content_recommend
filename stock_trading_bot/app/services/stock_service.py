import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional
from app.models import StockData, StockHistory


class StockService:
    def __init__(self):
        self._cache: dict[str, tuple[StockData, datetime]] = {}
        self._cache_duration = timedelta(minutes=1)

    def get_stock_data(self, symbol: str) -> Optional[StockData]:
        symbol = symbol.upper()
        
        if symbol in self._cache:
            cached_data, cached_time = self._cache[symbol]
            if datetime.now() - cached_time < self._cache_duration:
                return cached_data

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info or 'currentPrice' not in info and 'regularMarketPrice' not in info:
                hist = ticker.history(period="1d")
                if hist.empty:
                    return None
                current_price = float(hist['Close'].iloc[-1])
                open_price = float(hist['Open'].iloc[-1])
                high_price = float(hist['High'].iloc[-1])
                low_price = float(hist['Low'].iloc[-1])
                volume = int(hist['Volume'].iloc[-1])
                previous_close = float(hist['Close'].iloc[0]) if len(hist) > 1 else current_price
            else:
                current_price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
                open_price = info.get('open') or info.get('regularMarketOpen', 0)
                high_price = info.get('dayHigh') or info.get('regularMarketDayHigh', 0)
                low_price = info.get('dayLow') or info.get('regularMarketDayLow', 0)
                volume = info.get('volume') or info.get('regularMarketVolume', 0)
                previous_close = info.get('previousClose') or info.get('regularMarketPreviousClose', current_price)

            change = current_price - previous_close
            change_percent = (change / previous_close * 100) if previous_close else 0

            stock_data = StockData(
                symbol=symbol,
                current_price=current_price,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                volume=volume,
                previous_close=previous_close,
                change=round(change, 2),
                change_percent=round(change_percent, 2),
                timestamp=datetime.now()
            )
            
            self._cache[symbol] = (stock_data, datetime.now())
            return stock_data
            
        except Exception as e:
            print(f"Error fetching stock data for {symbol}: {e}")
            return None

    def get_stock_history(self, symbol: str, period: str = "1mo", interval: str = "1d") -> Optional[StockHistory]:
        symbol = symbol.upper()
        
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                return None
            
            data = []
            for index, row in hist.iterrows():
                data.append({
                    "date": index.strftime("%Y-%m-%d"),
                    "open": round(row['Open'], 2),
                    "high": round(row['High'], 2),
                    "low": round(row['Low'], 2),
                    "close": round(row['Close'], 2),
                    "volume": int(row['Volume'])
                })
            
            return StockHistory(symbol=symbol, data=data)
            
        except Exception as e:
            print(f"Error fetching stock history for {symbol}: {e}")
            return None

    def get_current_price(self, symbol: str) -> Optional[float]:
        stock_data = self.get_stock_data(symbol)
        return stock_data.current_price if stock_data else None


stock_service = StockService()
