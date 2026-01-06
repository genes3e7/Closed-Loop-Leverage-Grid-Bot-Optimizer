"""
Unit tests for src/analyzer.py
Focus: Data fetching, handling NaNs/Zeros, and calculating statistical metrics.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from src.analyzer import MarketAnalyzer


class TestMarketAnalyzer:
    def test_fetch_history_success(self, mock_ohlcv_data):
        """Test successful data loading from yfinance."""
        with patch("yfinance.download", return_value=mock_ohlcv_data):
            analyzer = MarketAnalyzer("BTC")
            analyzer.fetch_history(90)
            assert not analyzer.data.empty
            assert "Close" in analyzer.data.columns

    def test_fetch_history_empty_response(self):
        """Test handling of ticker not found (empty DF)."""
        empty_df = pd.DataFrame()
        with patch("yfinance.download", return_value=empty_df):
            analyzer = MarketAnalyzer("INVALID")
            # FIXED: Expect ValueError as raised by the implementation
            with pytest.raises(ValueError, match="No data returned"):
                analyzer.fetch_history(90)

    def test_fetch_history_network_error(self):
        """Test handling of network/library exceptions."""
        with patch("yfinance.download", side_effect=Exception("Connection Reset")):
            analyzer = MarketAnalyzer("BTC")
            with pytest.raises(RuntimeError, match="Failed to fetch"):
                analyzer.fetch_history(90)

    def test_calculate_metrics_normal(self, mock_ohlcv_data):
        """Test calculation of Volatility, Drift, and ATR."""
        analyzer = MarketAnalyzer("BTC")
        analyzer.data = mock_ohlcv_data

        metrics = analyzer.calculate_metrics()

        assert metrics["sigma_daily"] > 0
        assert isinstance(metrics["mu_daily"], float)
        assert metrics["atr"] > 0
        assert metrics["current_price"] > 0

    def test_calculate_metrics_zeros_in_price(self, mock_malformed_data):
        """
        CRITICAL: Zeros in price data cause log(0) = -inf.
        Analyzer should detect this and raise a clear error.
        """
        analyzer = MarketAnalyzer("BTC")
        analyzer.data = mock_malformed_data

        with pytest.raises(ValueError, match="zero or negative"):
            analyzer.calculate_metrics()

    def test_calculate_metrics_no_data(self):
        """Defensive: Calling calculate before fetch."""
        analyzer = MarketAnalyzer("BTC")
        with pytest.raises(ValueError, match="No data loaded"):
            analyzer.calculate_metrics()
