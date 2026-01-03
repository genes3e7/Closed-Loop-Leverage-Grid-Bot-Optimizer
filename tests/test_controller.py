"""
Integration tests for src/controller.py
Focus: Orchestration flow and typo correction.
"""

import pytest
from unittest.mock import patch
from src.controller import resolve_exchange, run_analysis


def test_resolve_exchange_typo():
    """Test auto-correction of exchange names."""
    # We patch ccxt.exchanges to ensure the test is deterministic
    # regardless of the installed ccxt version
    with patch("ccxt.exchanges", ["binance", "pionex", "kraken"]):
        # 'binnace' -> 'binance'
        assert resolve_exchange("binnace") == "binance"
        # 'pionex' -> 'pionex' (exact match)
        assert resolve_exchange("pionex") == "pionex"
        # 'totally_wrong' -> 'totally_wrong' (no match found)
        assert resolve_exchange("totally_wrong") == "totally_wrong"


@patch("src.controller.ExchangeSniffer")
@patch("src.controller.MarketAnalyzer")
@patch("src.controller.ClosedLoopOptimizer")
def test_run_analysis_flow(MockOpt, MockAnalyzer, MockSniffer):
    """Test the full run_analysis function end-to-end with mocks."""

    # Setup Mocks
    mock_sniffer = MockSniffer.return_value
    mock_sniffer.get_market_intelligence.return_value = {
        "current_price": 100,
        "maker_fee": 0.001,
        "spread_pct": 0.0,
    }

    mock_analyzer = MockAnalyzer.return_value
    mock_analyzer.calculate_metrics.return_value = {
        "sigma_daily": 0.05,
        "mu_daily": 0.0,
        "atr": 2.0,
        "current_price": 100,
    }

    mock_opt = MockOpt.return_value
    mock_opt.calculate_bounds.return_value = {"upper_bound": 110, "lower_bound": 90}
    # Fix: Provide a float return value for grid_step to avoid f-string format error
    mock_opt.calculate_grid_step.return_value = 0.01
    mock_opt.closed_loop_allocation.return_value = {
        "action": "TRADE",
        "target_liq_price": 80,
        "max_safe_leverage": 3.0,
        "required_margin_transfer": 100,
        "total_exposure": 300,
        "entry_price": 100,  # Fix: Added entry_price to mock
    }

    # Run Function
    try:
        run_analysis("BTC/USDT", "binance", 7, 1000)
    except SystemExit:
        pytest.fail("run_analysis triggered SystemExit (Crash)")

    # Assertions to ensure flow happened
    mock_sniffer.get_market_intelligence.assert_called_once()
    mock_analyzer.fetch_history.assert_called_once()
    mock_opt.closed_loop_allocation.assert_called_once()
