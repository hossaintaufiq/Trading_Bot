"""Broad-universe check of daily_trend_v1 (frozen 20/10 rule). Daily equal-weight across coins that have data that day."""
import sys
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.simulation.daily_trend_backtest import DATA_DIR, run_sleeve
from app.strategies.daily_trend import DailyTrendConfig

cfg = DailyTrendConfig()
strat, bh, per = {}, {}, []
for f in sorted(DATA_DIR.glob("*.parquet")):
    if f.stem == "LUNAUSDT":  # spliced series across the 2022 collapse/relaunch: not a continuous price
        continue
    df = pd.read_parquet(f).sort_values("timestamp").reset_index(drop=True)
    r = run_sleeve(f.stem, df, Decimal("1000"), cfg)
    idx = pd.to_datetime(list(r.equity.keys()), utc=True)
    eq = pd.Series([float(v) for v in r.equity.values()], index=idx)
    strat[f.stem] = eq.pct_change()
    bh[f.stem] = pd.Series(df["close"].values, index=pd.to_datetime(df["timestamp"], utc=True)).pct_change()
S, B = pd.DataFrame(strat), pd.DataFrame(bh)

def summarize(a, b, label):
    s, h = S[a:b], B[a:b]
    rs, rh = s.mean(axis=1).fillna(0), h.mean(axis=1).fillna(0)   # equal weight of active coins
    def m(r):
        e = (1 + r).cumprod(); return (e.iloc[-1] - 1) * 100, ((e / e.cummax()) - 1).min() * 100, r.mean() / r.std() * 365**.5
    (a1, d1, s1), (a2, d2, s2) = m(rs), m(rh)
    coin = ((1 + s.fillna(0)).prod() - 1)
    cb = ((1 + h.fillna(0)).prod() - 1)
    print(f"{label}: strat {a1:+.0f}% (DD {d1:.0f}%, Sharpe {s1:.2f}) | B&H {a2:+.0f}% (DD {d2:.0f}%, Sharpe {s2:.2f}) | "
          f"coins {len(coin)}: strat>0 in {int((coin>0).sum())}, strat beats own B&H in {int((coin>cb).sum())}, median coin strat {coin.median()*100:+.0f}% vs B&H {cb.median()*100:+.0f}%")

summarize("2018-01-01", "2023-12-31", "TRAIN 2018-23")
summarize("2024-01-01", "2026-11-12", "TEST  2024-26")
for y in range(2019, 2027): summarize(f"{y}-01-01", f"{y}-12-31", str(y))
