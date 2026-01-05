"""
Unit tests for src/optimizer.py
Focus: Mathematical edge cases, defensive logic, and boundary testing.
"""

import pytest
from src.optimizer import ClosedLoopOptimizer


class TestClosedLoopOptimizer:
    # --- BOUNDS CALCULATION TESTS (GBM Logic) ---

    def test_bounds_basic_sanity(self):
        """Standard case: Bounds should widen with time."""
        res_7d = ClosedLoopOptimizer.calculate_bounds(100, 0.05, 0.0, 7)
        res_30d = ClosedLoopOptimizer.calculate_bounds(100, 0.05, 0.0, 30)

        # Longer time = Wider Cone
        assert res_30d["upper_bound"] > res_7d["upper_bound"]
        assert res_30d["lower_bound"] < res_7d["lower_bound"]
        # Geometric Property: Upper > Lower
        assert res_7d["upper_bound"] > res_7d["lower_bound"]

    def test_bounds_volatility_impact(self):
        """Higher Volatility = Wider Bounds."""
        res_low_vol = ClosedLoopOptimizer.calculate_bounds(100, 0.01, 0.0, 7)
        res_high_vol = ClosedLoopOptimizer.calculate_bounds(100, 0.10, 0.0, 7)

        assert res_high_vol["upper_bound"] > res_low_vol["upper_bound"]
        assert res_high_vol["lower_bound"] < res_low_vol["lower_bound"]

    def test_bounds_extreme_drift(self):
        """
        Drift Stress Test.
        If Drift (Mu) is massive, the cone should tilt heavily.
        """
        # Massive Bullish Drift (+1% daily)
        res_bull = ClosedLoopOptimizer.calculate_bounds(100, 0.05, 0.01, 30)
        # Massive Bearish Drift (-3% daily) - Needs to be strong to pull upper bound below 100 vs volatility
        res_bear = ClosedLoopOptimizer.calculate_bounds(100, 0.05, -0.03, 30)

        assert res_bull["upper_bound"] > 130  # Should be significantly higher
        assert (
            res_bear["upper_bound"] < 100
        )  # Even upper bound should drop below entry if drift is toxic enough

    def test_bounds_tiny_prices(self):
        """Stress Test: SHIB/PEPE pricing (0.00001)."""
        price = 0.00001
        res = ClosedLoopOptimizer.calculate_bounds(price, 0.05, 0.0, 7)

        assert res["upper_bound"] > price
        assert res["lower_bound"] < price
        assert res["lower_bound"] > 0  # Prices cannot be negative

    def test_bounds_invalid_inputs(self):
        """Defensive: Should raise ValueError on nonsense inputs."""
        with pytest.raises(ValueError, match="Days"):
            ClosedLoopOptimizer.calculate_bounds(100, 0.05, 0.0, 0)
        with pytest.raises(ValueError, match="Price"):
            ClosedLoopOptimizer.calculate_bounds(-50, 0.05, 0.0, 7)

    # --- GRID STEP TESTS (Fee vs Volatility) ---

    def test_grid_step_fee_dominance(self):
        """Scenario: Fees are so high they dictate the step size."""
        # 0.1% Volatility (tiny), 5% Fee (Huge)
        # Logic: MinStep = (2 * Fee) / (1 - ProfitShare)
        # MinStep = (0.10) / 0.20 = 0.50
        step = ClosedLoopOptimizer.calculate_grid_step(sigma=0.001, maker_fee=0.05)

        assert step == pytest.approx(0.5)
        assert step > 0.001  # Ignored volatility

    def test_grid_step_volatility_dominance(self):
        """Scenario: Fees are low, Volatility dictates step size."""
        # 10% Volatility, 0% Fee
        step = ClosedLoopOptimizer.calculate_grid_step(sigma=0.10, maker_fee=0.0)

        # Logic: Step = 0.5 * Sigma
        assert step == 0.05

    def test_grid_step_zero_fees(self):
        """Edge Case: Zero fees shouldn't crash division."""
        step = ClosedLoopOptimizer.calculate_grid_step(sigma=0.05, maker_fee=0.0)
        assert step == 0.025  # Purely volatility based

    # --- GRID QUANTITY TESTS (Geometric Spacing) ---

    def test_grid_quantity_geometric_logic(self):
        """
        Test geometric calculation.
        Range: 100 -> 200. Step: 100% (1.0).
        Lines: 100 * (1+1)^1 = 200. Should be exactly 1 line.
        """
        qty = ClosedLoopOptimizer.calculate_grid_quantity(100, 200, 1.0)
        assert qty == 1

    def test_grid_quantity_rounding(self):
        """
        Test rounding up.
        Range: 100 -> 150. Step: 10% (0.1).
        1.1^4 ~= 1.46 (146) -> Not enough.
        1.1^5 ~= 1.61 (161) -> Enough.
        Result should be 5 lines.
        """
        qty = ClosedLoopOptimizer.calculate_grid_quantity(100, 150, 0.1)
        assert qty == 5

    def test_grid_quantity_massive_range(self):
        """Stress Test: 100x bagger range."""
        # 100 -> 10,000. Step 10%.
        qty = ClosedLoopOptimizer.calculate_grid_quantity(100, 10000, 0.1)
        # 1.1^x = 100. x = log(100)/log(1.1) ~= 48.3
        assert qty == 49

    def test_grid_quantity_invalid(self):
        """Defensive: Return 0 for crossed bounds."""
        assert ClosedLoopOptimizer.calculate_grid_quantity(200, 100, 0.1) == 0

    # --- MIN CAPITAL TESTS (Leverage & Notional) ---

    def test_min_capital_leverage_impact(self):
        """Higher leverage should reduce capital requirement linearly."""
        # Setup: 1 Line, $10 order.
        cap_1x = ClosedLoopOptimizer.calculate_min_capital(100, 200, 1.0, 1.0, 10.0)
        cap_10x = ClosedLoopOptimizer.calculate_min_capital(100, 200, 1.0, 10.0, 10.0)

        assert cap_1x == 10.0
        assert cap_10x == 1.0

    def test_min_capital_tiny_step(self):
        """Tiny steps = Many lines = High Capital."""
        # Range 100->105 (~5%). Step 0.01%.
        # Lines approx 500.
        cap = ClosedLoopOptimizer.calculate_min_capital(100, 105, 0.0001, 1.0, 1.0)
        assert cap > 400  # 400 lines * $1

    # --- ALLOCATION & KELLY TESTS (The Core Engine) ---

    def test_allocation_safety_buffer(self):
        """
        CRITICAL: Verify Liquidation is ALWAYS below Stop Loss.
        """
        stop_loss = 90
        res = ClosedLoopOptimizer.closed_loop_allocation(
            portfolio_balance=10000,
            entry_price=100,
            stop_loss=stop_loss,
            target_upper=120,
            safety_buffer=0.9,
        )

        # Target Liq = 90 * 0.9 = 81
        assert res["target_liq_price"] == 81.0
        assert res["target_liq_price"] < stop_loss

        # Inverse Check:
        # Leverage = Entry / (Entry - Liq) = 100 / 19 = 5.26x
        # If price drops 19%, equity is wiped.
        # Stop loss is at 10% drop.
        # We survive the stop loss.

    def test_allocation_negative_kelly(self):
        """If edge is negative, do not trade."""
        # Risk: 10% (100->90). Reward: 1% (100->101). R:R = 0.1.
        # WinRate: 50%.
        # Kelly is definitely negative.
        res = ClosedLoopOptimizer.closed_loop_allocation(
            1000, 100, 90, 101, win_rate=0.5
        )
        assert res["action"] == "DO_NOT_TRADE"
        assert "Negative Edge" in res["reason"]

    def test_allocation_tight_stop(self):
        """
        Stress Test: Stop loss extremely close to entry (High Leverage).
        """
        # Entry 100, Stop 99. Risk 1%.
        # Reward 110. R:R 10.
        # Kelly should be aggressive.
        res = ClosedLoopOptimizer.closed_loop_allocation(
            10000, 100, 99, 110, kelly_fraction=1.0
        )

        assert res["action"] == "TRADE"
        # Risk distance is tiny (0.01).
        # Exposure should be massive.
        assert res["total_exposure"] > 10000

        # Check Liquidation safety logic still holds
        # Liq should be 99 * 0.9 = 89.1
        # Dist to Liq = 10.9
        # Max Lev = 100 / 10.9 ~= 9.17x
        assert res["max_safe_leverage"] == pytest.approx(
            100 / (100 - (99 * 0.9)), rel=1e-3
        )

    def test_allocation_zero_portfolio(self):
        """Math should work even with 0 portfolio (returning 0 exposure)."""
        res = ClosedLoopOptimizer.closed_loop_allocation(0, 100, 90, 120)
        assert res["total_exposure"] == 0.0
