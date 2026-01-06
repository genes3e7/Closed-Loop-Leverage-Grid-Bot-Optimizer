"""
Tests specifically for the Drift Detection and Auto-Recovery logic in the Controller.
"""

from unittest.mock import patch

from src.controller import run_analysis


@patch("src.controller.ExchangeSniffer")
@patch("src.controller.MarketAnalyzer")
@patch("src.controller.ClosedLoopOptimizer")
@patch("src.controller.print_strategy_report")
def test_auto_neutral_switch_triggered(mock_report, MockOpt, MockAnalyzer, MockSniffer):
    """
    Scenario: Bearish Drift detected (Upper Bound < Current Price).
    Expected:
    1. Controller detects the condition.
    2. Controller prints warning (we won't assert print, but implied by logic flow).
    3. Controller sets metrics['mu_daily'] = 0.0.
    4. Controller RE-CALCULATES bounds with new drift.
    5. Report is generated with the NEW bounds.
    """
    # 1. Setup Data
    current_price = 100.0

    # Mocks
    mock_sniffer = MockSniffer.return_value
    mock_sniffer.get_market_intelligence.return_value = {
        "current_price": current_price,
        "maker_fee": 0.001,
        "spread_pct": 0.0,
        "funding_rate_8h": 0.0,
    }

    mock_analyzer = MockAnalyzer.return_value
    # Initial metrics with negative drift
    metrics_dict = {
        "sigma_daily": 0.05,
        "mu_daily": -0.05,  # Heavy bearish drift
        "atr": 5.0,
        "current_price": current_price,
    }
    mock_analyzer.calculate_metrics.return_value = metrics_dict

    mock_opt_instance = MockOpt.return_value
    mock_opt_instance.calculate_grid_step.return_value = 0.01
    mock_opt_instance.calculate_grid_quantity.return_value = 10
    mock_opt_instance.calculate_min_capital.return_value = 100
    mock_opt_instance.closed_loop_allocation.return_value = {
        "action": "TRADE",
        "entry_price": current_price,
    }

    # 2. Setup Bounds Calculation Side Effects
    # First call: Returns bounds BELOW current price (Triggering Drift Logic)
    # Second call: Returns corrected bounds (Neutral)
    bad_bounds = {"upper_bound": 90.0, "lower_bound": 80.0}  # 90 < 100 (Trigger)
    good_bounds = {"upper_bound": 110.0, "lower_bound": 90.0}

    mock_opt_instance.calculate_bounds.side_effect = [bad_bounds, good_bounds]

    # 3. Execution
    run_analysis("BTC/USDT", "binance", 7, 1000)

    # 4. Assertions

    # Ensure calculate_bounds was called TWICE
    assert mock_opt_instance.calculate_bounds.call_count == 2

    # Check that metrics dictionary was modified in place to 0.0
    assert metrics_dict["mu_daily"] == 0.0

    # Ensure the report received the GOOD bounds (the second calculation)
    args, _ = mock_report.call_args
    reported_bounds = args[2]  # 3rd argument is bounds
    assert reported_bounds == good_bounds


@patch("src.controller.ExchangeSniffer")
@patch("src.controller.MarketAnalyzer")
@patch("src.controller.ClosedLoopOptimizer")
@patch("src.controller.print_strategy_report")
def test_auto_neutral_switch_NOT_triggered_normally(
    mock_report, MockOpt, MockAnalyzer, MockSniffer
):
    """
    Scenario: Normal market conditions (Upper Bound > Current Price).
    Expected: Drift logic is NOT triggered. Bounds calculated only once.
    """
    current_price = 100.0

    mock_sniffer = MockSniffer.return_value
    mock_sniffer.get_market_intelligence.return_value = {
        "current_price": current_price,
        "maker_fee": 0.001,
        "spread_pct": 0.0,
    }

    mock_analyzer = MockAnalyzer.return_value
    metrics_dict = {
        "sigma_daily": 0.05,
        "mu_daily": 0.01,
        "atr": 5.0,
        "current_price": current_price,
    }
    mock_analyzer.calculate_metrics.return_value = metrics_dict

    mock_opt_instance = MockOpt.return_value
    mock_opt_instance.calculate_grid_step.return_value = 0.01
    mock_opt_instance.calculate_grid_quantity.return_value = 10
    mock_opt_instance.calculate_min_capital.return_value = 100
    mock_opt_instance.closed_loop_allocation.return_value = {
        "action": "TRADE",
        "entry_price": current_price,
    }

    # Bounds are healthy
    normal_bounds = {"upper_bound": 110.0, "lower_bound": 90.0}
    mock_opt_instance.calculate_bounds.return_value = normal_bounds

    # Execution
    run_analysis("BTC/USDT", "binance", 7, 1000)

    # Assertions
    # Should only calculate bounds once
    assert mock_opt_instance.calculate_bounds.call_count == 1
    # Metrics should NOT be touched
    assert metrics_dict["mu_daily"] == 0.01
