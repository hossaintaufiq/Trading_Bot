"""Tests for the day-trading additions (ADR-038): ORB strategy, Time Machine, ORB backtest, trade limits."""
from decimal import Decimal

import numpy as np
import pandas as pd

from app.risk.trade_limits import TradeLimits, check_limits, size_position
from app.simulation.orb_backtest import BTConfig, run_orb
from app.simulation.time_machine import STOP, TARGET, OPEN, first_touch, run_time_machine, session_matrix
from app.strategies.base_strategy import TimeFrame
from app.strategies.orb_breakout import ORBConfig, ORBStrategy, find_setup

CFG = ORBConfig(bars_per_day=12, or_bars=3, cutoff_bar=8, target_r=1.5)


def _day(date, rows):
    """rows: list of (open, high, low, close); 12 bars of 2h starting 00:00 UTC."""
    ts = pd.date_range(date, periods=len(rows), freq="2h", tz="UTC")
    return pd.DataFrame({"timestamp": ts, "open": [r[0] for r in rows], "high": [r[1] for r in rows],
                         "low": [r[2] for r in rows], "close": [r[3] for r in rows], "volume": 1.0})


def _flat(n, p=100.0):
    return [(p, p + 1, p - 1, p)] * n


# ---------- setup / strategy ----------
def test_setup_requires_close_above_range_not_a_wick():
    rows = _flat(3) + [(100, 105, 99, 100.5)] + _flat(8)          # wick to 105, closes inside range
    assert find_setup(_day("2024-01-01", rows), CFG) is None
    rows = _flat(3) + [(100, 103, 100, 102.5)] + _flat(8)         # closes above range high 101
    s = find_setup(_day("2024-01-01", rows), CFG)
    assert s is not None and s.trigger_idx == 3 and s.range_high == 101 and s.range_low == 99
    assert s.stop == 100.0                                         # range midpoint


def test_no_entry_after_cutoff():
    rows = _flat(9) + [(100, 110, 100, 109)] + _flat(2)
    assert find_setup(_day("2024-01-01", rows), CFG) is None


def test_strategy_signals_only_on_trigger_bar_and_ignores_open_candle():
    rows = _flat(3) + [(100, 103, 100, 102.5)]
    df = _day("2024-01-01", rows)
    sig = ORBStrategy(CFG).evaluate(df, "BTCUSDT", TimeFrame.M15)
    assert sig is not None and sig.reward_risk_ratio >= 1.5 - 1e-9
    df["is_closed"] = [True, True, True, False]
    assert ORBStrategy(CFG).evaluate(df, "BTCUSDT", TimeFrame.M15) is None
    later = _day("2024-01-01", rows + _flat(1))                    # trigger bar is no longer the last bar
    assert ORBStrategy(CFG).evaluate(later, "BTCUSDT", TimeFrame.M15) is None


# ---------- first touch ----------
def test_first_touch_stop_wins_ties_and_open_when_neither():
    highs = np.array([[101, 106], [101, 101], [110, 110]], dtype=float)
    lows = np.array([[99, 94], [99, 99], [101, 101]], dtype=float)
    out, idx = first_touch(highs, lows, stop=95.0, target=105.0)
    assert out.tolist() == [STOP, OPEN, TARGET]                    # row0: bar1 touches both -> stop first
    assert idx[0] == 1 and idx[2] == 0


# ---------- time machine ----------
def _hist(days, drift):
    frames = []
    for d in range(days):
        p, rows = 100.0, []
        for _ in range(12):
            c = p * (1 + drift)
            rows.append((p, max(p, c) * 1.001, min(p, c) * 0.999, c))
            p = c
        frames.append(_day(pd.Timestamp("2024-01-01", tz="UTC") + pd.Timedelta(days=d), rows))
    return pd.concat(frames, ignore_index=True)


def test_time_machine_is_deterministic_and_probabilities_sum_to_one():
    hist = session_matrix(_hist(30, 0.002), bars_per_day=12)
    a = run_time_machine(hist, k_fill=4, entry=100.0, stop=99.0, target=101.5, n_paths=500, seed=7)
    b = run_time_machine(hist, k_fill=4, entry=100.0, stop=99.0, target=101.5, n_paths=500, seed=7)
    assert a == b
    assert abs(a.p_target + a.p_stop + a.p_open - 1.0) < 1e-9
    assert a.p_target > 0.9                                        # strongly rising history reaches target


