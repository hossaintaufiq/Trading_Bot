"""ORB research run (ADR-038): frozen defaults, no tuning. Usage: python scripts/orb_research.py"""
import sys
from decimal import Decimal
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.simulation.orb_backtest import BTConfig, run_orb  # noqa: E402
from app.simulation.time_machine import run_time_machine, session_matrix  # noqa: E402
from app.strategies.orb_breakout import ORBConfig, find_setup  # noqa: E402


def load(symbol):
    files = sorted((ROOT / "storage" / "historical" / symbol / "15m").glob("*/*/*.parquet"))
    df = pd.concat([pd.read_parquet(f) for f in files]).drop_duplicates("timestamp")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df.sort_values("timestamp").reset_index(drop=True)


cfg = ORBConfig()
for sym in ("BTCUSDT", "ETHUSDT", "BNBUSDT"):
    df = load(sym)
    res = run_orb(df, cfg, BTConfig())
    t = res.trades
    wins = [x for x in t if x.net_pnl > 0]
    reasons = {r: sum(1 for x in t if x.reason == r) for r in ("target", "stop", "eod")}
    gross = sum((x.gross_pnl for x in t), Decimal(0)); fees = sum((x.fees for x in t), Decimal(0))
    print(f"{sym}: bars={len(df)} {df.timestamp.iloc[0].date()}..{df.timestamp.iloc[-1].date()} trades={len(t)} "
          f"wins={len(wins)} {reasons} gross={gross:.2f} fees={fees:.2f} net={res.final_equity-1000:.2f} "
          f"final={res.final_equity:.2f} maxDD={res.max_drawdown*100:.2f}%")
    # Time Machine on the most recent signal day, history strictly before it
    days = df.groupby(df.timestamp.dt.normalize())
    for date, day in reversed(list(days)):
        day = day.reset_index(drop=True)
        s = find_setup(day, cfg)
        if s and len(day) == 96:
            hist = session_matrix(df, 96, before=date)
            risk = s.signal_price - s.stop
            r = run_time_machine(hist, s.trigger_idx + 1, s.signal_price, s.stop, s.signal_price + 1.5 * risk, 10000, 19)
            print(f"   TimeMachine {date.date()} (history {r.n_sessions} sessions): target {r.p_target:.1%} stop {r.p_stop:.1%} open {r.p_open:.1%}")
            break
