import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Optional
from app.models import TradingSignal, Strategy


class StrategyService:
    def __init__(self):
        self.strategies = {
            "sma_crossover": Strategy(
                name="SMA Crossover",
                description="Simple Moving Average Crossover strategy. Generates buy signal when short-term SMA crosses above long-term SMA, and sell signal when it crosses below.",
                parameters={"short_period": 10, "long_period": 30}
            ),
            "rsi": Strategy(
                name="RSI",
                description="Relative Strength Index strategy. Generates buy signal when RSI is below oversold level (30), and sell signal when RSI is above overbought level (70).",
                parameters={"period": 14, "oversold": 30, "overbought": 70}
            ),
            "macd": Strategy(
                name="MACD",
                description="Moving Average Convergence Divergence strategy. Generates signals based on MACD line crossing signal line.",
                parameters={"fast_period": 12, "slow_period": 26, "signal_period": 9}
            ),
            "bollinger_bands": Strategy(
                name="Bollinger Bands",
                description="Bollinger Bands strategy. Generates buy signal when price touches lower band, sell signal when price touches upper band.",
                parameters={"period": 20, "std_dev": 2}
            )
        }

    def get_strategies(self) -> list[Strategy]:
        return list(self.strategies.values())

    def get_signal(self, symbol: str, strategy_name: str = "sma_crossover") -> Optional[TradingSignal]:
        symbol = symbol.upper()
        
        if strategy_name not in self.strategies:
            return None

        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="3mo", interval="1d")
            
            if hist.empty or len(hist) < 30:
                return None

            current_price = float(hist['Close'].iloc[-1])
            
            if strategy_name == "sma_crossover":
                return self._sma_crossover_signal(symbol, hist, current_price)
            elif strategy_name == "rsi":
                return self._rsi_signal(symbol, hist, current_price)
            elif strategy_name == "macd":
                return self._macd_signal(symbol, hist, current_price)
            elif strategy_name == "bollinger_bands":
                return self._bollinger_bands_signal(symbol, hist, current_price)
            
            return None
            
        except Exception as e:
            print(f"Error generating signal for {symbol}: {e}")
            return None

    def _sma_crossover_signal(self, symbol: str, hist: pd.DataFrame, current_price: float) -> TradingSignal:
        params = self.strategies["sma_crossover"].parameters
        short_period = params["short_period"]
        long_period = params["long_period"]
        
        hist['SMA_short'] = hist['Close'].rolling(window=short_period).mean()
        hist['SMA_long'] = hist['Close'].rolling(window=long_period).mean()
        
        current_short = hist['SMA_short'].iloc[-1]
        current_long = hist['SMA_long'].iloc[-1]
        prev_short = hist['SMA_short'].iloc[-2]
        prev_long = hist['SMA_long'].iloc[-2]
        
        if prev_short <= prev_long and current_short > current_long:
            signal = "BUY"
            confidence = min(0.9, 0.5 + (current_short - current_long) / current_long * 10)
        elif prev_short >= prev_long and current_short < current_long:
            signal = "SELL"
            confidence = min(0.9, 0.5 + (current_long - current_short) / current_long * 10)
        elif current_short > current_long:
            signal = "HOLD_BULLISH"
            confidence = 0.5 + (current_short - current_long) / current_long * 5
        else:
            signal = "HOLD_BEARISH"
            confidence = 0.5 + (current_long - current_short) / current_long * 5
        
        return TradingSignal(
            symbol=symbol,
            signal=signal,
            strategy="SMA Crossover",
            confidence=round(min(confidence, 1.0), 2),
            current_price=round(current_price, 2),
            timestamp=datetime.now(),
            details={
                "short_sma": round(current_short, 2),
                "long_sma": round(current_long, 2),
                "short_period": short_period,
                "long_period": long_period
            }
        )

    def _rsi_signal(self, symbol: str, hist: pd.DataFrame, current_price: float) -> TradingSignal:
        params = self.strategies["rsi"].parameters
        period = params["period"]
        oversold = params["oversold"]
        overbought = params["overbought"]
        
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        if current_rsi < oversold:
            signal = "BUY"
            confidence = 0.5 + (oversold - current_rsi) / oversold * 0.4
        elif current_rsi > overbought:
            signal = "SELL"
            confidence = 0.5 + (current_rsi - overbought) / (100 - overbought) * 0.4
        elif current_rsi < 50:
            signal = "HOLD_BULLISH"
            confidence = 0.4
        else:
            signal = "HOLD_BEARISH"
            confidence = 0.4
        
        return TradingSignal(
            symbol=symbol,
            signal=signal,
            strategy="RSI",
            confidence=round(min(confidence, 1.0), 2),
            current_price=round(current_price, 2),
            timestamp=datetime.now(),
            details={
                "rsi": round(current_rsi, 2),
                "oversold_level": oversold,
                "overbought_level": overbought
            }
        )

    def _macd_signal(self, symbol: str, hist: pd.DataFrame, current_price: float) -> TradingSignal:
        params = self.strategies["macd"].parameters
        fast = params["fast_period"]
        slow = params["slow_period"]
        signal_period = params["signal_period"]
        
        exp1 = hist['Close'].ewm(span=fast, adjust=False).mean()
        exp2 = hist['Close'].ewm(span=slow, adjust=False).mean()
        macd_line = exp1 - exp2
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line
        
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        prev_signal = signal_line.iloc[-2]
        
        if prev_macd <= prev_signal and current_macd > current_signal:
            signal = "BUY"
            confidence = 0.7
        elif prev_macd >= prev_signal and current_macd < current_signal:
            signal = "SELL"
            confidence = 0.7
        elif current_macd > current_signal:
            signal = "HOLD_BULLISH"
            confidence = 0.5
        else:
            signal = "HOLD_BEARISH"
            confidence = 0.5
        
        return TradingSignal(
            symbol=symbol,
            signal=signal,
            strategy="MACD",
            confidence=round(confidence, 2),
            current_price=round(current_price, 2),
            timestamp=datetime.now(),
            details={
                "macd": round(current_macd, 2),
                "signal_line": round(current_signal, 2),
                "histogram": round(histogram.iloc[-1], 2)
            }
        )

    def _bollinger_bands_signal(self, symbol: str, hist: pd.DataFrame, current_price: float) -> TradingSignal:
        params = self.strategies["bollinger_bands"].parameters
        period = params["period"]
        std_dev = params["std_dev"]
        
        sma = hist['Close'].rolling(window=period).mean()
        std = hist['Close'].rolling(window=period).std()
        
        upper_band = sma + (std * std_dev)
        lower_band = sma - (std * std_dev)
        
        current_upper = upper_band.iloc[-1]
        current_lower = lower_band.iloc[-1]
        current_sma = sma.iloc[-1]
        
        if current_price <= current_lower:
            signal = "BUY"
            confidence = 0.7
        elif current_price >= current_upper:
            signal = "SELL"
            confidence = 0.7
        elif current_price < current_sma:
            signal = "HOLD_BULLISH"
            confidence = 0.4
        else:
            signal = "HOLD_BEARISH"
            confidence = 0.4
        
        return TradingSignal(
            symbol=symbol,
            signal=signal,
            strategy="Bollinger Bands",
            confidence=round(confidence, 2),
            current_price=round(current_price, 2),
            timestamp=datetime.now(),
            details={
                "upper_band": round(current_upper, 2),
                "lower_band": round(current_lower, 2),
                "middle_band": round(current_sma, 2)
            }
        )


strategy_service = StrategyService()
