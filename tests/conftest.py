"""
Pytest Configuration and Fixtures.
Centralizes mock data for robust testing across modules.
"""

import pytest
import pandas as pd
import numpy as np
from unittest.mock import MagicMock


@pytest.fixture
def mock_ohlcv_data():
    """Generates a synthetic DataFrame behaving like YFinance data."""
    np.random.seed(42)
    days = 100
    dates = pd.date_range(start="2023-01-01", periods=days)

    # Random Walk
    returns = np.random.normal(0, 0.02, days)
    price_path = 100 * np.exp(np.cumsum(returns))

    df = pd.DataFrame(
        {
            "Open": price_path,
            "High": price_path * 1.02,
            "Low": price_path * 0.98,
            "Close": price_path,
            "Volume": np.random.randint(1000, 10000, days),
        },
        index=dates,
    )

    return df


@pytest.fixture
def mock_malformed_data():
    """Generates data with NaNs and Zeros to test error handling."""
    df = pd.DataFrame(
        {
            "Close": [
                100,
                101,
                np.nan,
                102,
                0,
                103,
            ],  # 0 will break log returns if not handled
            "High": [105, 106, 107, 108, 109, 110],
            "Low": [95, 96, 97, 98, 99, 100],
        }
    )
    return df


@pytest.fixture
def mock_ccxt_exchange():
    """Mocks a CCXT exchange object."""
    exchange = MagicMock()
    exchange.has = {"fetchTradingFees": True, "fetchFundingRate": True}
    exchange.markets = {"BTC/USDT": {"id": "BTCUSDT"}}
    return exchange
