"""
Handles the output/display logic for the bot optimizer.
Separates 'View' from 'Logic'.
"""


def print_strategy_report(
    ticker: str,
    days: int,
    bounds: dict,
    stop_loss: float,
    grid_step: float,
    grid_quantity: int,
    allocation: dict,
    portfolio: float,
    is_min_recommended: bool = False,
):
    """Prints the formatted strategy report to stdout."""
    print("\n" + "=" * 40)
    print(f"   STRATEGY REPORT: {ticker} ({days} Days)")
    print("=" * 40)

    if allocation.get("action") != "TRADE":
        print(f"⛔ STOP: {allocation.get('reason')}")
        return

    # Added Current Price to output
    print(f"CURRENT PRICE:     ${allocation['entry_price']:.2f}")
    print("-" * 40)

    # Warning for Bearish Drift
    if bounds["upper_bound"] < allocation["entry_price"]:
        print("⚠️  WARNING: Grid is entirely BELOW current price!")
        print("    (Historical trend is bearish. Use --neutral to center grid.)")
        print("-" * 40)

    print(f"1. GRID BOUNDS:    ${bounds['lower_bound']:.2f} to ${bounds['upper_bound']:.2f}")
    print(f"2. STOP LOSS:      ${stop_loss:.2f} (Invalidation)")
    print(f"3. GRID QUANTITY:  {grid_quantity} Lines (Step: ~{grid_step * 100:.3f}%)")
    print("-" * 40)
    print(f"4. LIQUIDATION:    ${allocation['target_liq_price']:.2f} (Safety Floor)")
    print(f"5. EFF. LEVERAGE:  {allocation['max_safe_leverage']:.2f}x")
    print("-" * 40)

    header_text = (
        ">>> EXECUTION (Recommended Minimum) <<<"
        if is_min_recommended
        else f">>> EXECUTION (For Portfolio ${portfolio:,.0f}) <<<"
    )
    print(header_text)

    print(f"TRANSFER TO BOT:   ${allocation['required_margin_transfer']:,.2f}")
    print(f"TOTAL EXPOSURE:    ${allocation['total_exposure']:,.2f}")
    print("=" * 40)


def print_market_intel(fee_data: dict, volatility_metrics: dict):
    """Prints the initial data gathering status."""
    print(
        f"✅ SNIFFER: Found Fees (Mk: {fee_data['maker_fee']:.4f}) | "
        f"Spread: {fee_data['spread_pct']:.4f}%"
    )
    print(
        f"✅ ANALYZER: Volatility {volatility_metrics['sigma_daily'] * 100:.2f}% | "
        f"Drift {volatility_metrics['mu_daily'] * 100:.3f}%"
    )
