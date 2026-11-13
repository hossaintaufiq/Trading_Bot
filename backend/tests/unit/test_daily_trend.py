"""Tests for daily_trend_v1 (ADR-037): no look-ahead, correct state machine, Decimal cost accounting."""
from decimal import Decimal

import pandas as pd

from app.simulation.daily_trend_backtest import FEE, HALF_SPREAD, SLIP, run_sleeve
from app.strategies.daily_trend import DailyTrendConfig, DailyTrendStrategy, compute_positions


def _df(closes):
    ts = pd.date_range("2024-01-01", periods=len(closes), freq="D", tz="UTC")
    return pd.DataFrame({"timestamp": ts, "open": closes, "high": closes, "low": closes, "close": closes, "volume": 1.0})


def test_enter_on_breakout_exit_on_breakdown():
    closes = [10.0] * 5 + [11.0, 12.0, 13.0, 9.0, 9.0]
    pos = compute_positions(closes, 3, 3)
    assert pos[:5] == [0] * 5
    assert pos[5] == 1 and pos[7] == 1
    assert pos[8] == 0


def test_no_lookahead_future_bars_do_not_change_past_state():
    base = [10.0, 10.5, 10.2, 10.8, 11.5, 12.0, 11.0, 10.0, 9.0, 12.0]
    a = compute_positions(base, 3, 2)
    b = compute_positions(base + [1.0, 100.0, 1.0], 3, 2)
    assert b[: len(base)] == a


def test_signal_only_on_flat_to_long_flip_and_ignores_open_candle():
    df = _df([10.0] * 5 + [11.0])
    sig = DailyTrendStrategy(DailyTrendConfig(entry_lookback=3, exit_lookback=3)).evaluate(df, "BTCUSDT")
    assert sig is not None and sig.entry_price == 11.0
    df["is_closed"] = [True] * 5 + [False]
    assert DailyTrendStrategy(DailyTrendConfig(entry_lookback=3, exit_lookback=3)).evaluate(df, "BTCUSDT") is None


def test_fill_at_next_open_with_costs_and_pnl_reconciles():
    closes = [10.0] * 5 + [11.0, 12.0, 13.0, 9.0, 9.0, 9.0]
    df = _df(closes)
    df["open"] = [10.0] * 5 + [11.0, 11.5, 12.5, 13.0, 9.5, 9.0]
    cfg = DailyTrendConfig(entry_lookback=3, exit_lookback=3)
    cap = Decimal("1000")
    res = run_sleeve("X", df, cap, cfg)
    assert len(res.trades) == 1
    t = res.trades[0]
    # signal at close of bar 5 -> entry at open of bar 6 (11.5), not at bar 5's price
    assert t.entry_time == "2024-01-07"
    assert t.entry_price == Decimal("11.5") * (1 + SLIP + HALF_SPREAD)
    assert t.exit_time == "2024-01-10" and t.exit_price == Decimal("9.5") * (1 - SLIP - HALF_SPREAD)
    final = res.equity["2024-01-11"]
    assert abs(final - (cap + t.net_pnl)) < Decimal("1e-9")      # accounting identity: cash == capital + net pnl
    assert t.fees > 0


def test_flat_market_no_trades_no_cost():
    res = run_sleeve("X", _df([10.0] * 30), Decimal("1000"), DailyTrendConfig())
    assert res.trades == [] and res.equity["2024-01-30"] == Decimal("1000")
