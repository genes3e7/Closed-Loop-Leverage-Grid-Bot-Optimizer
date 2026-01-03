"""
Closed Loop Bot Optimizer - Entry Point.
"""

import argparse
from src.controller import run_analysis


def main():
    parser = argparse.ArgumentParser(
        description="Closed Loop Grid Bot Optimizer: Calculates safe leverage and grid parameters based on volatility and fees."
    )

    parser.add_argument(
        "ticker",
        type=str,
        help="The asset symbol (e.g., 'BTC' or 'SOL'). NOTE: If using a specific --exchange, use the pair format (e.g., 'BTC/USDT') to ensure fee sniffing works.",
    )

    parser.add_argument(
        "--exchange",
        type=str,
        default="binance",
        help="The exchange ID (ccxt) to sniff fees from. Common: 'binance', 'pionex', 'cryptocom', 'bybit', 'okx'. (default: binance)",
    )

    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Duration to run the bot in days (default: 7)",
    )

    parser.add_argument(
        "--portfolio",
        type=float,
        default=None,
        help="Total portfolio size/bankroll. If omitted, calculates the MINIMUM REQUIRED capital.",
    )

    args = parser.parse_args()

    # Pass control to the Logic Controller in src/
    run_analysis(
        ticker=args.ticker,
        exchange=args.exchange,
        days=args.days,
        portfolio=args.portfolio,
    )


if __name__ == "__main__":
    main()