def test_time_machine_falling_history_hits_stop_for_both_methods():
    hist = session_matrix(_hist(30, -0.004), bars_per_day=12)
    for m in ("session_block", "candle_iid"):
        r = run_time_machine(hist, 4, 100.0, 99.0, 101.5, n_paths=300, seed=1, method=m)
        assert r.p_stop > 0.9


def test_session_matrix_excludes_history_on_or_after_signal_date():
    df = _hist(10, 0.001)
    m = session_matrix(df, bars_per_day=12, before=pd.Timestamp("2024-01-06", tz="UTC"))
    assert m.n_sessions == 5                                       # Jan 1-5 only: no look-ahead
    assert session_matrix(df, 12).n_sessions == 10


# ---------- backtest ----------
def test_backtest_target_hit_pnl_reconciles_with_costs():
    # range 99-101, trigger bar 3 closes 102 (stop 100, R=2, target 105), next open 102, then runs to 106
    rows = _flat(3) + [(100, 103, 100, 102)] + [(102, 106, 101.5, 105.5)] + _flat(7, 105)
    cfg = BTConfig(initial=Decimal("1000"), risk_pct=Decimal("0.005"))
    res = run_orb(_day("2024-01-01", rows), CFG, cfg)
    assert len(res.trades) == 1
    t = res.trades[0]
    assert t.reason == "target" and t.net_pnl == t.gross_pnl - t.fees
    assert res.final_equity == Decimal("1000") + t.net_pnl         # ledger reconciles
    assert t.entry_price > Decimal("102")                          # slippage worsens the fill (A-10)
    assert t.exit_price < Decimal("105")


def test_backtest_stop_exit_and_loss_bounded_near_risk():
    rows = _flat(3) + [(100, 103, 100, 102)] + [(102, 102.5, 99, 99.5)] + _flat(7, 99.5)
    res = run_orb(_day("2024-01-01", rows), CFG, BTConfig())
    t = res.trades[0]
    assert t.reason == "stop" and t.net_pnl < 0
    assert -t.net_pnl < Decimal("1000") * Decimal("0.005") * Decimal("1.6")   # ~risk plus costs/slippage


def test_backtest_skips_gap_below_stop_and_flat_at_session_end():
    gap = _flat(3) + [(100, 103, 100, 102)] + [(99, 99.5, 98, 98.5)] + _flat(7, 98.5)
    assert run_orb(_day("2024-01-01", gap), CFG, BTConfig()).trades == []
    drift = _flat(3) + [(100, 103, 100, 102)] + [(102, 103, 101.5, 102.5)] + _flat(7, 102.5)
    assert run_orb(_day("2024-01-01", drift), CFG, BTConfig()).trades[0].reason == "eod"


def test_backtest_never_peeks_at_the_future_for_entry():
    rows = _flat(3) + [(100, 103, 100, 102)] + _flat(8, 102)
    a = run_orb(_day("2024-01-01", rows), CFG, BTConfig())
    b = run_orb(_day("2024-01-01", rows[:6]), CFG, BTConfig())    # truncated day: same entry
    assert a.trades[0].entry_price == b.trades[0].entry_price


# ---------- trade limits ----------
def test_size_position_risks_exactly_the_budget_and_never_levers():
    q = size_position(Decimal("1000"), Decimal("0.005"), Decimal("100"), Decimal("99"))
    assert q == Decimal("5")                                       # $5 risk / $1 per unit
    q2 = size_position(Decimal("1000"), Decimal("0.005"), Decimal("100"), Decimal("99.9"), fee_rate=Decimal("0.001"))
    assert q2 * Decimal("100") * Decimal("1.001") <= Decimal("1000")


def test_check_limits_blocks_each_violation():
    lim = TradeLimits()
    ok = dict(equity=Decimal("1000"), entry=Decimal("100"), stop=Decimal("99"), target=Decimal("101.5"),
              trades_today=0, hour_utc=3)
    assert check_limits(limits=lim, **ok).passed
    assert "reward_risk" in check_limits(limits=lim, **{**ok, "target": Decimal("101")}).failed
    assert "trades_per_day" in check_limits(limits=lim, **{**ok, "trades_today": 2}).failed
    assert "entry_window" in check_limits(limits=lim, **{**ok, "hour_utc": 15}).failed
    assert "stop_side" in check_limits(limits=lim, **{**ok, "stop": Decimal("101")}).failed
