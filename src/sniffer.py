"""
Module for fetching real-time exchange data (Fees, Funding, Spread).
"""

import ccxt
from typing import Dict, Optional, Any


class ExchangeSniffer:
    """
    Handles connection to exchanges to 'sniff' hidden costs and live metrics.
    """

    def __init__(
        self,
        exchange_id: str,
        api_key: Optional[str] = None,
        secret: Optional[str] = None,
    ):
        self.exchange_id = exchange_id.lower()
        self.api_key = api_key
        self.secret = secret
        self.exchange = self._initialize_exchange()

    def _initialize_exchange(self) -> Optional[Any]:
        """Initializes the CCXT exchange object safely. Returns None if not found."""
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            config = {"enableRateLimit": True}
            if self.api_key and self.secret:
                config.update({"apiKey": self.api_key, "secret": self.secret})
            return exchange_class(config)
        except AttributeError:
            print(
                f"⚠️ Warning: Exchange '{self.exchange_id}' not found in local CCXT library."
            )
            print("   -> Running in OFFLINE mode (using Binance for Fallback Data).")
            return None

    def get_market_intelligence(self, symbol: str) -> Dict[str, Optional[float]]:
        """
        Fetches all critical cost metrics.
        If offline, tries to fetch Funding/Spread from Binance and returns None for fees.
        """
        # Default Fallbacks
        metrics = {
            "maker_fee": 0.001,
            "taker_fee": 0.001,
            "spread_pct": 0.0,
            "funding_rate_8h": 0.0001,
            "current_price": 0.0,
        }

        # --- FALLBACK MODE (Binance) ---
        if not self.exchange:
            try:
                # User requested: Default to Binance for Funding/Spread if primary is offline
                fallback_ex = ccxt.binance({"enableRateLimit": True})
                # Ensure symbol has a slash for CCXT (e.g. BTC -> BTC/USDT)
                fallback_symbol = symbol if "/" in symbol else f"{symbol}/USDT"

                # 1. Fetch Ticker (Spread + Price)
                ticker = fallback_ex.fetch_ticker(fallback_symbol)
                if ticker.get("bid") and ticker.get("ask"):
                    metrics["current_price"] = ticker["last"]
                    spread = ticker["ask"] - ticker["bid"]
                    metrics["spread_pct"] = spread / ticker["ask"]

                # 2. Fetch Funding
                # Try fetchFundingRate first, fallback to implicit if needed
                if fallback_ex.has.get("fetchFundingRate"):
                    funding = fallback_ex.fetch_funding_rate(fallback_symbol)
                    metrics["funding_rate_8h"] = funding.get("fundingRate", 0.0001)

                print(
                    f"   ℹ️ Successfully fetched fallback data from Binance for {fallback_symbol}"
                )

            except Exception as e:
                print(
                    f"   ❌ Fallback to Binance failed ({str(e)}). Using hard defaults."
                )

            # CRITICAL: Set fees to None to signal Controller to ask user
            metrics["maker_fee"] = None
            metrics["taker_fee"] = None
            return metrics

        # --- NORMAL MODE ---
        try:
            self.exchange.load_markets()
            if symbol not in self.exchange.markets:
                pass

            # 1. Sniff Fees
            try:
                if self.exchange.has.get("fetchTradingFees"):
                    fees = self.exchange.fetch_trading_fees([symbol])[symbol]
                    metrics["maker_fee"] = fees["maker"]
                    metrics["taker_fee"] = fees["taker"]
                else:
                    market = self.exchange.market(symbol)
                    metrics["maker_fee"] = market.get("maker", 0.001)
                    metrics["taker_fee"] = market.get("taker", 0.001)
            except Exception:
                pass

            # 2. Sniff Spread & Price
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                bid = ticker.get("bid")
                ask = ticker.get("ask")
                last = ticker.get("last")

                if bid and ask and last:
                    metrics["current_price"] = last
                    spread = ask - bid
                    metrics["spread_pct"] = (spread / ask) if ask > 0 else 0.0
            except Exception:
                pass

            # 3. Sniff Funding
            try:
                if self.exchange.has.get("fetchFundingRate"):
                    funding = self.exchange.fetch_funding_rate(symbol)
                    metrics["funding_rate_8h"] = funding.get("fundingRate", 0.0001)
            except Exception:
                pass

        except Exception as e:
            print(f"⚠️ Warning: Sniffer encountered error: {e}. Using safety defaults.")

        return metrics
