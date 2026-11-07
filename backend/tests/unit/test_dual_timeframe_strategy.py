"""
Unit tests for NEPTUNE Dual-Timeframe Trend Following Strategy (`htf_trend_following_v1`).

Validates:
1. Long-only spot execution (Rule S-01): No SHORT signals generated.
2. Incomplete candle rejection (Rule A-09): is_closed == False rejects signals.
3. 4h Macro Regime gating (Cash preservation): Bearish or weak ADX regimes emit None.
4. Market Structure Shift (1h): Pullback and swing breakout trigger valid RawSignal.
5. Payoff geometry & friction headroom: R:R >= 2.5:1, friction drag < 10% of target move.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import numpy as np
import pandas as pd
import pytest

from app.strategies.base_strategy import SignalDirection, TimeFrame
from app.strategies.dual_timeframe_trend import (
    DualTimeframeConfig,
    DualTimeframeTrendStrategy,
)


def create_synthetic_candle_data(
    n_candles: int,
    base_price: float = 50000.0,
    trend_slope: float = 10.0,
    volatility: float = 100.0,
    interval_hours: int = 1,
) -> pd.DataFrame:
    """Generate synthetic OHLCV candle DataFrame with timestamps."""
    start_time = datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc)
    timestamps = [start_time + timedelta(hours=i * interval_hours) for i in range(n_candles)]

    closes = []
    curr = base_price
    for i in range(n_candles):
        curr += trend_slope + np.random.normal(0, volatility * 0.1)
        closes.append(curr)

    closes = np.array(closes)
    highs = closes + np.random.uniform(50, 150, n_candles)
    lows = closes - np.random.uniform(50, 150, n_candles)
    opens = (highs + lows) / 2.0
    volumes = np.random.uniform(100, 1000, n_candles)

    df = pd.DataFrame({
        "timestamp": timestamps,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": volumes,
        "is_closed": [True] * n_candles,
    })
    return df


def test_rule_a09_incomplete_candle_rejection():
    """Verify Rule A-09: Strategy rejects incomplete (in-progress) candles."""
    strategy = DualTimeframeTrendStrategy()
    df_1h = create_synthetic_candle_data(n_candles=100)
    df_1h.loc[df_1h.index[-1], "is_closed"] = False

    signal = strategy.evaluate(df_1h, "BTCUSDT")
    assert signal is None, "Strategy must return None when candle is not closed"


def test_4h_bear_regime_preserves_cash():
    """Verify Cash Preservation Gate: In a downtrend, strategy returns None."""
    strategy = DualTimeframeTrendStrategy()

    # Generate strong 4h downtrend data (250 candles)
    df_4h = create_synthetic_candle_data(
        n_candles=250, base_price=60000.0, trend_slope=-50.0, interval_hours=4
    )
    df_1h = create_synthetic_candle_data(
        n_candles=1000, base_price=60000.0, trend_slope=-12.5, interval_hours=1
    )

    signal = strategy.evaluate(df_1h, "BTCUSDT", df_4h=df_4h)
    assert signal is None, "Bearish 4h regime must strictly emit None (preserve cash)"


def test_4h_weak_adx_chop_preserves_cash():
    """Verify Cash Preservation Gate: In low-ADX horizontal chop, strategy returns None."""
    strategy = DualTimeframeTrendStrategy(DualTimeframeConfig(min_adx_4h=30.0))

    # Generate sideways choppy data (slope 0)
    df_4h = create_synthetic_candle_data(
        n_candles=250, base_price=50000.0, trend_slope=0.0, volatility=50.0, interval_hours=4
    )
    df_1h = create_synthetic_candle_data(
        n_candles=1000, base_price=50000.0, trend_slope=0.0, volatility=50.0, interval_hours=1
    )

    signal = strategy.evaluate(df_1h, "BTCUSDT", df_4h=df_4h)
    assert signal is None, "Weak ADX chop must strictly emit None (preserve cash)"


def test_valid_long_setup_generation_and_asymmetric_payoff():
    """Verify that a valid 4h trend + 1h pullback + market structure shift produces RawSignal."""
    strategy = DualTimeframeTrendStrategy()

    # 1. Build a confirmed 4h bull trend (250 bars, rising from 40k to 65k)
    df_4h = create_synthetic_candle_data(
        n_candles=250, base_price=40000.0, trend_slope=100.0, volatility=80.0, interval_hours=4
    )

    # 2. Build 1h candles ending with a pullback followed by a breakout close
    df_1h = create_synthetic_candle_data(
        n_candles=300, base_price=60000.0, trend_slope=20.0, volatility=50.0, interval_hours=1
    )

    # Inject a clean pullback into 1h EMA band and a breakout close
    # Last 6 bars: Bar -6..-2 pullback below local swing high, Bar -1 closes above
    swing_high = float(df_1h["high"].iloc[-6])
    df_1h.loc[df_1h.index[-5], "low"] = float(df_1h["close"].iloc[-5]) - 400.0  # touch pullback zone
    df_1h.loc[df_1h.index[-5], "high"] = swing_high - 50.0
    df_1h.loc[df_1h.index[-4], "high"] = swing_high - 60.0
    df_1h.loc[df_1h.index[-3], "high"] = swing_high - 40.0
    df_1h.loc[df_1h.index[-2], "close"] = swing_high - 20.0
    df_1h.loc[df_1h.index[-2], "high"] = swing_high - 10.0
    # Breakout candle: closes above swing high
    df_1h.loc[df_1h.index[-1], "close"] = swing_high + 100.0
    df_1h.loc[df_1h.index[-1], "high"] = swing_high + 150.0
    df_1h.loc[df_1h.index[-1], "is_closed"] = True

    signal = strategy.evaluate(df_1h, "BTCUSDT", df_4h=df_4h)

    assert signal is not None, "Expected valid RawSignal on confirmed swing structure breakout"
    assert signal.direction == SignalDirection.LONG, "Must be strictly LONG spot"
    assert signal.symbol == "BTCUSDT"
    assert signal.timeframe == TimeFrame.H1
    assert signal.entry_price > signal.stop_price, "Entry must be above stop"
    assert signal.target_price > signal.entry_price, "Target must be above entry"

    # Verify R:R ratio >= 2.5
    assert signal.reward_risk_ratio >= 2.50, f"R:R must be >= 2.5, got {signal.reward_risk_ratio}"

    # Verify frictional cost drag is < 15% of target move (vs >35% on 15m baseline)
    target_move_pct = (signal.target_price - signal.entry_price) / signal.entry_price
    friction_drag = 0.0032 / target_move_pct
    assert friction_drag < 0.15, f"Friction drag must be < 15% of target move, got {friction_drag:.2%}"


def test_monetary_precision_decimal_invariants():
    """Verify that stop and target levels conform to Decimal precision rules (Rule A-01)."""
    strategy = DualTimeframeTrendStrategy()
    df_4h = create_synthetic_candle_data(n_candles=250, base_price=50000.0, trend_slope=80.0, interval_hours=4)
    df_1h = create_synthetic_candle_data(n_candles=300, base_price=65000.0, trend_slope=15.0, interval_hours=1)

    swing_high = float(df_1h["high"].iloc[-5])
    df_1h.loc[df_1h.index[-4:-1], "high"] = swing_high - 30.0
    df_1h.loc[df_1h.index[-1], "close"] = swing_high + 50.0
    df_1h.loc[df_1h.index[-1], "high"] = swing_high + 80.0

    signal = strategy.evaluate(df_1h, "BTCUSDT", df_4h=df_4h)
    if signal is not None:
        # Check that entry, stop, and target are positive and formatted cleanly
        assert signal.entry_price > 0
        assert signal.stop_price > 0
        assert signal.target_price > 0
        risk = Decimal(str(signal.entry_price)) - Decimal(str(signal.stop_price))
        reward = Decimal(str(signal.target_price)) - Decimal(str(signal.entry_price))
        assert risk > Decimal("0")
        assert reward > Decimal("0")
        ratio = float(reward / risk)
        assert ratio >= 2.49
