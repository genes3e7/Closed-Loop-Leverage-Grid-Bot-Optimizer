"""
Core Logic: The Closed Loop Optimizer.
Combines Analyzer (Volatility) and Sniffer (Fees) to output Bot Params.
"""

import math
from typing import Any

import numpy as np


class ClosedLoopOptimizer:
    """
    The engine that calculates Boundaries, Leverage, and Capital Allocation.
    """

    @staticmethod
    def calculate_bounds(
        current_price: float,
        sigma: float,
        mu: float,
        days: int,
        confidence_z: float = 2.0,
    ) -> dict[str, float]:
        """
        Calculates Drift-Adjusted Volatility Cone.
        Range = Price * exp( (mu - 0.5*sigma^2)*t +/- z*sigma*sqrt(t) )
        """
        if days <= 0:
            raise ValueError("Days must be positive.")
        if current_price <= 0:
            raise ValueError("Price must be positive.")

        drift_component = (mu - 0.5 * sigma**2) * days
        vol_component = confidence_z * sigma * np.sqrt(days)

        upper = current_price * np.exp(drift_component + vol_component)
        lower = current_price * np.exp(drift_component - vol_component)

        return {"upper_bound": upper, "lower_bound": lower}

    @staticmethod
    def calculate_grid_step(sigma: float, maker_fee: float, min_profit_share: float = 0.8) -> float:
        """
        Calculates optimal grid spacing accounting for Fee Drag.
        Constraint: Fees must not eat more than (1 - min_profit_share) of profit.
        """
        round_trip_fee = maker_fee * 2
        # Fee constraint: step * (1-share) > fee  --> step > fee / (1-share)
        fee_drag_limit = 1.0 - min_profit_share
        if fee_drag_limit <= 0:
            return 0.01  # Fallback

        min_fee_step = round_trip_fee / fee_drag_limit

        # Volatility sweet spot (capture 0.5 daily sigma)
        vol_step = sigma * 0.5

        # Return the larger of the two (Defensive: don't lose money to fees)
        return max(min_fee_step, vol_step)

    @staticmethod
    def calculate_grid_quantity(lower_bound: float, upper_bound: float, grid_step: float) -> int:
        """
        Calculates the number of grid lines (Geometric).
        N = ln(Upper/Lower) / ln(1 + step)
        """
        if grid_step <= 0:
            return 0
        if lower_bound <= 0 or upper_bound <= 0:
            return 0
        if lower_bound >= upper_bound:
            return 0

        num_lines = math.log(upper_bound / lower_bound) / math.log(1 + grid_step)
        return int(math.ceil(num_lines))

    @staticmethod
    def calculate_min_capital(
        lower_bound: float,
        upper_bound: float,
        grid_step: float,
        safe_leverage: float,
        min_order_size: float = 6.0,
    ) -> float:
        """
        Calculates the minimum capital required to run the grid.
        Formula: (Lines * MinOrderSize) / Leverage
        """
        num_lines = ClosedLoopOptimizer.calculate_grid_quantity(lower_bound, upper_bound, grid_step)

        # Total Notional required to place min order on every line
        total_notional = num_lines * min_order_size

        # Cash required = Notional / Leverage
        min_margin = total_notional / safe_leverage

        return min_margin

    @staticmethod
    def closed_loop_allocation(
        portfolio_balance: float,
        entry_price: float,
        stop_loss: float,
        target_upper: float,
        win_rate: float = 0.55,
        kelly_fraction: float = 0.5,
        safety_buffer: float = 0.90,
    ) -> dict[str, Any]:
        """
        Derives the 'Closed Loop' parameters: Active/Passive Margin split.
        """
        # 1. Validation
        if stop_loss >= entry_price:
            raise ValueError("Stop Loss must be below Entry Price for Long Grid.")

        # 2. Ratios & Payoff
        risk_dist = (entry_price - stop_loss) / entry_price
        reward_dist = (target_upper - entry_price) / entry_price

        if risk_dist <= 0:
            return {"error": "Invalid Risk Distance"}

        payoff_ratio = reward_dist / risk_dist

        # 3. Kelly Criterion (Constrained)
        # f = p - (q / b)
        q = 1 - win_rate
        raw_kelly = win_rate - (q / payoff_ratio)
        applied_kelly = raw_kelly * kelly_fraction

        if applied_kelly <= 0:
            return {"action": "DO_NOT_TRADE", "reason": "Negative Edge/Kelly"}

        # 4. Total Notional Exposure (The 'Wager')
        # Position Size = Balance * (Kelly% / Risk%)
        total_exposure = portfolio_balance * (applied_kelly / risk_dist)

        # 5. Closed Loop Safety (Liquidation Math)
        # Target Liq must be SAFETY_BUFFER (e.g. 10%) below Stop Loss
        target_liq_price = stop_loss * safety_buffer

        # Max Safe Leverage = Entry / (Entry - Liq)
        dist_to_liq = entry_price - target_liq_price
        max_safe_leverage = entry_price / dist_to_liq

        # 6. Margin Calculation
        required_margin = total_exposure / max_safe_leverage

        return {
            "action": "TRADE",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "target_liq_price": target_liq_price,
            "max_safe_leverage": max_safe_leverage,
            "total_exposure": total_exposure,
            "required_margin_transfer": required_margin,
            "kelly_risk_pct": applied_kelly,
        }
