"""
ORB paper backtest (ADR-038). Decimal accounting (A-01), UTC days (A-02).

Execution model (A-09, A-10): the signal is decided at the CLOSE of the trigger bar and filled at the OPEN of
the next bar with slippage + half-spread against us and a fee on both sides. Stop/target are checked from the
fill bar onward; if one bar touches both, the stop is assumed first. A gap through the stop skips the trade.
Open positions are flattened at the close of the last bar of the day. One trade per day, long-only, no leverage.
Risk sizing uses `size_position` (risk_pct of CURRENT equity at the stop).
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

import pandas as pd

from app.risk.trade_limits import size_position
from app.simulation.daily_trend_backtest import FEE, HALF_SPREAD, SLIP
from app.simulation.time_machine import STOP, TARGET, first_touch
from app.strategies.orb_breakout import ORBConfig, find_setup


@dataclass
class BTConfig:
    initial: Decimal = Decimal("1000")
    risk_pct: Decimal = Decimal("0.005")


@dataclass
class ORBTrade:
    date: str
    entry_price: Decimal
    exit_price: Decimal
    qty: Decimal
    reason: str                # target | stop | eod
    gross_pnl: Decimal
    fees: Decimal
    net_pnl: Decimal


@dataclass
class ORBResult:
    trades: List[ORBTrade] = field(default_factory=list)
    final_equity: Decimal = Decimal(0)
    max_drawdown: Decimal = Decimal(0)


def _d(x) -> Decimal:
    return Decimal(str(float(x)))


def run_orb(df: pd.DataFrame, cfg: ORBConfig, bt: BTConfig) -> ORBResult:
    """`df`: closed bars, ascending, UTC `timestamp`. Days that do not start with a full opening range are skipped."""
    ts = pd.to_datetime(df["timestamp"], utc=True)
    equity = bt.initial
    peak, mdd = equity, Decimal(0)
    res = ORBResult(final_equity=equity)
    slip = SLIP + HALF_SPREAD
    for date, day in df.groupby(ts.dt.normalize(), sort=True):
        day = day.reset_index(drop=True)
        setup = find_setup(day, cfg)
        if setup is None or setup.trigger_idx + 1 >= len(day):
            continue
        f = setup.trigger_idx + 1                               # fill bar = next bar after the trigger close
        fill = _d(day["open"].iloc[f]) * (1 + slip)
        stop = _d(setup.stop)
        if fill <= stop:
            continue                                            # gapped through the stop
        target = _d(setup.signal_price) + _d(cfg.target_r) * (_d(setup.signal_price) - stop)
        qty = size_position(equity, bt.risk_pct, fill, stop, FEE)
        if qty <= 0:
            continue
        hi = day["high"].iloc[f:].astype(float).to_numpy()
        lo = day["low"].iloc[f:].astype(float).to_numpy()
        out, idx = first_touch(hi, lo, float(stop), float(target))
        code, j = int(out[0]), int(idx[0])
        if code == STOP:
            bar_open = _d(day["open"].iloc[f + j])
            raw, reason = min(stop, bar_open), "stop"           # a gap down fills at the open, not the stop
        elif code == TARGET:
            raw, reason = target, "target"
        else:
            raw, reason = _d(day["close"].iloc[-1]), "eod"
        exit_px = raw * (1 - slip)
        fees = qty * fill * FEE + qty * exit_px * FEE
        gross = qty * (exit_px - fill)
        net = gross - fees
        equity += net
        peak = max(peak, equity)
        mdd = max(mdd, (peak - equity) / peak)
        res.trades.append(ORBTrade(str(pd.Timestamp(date).date()), fill, exit_px, qty, reason, gross, fees, net))
    res.final_equity, res.max_drawdown = equity, mdd
    return res
