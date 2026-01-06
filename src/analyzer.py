"""
Module for historical market analysis (Volatility, ATR, Drift).
"""

import numpy as np
import pandas as pd
import yfinance as yf


class MarketAnalyzer:
    """
    Analyzes historical price data to derive 'The Volatility Cone'.
    """

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.data = pd.DataFrame()

    def fetch_history(self, days: int = 90) -> None:
        """Fetches historical data from YFinance with error handling."""
        try:
            # Add 'd' suffix if missing for yfinance crypto format usually
            symbol = self.ticker if self.ticker.endswith("-USD") else f"{self.ticker}-USD"

            # Defensive: Fetch a bit more to ensure we have valid periods for ATR
            self.data = yf.download(symbol, period=f"{days}d", progress=False)

            if self.data.empty:
                print(
                    f"ℹ️ Note: '{symbol}' data not found. "
                    f"Defaulting to raw ticker '{self.ticker}'..."
                )
                # Fallback attempt without -USD suffix
                self.data = yf.download(self.ticker, period=f"{days}d", progress=False)

            if self.data.empty:
                raise ValueError(f"No data returned for {self.ticker}")

            # Handle MultiIndex columns if YF returns them
            if isinstance(self.data.columns, pd.MultiIndex):
                self.data.columns = self.data.columns.get_level_values(0)

        except Exception as e:
            # We catch specific library errors or re-raise
            # If it is already a ValueError (from above), re-raise it directly
            if isinstance(e, ValueError):
                raise e
            raise RuntimeError(f"❌ Failed to fetch market data: {str(e)}") from e

    def calculate_metrics(self) -> dict[str, float]:
        """
        Calculates Volatility, Drift, and ATR.
        """
        if self.data.empty:
            raise ValueError("No data loaded. Call fetch_history() first.")

        # Pre-calc validation
        if "Close" not in self.data.columns:
            raise ValueError("Malformed data: Missing 'Close' column")

        # 1. Log Returns
        # Use simple numeric extraction to avoid Series alignment issues
        close_prices = self.data["Close"].values.astype(float)

        # Guard against zero/negative prices
        if np.any(close_prices <= 0):
            raise ValueError("Data contains zero or negative prices.")

        log_rets = np.diff(np.log(close_prices))

        # 2. Volatility (Daily Sigma) & Drift (Mu)
        sigma_daily = float(np.std(log_rets))
        mu_daily = float(np.mean(log_rets))

        # 3. ATR (Average True Range) - 14 period
        high = self.data["High"].values.astype(float)
        low = self.data["Low"].values.astype(float)
        prev_close = np.roll(close_prices, 1)
        prev_close[0] = close_prices[0]  # Fix first element

        tr1 = high - low
        tr2 = np.abs(high - prev_close)
        tr3 = np.abs(low - prev_close)

        true_range = np.maximum(tr1, np.maximum(tr2, tr3))
        # Simple Moving Average for ATR
        atr = float(np.mean(true_range[-14:]))

        return {
            "current_price": float(close_prices[-1]),
            "sigma_daily": sigma_daily,
            "mu_daily": mu_daily,
            "atr": atr,
        }
