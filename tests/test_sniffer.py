"""
Unit tests for src/sniffer.py
Focus: API resilience, default fallbacks, and error handling.
"""

from unittest.mock import patch
from src.sniffer import ExchangeSniffer


class TestExchangeSniffer:
    def test_init_valid_exchange(self):
        """Test CCXT initialization."""
        sniffer = ExchangeSniffer("binance")
        assert sniffer.exchange is not None

    def test_init_invalid_exchange(self):
        """Test passing a nonsense exchange ID (Should default to Offline Mode)."""
        # Fix: Offline mode does not raise, it returns None
        sniffer = ExchangeSniffer("fake_exchange_123")
        assert sniffer.exchange is None

    def test_get_intelligence_full_success(self, mock_ccxt_exchange):
        """Test sniffing when API returns everything perfectly."""
        # Mock API returns
        mock_ccxt_exchange.fetch_trading_fees.return_value = {
            "BTC/USDT": {"maker": 0.002, "taker": 0.004}
        }
        mock_ccxt_exchange.fetch_ticker.return_value = {
            "bid": 99.0,
            "ask": 101.0,
            "last": 100.0,
        }
        mock_ccxt_exchange.fetch_funding_rate.return_value = {"fundingRate": 0.0005}

        with patch("ccxt.binance", return_value=mock_ccxt_exchange):
            sniffer = ExchangeSniffer("binance")
            data = sniffer.get_market_intelligence("BTC/USDT")

            assert data["maker_fee"] == 0.002
            assert data["spread_pct"] > 0
            assert data["funding_rate_8h"] == 0.0005

    def test_get_intelligence_api_failure(self, mock_ccxt_exchange):
        """Test sniffing when API throws errors (should return defaults)."""
        # API raises exception on call
        mock_ccxt_exchange.fetch_trading_fees.side_effect = Exception("API Down")
        mock_ccxt_exchange.fetch_funding_rate.side_effect = Exception("API Down")

        with patch("ccxt.binance", return_value=mock_ccxt_exchange):
            sniffer = ExchangeSniffer("binance")
            data = sniffer.get_market_intelligence("BTC/USDT")

            # Should fall back to defaults defined in sniffer.py
            assert data["maker_fee"] == 0.001
            assert data["funding_rate_8h"] == 0.0001

    def test_get_intelligence_symbol_not_found(self, mock_ccxt_exchange):
        """Test sniffing for a symbol that doesn't exist on the exchange."""
        mock_ccxt_exchange.markets = {"BTC/USDT": {}}

        # FIXED: Ensure fetching fees for invalid symbol raises exception
        def side_effect_fees(symbols):
            if "ETH/USDT" in symbols:
                raise Exception("Symbol not found")
            return {"BTC/USDT": {"maker": 0.002, "taker": 0.004}}

        mock_ccxt_exchange.fetch_trading_fees.side_effect = side_effect_fees

        with patch("ccxt.binance", return_value=mock_ccxt_exchange):
            sniffer = ExchangeSniffer("binance")
            data = sniffer.get_market_intelligence("ETH/USDT")  # Invalid

            # Should handle gracefully (return defaults)
            assert data["maker_fee"] == 0.001
