"""Fetch long daily history from Binance PUBLIC market data (no keys) into storage/research/daily/."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.data.market.daily_history import OUT, fetch  # noqa: E402

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for s in sys.argv[1:] or ["BTCUSDT", "ETHUSDT", "BNBUSDT"]:
        df = fetch(s)
        df.to_parquet(OUT / f"{s}.parquet")
        print(s, len(df), df["timestamp"].iloc[0].date(), df["timestamp"].iloc[-1].date())
