"""
NEPTUNE Backend — conftest.py
Shared pytest fixtures for all tests.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from decimal import Decimal


def make_candles(
    n: int = 100,
    symbol: str = "BTCUSDT",
    timeframe: str = "15m",
    start_price: float = 50000.0,
    seed: int = 42,
) -> pd.DataFrame:
    """
    Generate synthetic OHLCV candles for unit tests.
    NOT for use as representative market data.
    """
    rng = np.random.default_rng(seed)
    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    interval_map = {"15m": 15, "1h": 60, "4h": 240}
    interval_minutes = interval_map.get(timeframe, 15)

    timestamps = [now + timedelta(minutes=i * interval_minutes) for i in range(n)]
    closes = [start_price]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + rng.normal(0, 0.002)))

    highs = [c * (1 + abs(rng.normal(0, 0.001))) for c in closes]
    lows = [c * (1 - abs(rng.normal(0, 0.001))) for c in closes]
    opens = [closes[0]] + closes[:-1]
    volumes = rng.uniform(100, 1000, n).tolist()

    return pd.DataFrame({
        "timestamp": timestamps,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "is_closed": [True] * n,
        "symbol": symbol,
        "timeframe": timeframe,
    })


@pytest.fixture
def sample_candles() -> pd.DataFrame:
    """100 synthetic BTCUSDT 15m candles."""
    return make_candles(n=100)


@pytest.fixture
def sample_candles_1h() -> pd.DataFrame:
    """100 synthetic BTCUSDT 1h candles."""
    return make_candles(n=100, timeframe="1h")
