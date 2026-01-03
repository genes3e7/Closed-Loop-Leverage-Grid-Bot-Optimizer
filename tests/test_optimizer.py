"""
Unit tests for src/optimizer.py
Focus: Mathematical edge cases, defensive logic, and boundary testing.
"""

import pytest
from src.optimizer import ClosedLoopOptimizer


class TestClosedLoopOptimizer:
    # --- BOUNDS CALCULATION TESTS ---

    def test_bounds_basic_sanity(self):
        """Standard case: Bounds should widen with time."""
        res_7d = ClosedLoopOptimizer.calculate_bounds(100, 0.05, 0.0, 7)
        res_30d = ClosedLoopOptimizer.calculate_bounds(100, 0.05, 0.0, 30)

        assert res_30d["upper_bound"] > res_7d["upper_bound"]
        assert res_30d["lower_bound"] < res_7d["lower_bound"]
        # Check geometric property
        assert res_7d["upper_bound"] > res_7d["lower_bound"]

    def test_bounds_zero_volatility(self):
        """Edge Case: If volatility is 0, bounds should equal price (plus drift)."""
        res = ClosedLoopOptimizer.calculate_bounds(100, 0.0, 0.0, 7)
        assert res["upper_bound"] == 100.0
        assert res["lower_bound"] == 100.0

    def test_bounds_negative_drift(self):
        """Edge Case: Bearish drift should tilt bounds downwards."""
        res = ClosedLoopOptimizer.calculate_bounds(
            100, 0.05, -0.01, 30
        )  # 1% daily drop
        # The center of the cone should be below 100
        center = (res["upper_bound"] + res["lower_bound"]) / 2
        assert center < 100

    def test_bounds_invalid_inputs(self):
        """Defensive: Should raise ValueError on nonsense inputs."""
        with pytest.raises(ValueError, match="Days"):
            ClosedLoopOptimizer.calculate_bounds(100, 0.05, 0.0, 0)
        with pytest.raises(ValueError, match="Price"):
            ClosedLoopOptimizer.calculate_bounds(-50, 0.05, 0.0, 7)

    # --- GRID STEP TESTS ---

    def test_grid_step_fee_dominance(self):
        """Scenario: Fees are so high they dictate the step size."""
        # 0.1% Volatility (tiny), 5% Fee (Huge)
        step = ClosedLoopOptimizer.calculate_grid_step(sigma=0.001, maker_fee=0.05)

        # Fee logic: 2*0.05 / 0.2 = 0.5 (50% step required to profit)
        assert step == pytest.approx(0.5)
        assert step > 0.001  # Ignored volatility

    def test_grid_step_volatility_dominance(self):
        """Scenario: Fees are low, Volatility dictates step size."""
        # 10% Volatility, 0% Fee
        step = ClosedLoopOptimizer.calculate_grid_step(sigma=0.10, maker_fee=0.0)

        # Vol logic: 0.10 * 0.5 = 0.05
        assert step == 0.05

    def test_grid_step_profit_share_edge(self):
        """Edge Case: Function handles weird profit share inputs gracefully."""
        # If min_profit_share is 1.0 (impossible to achieve with fees), check fallback
        step = ClosedLoopOptimizer.calculate_grid_step(0.05, 0.01, min_profit_share=1.0)
        assert step > 0  # Should not crash or divide by zero

    # --- GRID QUANTITY TESTS (NEW) ---

    def test_grid_quantity_geometric_logic(self):
        """Test geometric calculation of grid lines."""
        # Scenario: Range 100 -> 200, Step 100% (1.0).
        # Should be exactly 1 line (100 -> 200).
        # Formula: ln(200/100) / ln(1+1) = ln(2)/ln(2) = 1.
        qty = ClosedLoopOptimizer.calculate_grid_quantity(100, 200, 1.0)
        assert qty == 1

    def test_grid_quantity_rounding_up(self):
        """Ensure grid quantity rounds up (ceil) to cover the range."""
        # Scenario: Range 100 -> 150. Step 10% (0.1).
        # 100 * 1.1^4 = 146.41 (Not enough)
        # 100 * 1.1^5 = 161.05 (Enough)
        # Should return 5 lines.
        qty = ClosedLoopOptimizer.calculate_grid_quantity(100, 150, 0.1)
        assert qty == 5

    def test_grid_quantity_invalid_inputs(self):
        """Defensive: Return 0 for invalid bounds or step."""
        # Step <= 0
        assert ClosedLoopOptimizer.calculate_grid_quantity(100, 200, 0) == 0
        assert ClosedLoopOptimizer.calculate_grid_quantity(100, 200, -0.1) == 0

        # Bounds invalid
        assert ClosedLoopOptimizer.calculate_grid_quantity(0, 100, 0.1) == 0
        assert ClosedLoopOptimizer.calculate_grid_quantity(100, -100, 0.1) == 0

        # Lower >= Upper (log will be <= 0)
        assert ClosedLoopOptimizer.calculate_grid_quantity(200, 100, 0.1) == 0

    # --- MIN CAPITAL TESTS (NEW) ---

    def test_min_capital_basic(self):
        """Test standard capital calculation."""
        # Bounds 100->200 (Step 1.0) -> 1 Line.
        # MinOrder 10, Leverage 1.0.
        # Capital = (1 * 10) / 1 = 10.
        cap = ClosedLoopOptimizer.calculate_min_capital(100, 200, 1.0, 1.0, 10.0)
        assert cap == 10.0

    def test_min_capital_leverage_impact(self):
        """Higher leverage should reduce capital requirement."""
        # Same setup but 10x leverage -> Capital = 1.0
        cap = ClosedLoopOptimizer.calculate_min_capital(100, 200, 1.0, 10.0, 10.0)
        assert cap == 1.0

    def test_min_capital_step_impact(self):
        """Smaller step sizes increase line count, increasing capital."""
        # Bounds 100->200.
        # Step 1.0 (100%) -> 1 Line.
        # Step 0.5 (50%) -> ln(2)/ln(1.5) = ~1.7 -> 2 Lines.
        cap_large_step = ClosedLoopOptimizer.calculate_min_capital(
            100, 200, 1.0, 1.0, 10.0
        )
        cap_small_step = ClosedLoopOptimizer.calculate_min_capital(
            100, 200, 0.5, 1.0, 10.0
        )

        assert cap_small_step > cap_large_step
        assert cap_small_step == 20.0  # 2 lines * 10

    def test_min_capital_invalid_inputs(self):
        """Should handle invalid step gracefullly (return 0.0)."""
        cap = ClosedLoopOptimizer.calculate_min_capital(100, 200, 0.0, 1.0, 10.0)
        assert cap == 0.0

    # --- ALLOCATION TESTS ---

    def test_allocation_safety(self):
        """Test if liquidation price is correctly padded."""
        res = ClosedLoopOptimizer.closed_loop_allocation(
            portfolio_balance=10000,
            entry_price=100,
            stop_loss=90,
            target_upper=120,
            kelly_fraction=1.0,
            safety_buffer=0.9,
        )

        assert res["action"] == "TRADE"
        # Liq must be 90 * 0.9 = 81
        assert res["target_liq_price"] == 81.0
        # Leverage check: 100 / (100 - 81) = 100/19 ~= 5.26
        assert 5.2 < res["max_safe_leverage"] < 5.3

    def test_allocation_stop_above_entry(self):
        """Defensive: Long Grid Stop Loss must be below Entry."""
        with pytest.raises(ValueError, match="Stop Loss"):
            ClosedLoopOptimizer.closed_loop_allocation(1000, 100, 105, 120)

    def test_allocation_negative_edge(self):
        """Kelly Logic: If Payoff/Winrate implies losing money, DO NOT TRADE."""
        # Win rate 10%, Payoff 1:1 -> Kelly is negative
        res = ClosedLoopOptimizer.closed_loop_allocation(
            1000, 100, 90, 110, win_rate=0.1
        )
        assert res["action"] == "DO_NOT_TRADE"
        assert "Negative Edge" in res["reason"]

    def test_allocation_zero_portfolio(self):
        """Edge Case: Portfolio is 0."""
        res = ClosedLoopOptimizer.closed_loop_allocation(0, 100, 90, 120)
        # Should execute math but return 0 exposure
        assert res["total_exposure"] == 0.0
        assert res["required_margin_transfer"] == 0.0
