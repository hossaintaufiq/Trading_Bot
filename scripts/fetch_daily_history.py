"""Fetch long daily history from Binance PUBLIC market data (no keys) into storage/research/daily/."""
import sys
from pathlib import Path

import httpx
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "storage" / "research" / "daily"
SYMBOLS = sys.argv[1:] or ["BTCUSDT", "ETHUSDT", "BNBUSDT"]


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
    # A-09: drop the in-progress candle (open time + 1 day is in the future)
    now = pd.Timestamp.now(tz="UTC")
    return d[d["timestamp"] + pd.Timedelta(days=1) <= now].reset_index(drop=True)


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for s in SYMBOLS:
        df = fetch(s)
        df.to_parquet(OUT / f"{s}.parquet")
        print(s, len(df), df["timestamp"].iloc[0].date(), df["timestamp"].iloc[-1].date())
