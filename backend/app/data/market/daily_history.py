"""Daily candle history from Binance PUBLIC market data (no keys) with closed-candle-only guarantee (A-09)."""
import time
from pathlib import Path

import httpx
import pandas as pd

OUT = Path(__file__).resolve().parents[4] / "storage" / "research" / "daily"
_LAST_REFRESH: dict = {}


def fetch(symbol: str) -> pd.DataFrame:
    rows, start = [], int(pd.Timestamp("2017-11-15", tz="UTC").timestamp() * 1000)
    while True:
        r = httpx.get("https://api.binance.com/api/v3/klines",
                      params=dict(symbol=symbol, interval="1d", startTime=start, limit=1000), timeout=30).json()
        if not r:
            break
        rows += r
        start = r[-1][0] + 86_400_000
        if len(r) < 1000:
            break
    d = pd.DataFrame(rows).iloc[:, :6]
    d.columns = ["timestamp", "open", "high", "low", "close", "volume"]
    d["timestamp"] = pd.to_datetime(d["timestamp"], unit="ms", utc=True)
    d = d.astype({c: float for c in ["open", "high", "low", "close", "volume"]})
    now = pd.Timestamp.now(tz="UTC")
    return d[d["timestamp"] + pd.Timedelta(days=1) <= now].reset_index(drop=True)  # drop in-progress candle


def refresh_if_stale(symbol: str, min_interval_s: int = 300) -> bool:
    """Re-download if a newer fully closed daily candle should exist. Returns True if data changed."""
    path = OUT / f"{symbol}.parquet"
    if path.exists():
        last = pd.read_parquet(path, columns=["timestamp"])["timestamp"].max()
        if last + pd.Timedelta(days=1) >= pd.Timestamp.now(tz="UTC").normalize():
            return False                                   # already have yesterday's closed candle
    if time.time() - _LAST_REFRESH.get(symbol, 0) < min_interval_s:
        return False
    _LAST_REFRESH[symbol] = time.time()
    try:
        df = fetch(symbol)
    except Exception:
        return False
    OUT.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path)
    return True
