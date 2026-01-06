"""
Integration tests mocking external APIs.
"""

from unittest.mock import patch

import pytest

from src.analyzer import MarketAnalyzer
from src.sniffer import ExchangeSniffer


@pytest.fixture
def mock_yfinance_data():
    """Create a mock DataFrame for YFinance."""
    import numpy as np
    import pandas as pd

    dates = pd.date_range(start="2023-01-01", periods=100)
    # Create a random walk
    np.random.seed(42)
    returns = np.random.normal(0, 0.02, 100)
    price = 100 * np.exp(np.cumsum(returns))

    df = pd.DataFrame(
        {"Close": price, "High": price * 1.05, "Low": price * 0.95, "Open": price},
        index=dates,
    )
    return df


def test_analyzer_flow(mock_yfinance_data):
    """Test full analysis flow with mocked data."""
    with patch("yfinance.download", return_value=mock_yfinance_data):
        analyzer = MarketAnalyzer("BTC")
        analyzer.fetch_history(90)
        metrics = analyzer.calculate_metrics()

        assert metrics["current_price"] > 0
        assert metrics["sigma_daily"] > 0
        assert metrics["atr"] > 0


def test_sniffer_defensive_defaults():
    """Test that sniffer returns safe defaults if exchange fails."""
    # Initialize with a non-existent exchange to trigger base errors or mocking
    with patch("ccxt.binance") as mock_ex:
        # FIXED: Configure all methods to raise Exceptions
        exchange_instance = mock_ex.return_value
        exchange_instance.fetch_ticker.side_effect = Exception("API Down")
        exchange_instance.fetch_trading_fees.side_effect = Exception("API Down")
        exchange_instance.fetch_funding_rate.side_effect = Exception("API Down")

        # Ensure capabilities are True so it attempts the calls
        exchange_instance.has = {"fetchTradingFees": True, "fetchFundingRate": True}

        sniffer = ExchangeSniffer("binance")
        intel = sniffer.get_market_intelligence("BTC/USDT")

        # Should return defaults, not crash
        assert intel["maker_fee"] == 0.001
        assert intel["funding_rate_8h"] == 0.0001
