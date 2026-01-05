"""
Orchestrator for the Closed Loop System.
Connects Sniffer, Analyzer, and Optimizer.
"""

import sys
import difflib
import ccxt
from .analyzer import MarketAnalyzer
from .sniffer import ExchangeSniffer
from .optimizer import ClosedLoopOptimizer
from .reporting import print_strategy_report, print_market_intel


def resolve_exchange(exchange_name: str) -> str:
    """Auto-corrects exchange name typos."""
    if exchange_name not in ccxt.exchanges:
        # Increased cutoff to 0.85 to prevent 'pionex' -> 'poloniex' false positives
        matches = difflib.get_close_matches(
            exchange_name, ccxt.exchanges, n=1, cutoff=0.85
        )
        if matches:
            print(
                f"⚠️ Warning: Exchange '{exchange_name}' not found. Auto-correcting to: '{matches[0]}'"
            )
            return matches[0]

        # If no typo match is found, we proceed with the original name.
        # We rely on the ExchangeSniffer to attempt loading it; if it fails there,
        # it will gracefully degrade to Offline Mode.

    return exchange_name


def run_analysis(
    ticker: str,
    exchange: str,
    days: int,
    portfolio: float = None,
    is_neutral: bool = False,
):
    """
    Main Logic Flow: Sniff -> Analyze -> Optimize -> Report
    """
    print(f"--- 🚀 INITIALIZING CLOSED LOOP SYSTEM: {ticker} ---")

    try:
        # 1. AUTO-CORRECT EXCHANGE
        exchange = resolve_exchange(exchange)

        # 2. SNIFF (Real-time data)
        sniffer = ExchangeSniffer(exchange_id=exchange)
        market_intel = sniffer.get_market_intelligence(ticker)

        # --- INTERACTIVE FEE PROMPT (If Exchange Unknown) ---
        if market_intel["maker_fee"] is None:
            print("\n⚠️  EXCHANGE DATA NOT AVAILABLE FOR FEES")
            print("   Please input the fee tier for your exchange manually.")

            while True:
                try:
                    maker_input = input(
                        f"   Enter Maker Fee (%) for {exchange} (e.g. 0.05): "
                    )
                    taker_input = input(
                        f"   Enter Taker Fee (%) for {exchange} (e.g. 0.05): "
                    )

                    # Convert percentage to decimal (0.05% -> 0.0005)
                    # Input validation implicit here (float conversion will raise ValueError)
                    market_intel["maker_fee"] = float(maker_input) / 100
                    market_intel["taker_fee"] = float(taker_input) / 100

                    print(
                        f"   -> Using Maker: {market_intel['maker_fee']:.4f} | Taker: {market_intel['taker_fee']:.4f}\n"
                    )
                    break  # Exit loop on success
                except ValueError:
                    print(
                        "   ❌ Invalid input. Please enter valid numeric values (e.g. 0.05)."
                    )

        # 3. ANALYZE (Historical Volatility)
        clean_ticker = ticker.split("/")[0]  # 'BTC/USDT' -> 'BTC'
        analyzer = MarketAnalyzer(clean_ticker)
        analyzer.fetch_history(days=90)
        metrics = analyzer.calculate_metrics()

        # Override Drift if Neutral Mode requested
        if is_neutral:
            metrics["mu_daily"] = 0.0
            print("   ℹ️  NEUTRAL MODE ACTIVE: Ignoring historical drift.")

        # Print Intel Report
        print_market_intel(market_intel, metrics)

        # Prefer live price if available, else historical close
        current_price = market_intel.get("current_price") or metrics["current_price"]

        # 4. OPTIMIZE (The Math)
        opt = ClosedLoopOptimizer()

        # A. Bounds
        bounds = opt.calculate_bounds(
            current_price, metrics["sigma_daily"], metrics["mu_daily"], days
        )

        # --- AUTO-RECOVERY: Detect Bearish Drift ---
        # If the historical trend is so bearish that the grid is projected entirely
        # below the current price, we force Neutral Mode to center the grid.
        if bounds["upper_bound"] < current_price:
            print(
                "\n   ⚠️  WARNING: Detected Bearish Drift (Upper Bound < Current Price)."
            )
            print(
                "   -> 🛡️  Automatically switching to NEUTRAL MODE (Drift = 0) to center the grid."
            )

            # Force neutral drift
            metrics["mu_daily"] = 0.0
            # Recalculate bounds
            bounds = opt.calculate_bounds(
                current_price, metrics["sigma_daily"], metrics["mu_daily"], days
            )

        stop_loss = bounds["lower_bound"] - (1.5 * metrics["atr"])

        # B. Grid Step & Quantity
        grid_step = opt.calculate_grid_step(
            metrics["sigma_daily"], market_intel["maker_fee"]
        )
        grid_quantity = opt.calculate_grid_quantity(
            bounds["lower_bound"], bounds["upper_bound"], grid_step
        )

        # C. Allocation & Min Capital
        # Calculate leverage first to determine min capital if needed
        target_liq = stop_loss * 0.90
        dist_to_liq = current_price - target_liq
        max_safe_leverage = current_price / dist_to_liq if dist_to_liq > 0 else 1.0

        is_min_recommended = False

        if portfolio is None or portfolio <= 0:
            # Calculate minimum recommended capital to ensure valid grid lines
            min_capital = opt.calculate_min_capital(
                bounds["lower_bound"],
                bounds["upper_bound"],
                grid_step,
                max_safe_leverage,
            )
            # Use this minimum as the portfolio for allocation
            portfolio = min_capital
            is_min_recommended = True

        allocation = opt.closed_loop_allocation(
            portfolio_balance=portfolio,
            entry_price=current_price,
            stop_loss=stop_loss,
            target_upper=bounds["upper_bound"],
        )

        # 5. REPORT
        print_strategy_report(
            ticker,
            days,
            bounds,
            stop_loss,
            grid_step,
            grid_quantity,
            allocation,
            portfolio,
            is_min_recommended,
        )

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")
        sys.exit(1)
