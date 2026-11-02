"""
Unit tests for NEPTUNE Entry Filters & Hypothesis Evaluator (`test_entry_filters.py`).

Verifies:
- Rule S-05: Zero look-ahead bias in higher timeframe lookups.
- Rule A-09: Strictly closed candle evaluations.
- Rule E-02: Unit test coverage for all entry filter hypotheses (H1 to H7).
- Partition integrity and chronological separation.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest

from app.analytics.filters import (
    filter_trend_strength_adx,
    filter_higher_timeframe_alignment,
    filter_momentum_confirmation,
    filter_volume_confirmation,
    filter_volatility_bounds,
    filter_regime_confidence,
    filter_confluence_ensemble,
)
from app.data.market.validator import ValidatedCandle
from app.simulation.filter_evaluator import FilterHypothesisEvaluator
from app.simulation.models import SimulatedTrade


def _generate_synthetic_candles(
    n: int,
    base_price: float = 100.0,
    trend_step: float = 0.5,
    start_dt: datetime = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
    hours_step: int = 1,
) -> list[ValidatedCandle]:
    """Helper creating n synthetic closed candles with steady trend."""
    candles = []
    curr = base_price
    for i in range(n):
        ts = (start_dt + timedelta(hours=i * hours_step)).isoformat().replace("+00:00", "Z")
        curr += trend_step
        candles.append(
            ValidatedCandle(
                symbol="BTCUSDT",
                timeframe="1h",
                timestamp=ts,
                open=curr - 0.2,
                high=curr + 1.0,
                low=curr - 1.0,
                close=curr,
                volume=100.0 + (i % 5) * 10.0,
                is_closed=True,
            )
        )
    return candles


class TestEntryFilters:
    """Tests for H1-H7 entry filter hypotheses."""

    def test_h1_trend_strength_adx(self):
        # 40 candles with strong upward trend
        candles = _generate_synthetic_candles(40, base_price=100.0, trend_step=1.0)
        
        # Long should pass strong trend
        dec_long = filter_trend_strength_adx(candles, direction="LONG", min_adx=20.0, require_di=True)
        assert dec_long.passed is True
        assert dec_long.telemetry["adx"] >= 20.0
        assert dec_long.telemetry["plus_di"] > dec_long.telemetry["minus_di"]

        # Short should fail because trend is bullish (+DI > -DI)
        dec_short = filter_trend_strength_adx(candles, direction="SHORT", min_adx=20.0, require_di=True)
        assert dec_short.passed is False
        assert "Direction conflict" in dec_short.rejection_reason

        # Excessive threshold should fail
        dec_high = filter_trend_strength_adx(candles, direction="LONG", min_adx=150.0)
        assert dec_high.passed is False
        assert "below threshold" in dec_high.rejection_reason

    def test_h2_higher_timeframe_alignment_no_lookahead(self):
        # 70 HTF candles starting earlier
        htf_candles = _generate_synthetic_candles(70, base_price=100.0, trend_step=0.5)
        target_ts = htf_candles[55].timestamp
        
        # Test Long alignment
        dec = filter_higher_timeframe_alignment(target_ts, "LONG", htf_candles)
        assert dec.passed is True
        # Rule S-05 check: telemetry HTF timestamp must not exceed target_ts
        assert dec.telemetry["htf_timestamp"] <= target_ts

        # Short should be rejected on bullish HTF
        dec_short = filter_higher_timeframe_alignment(target_ts, "SHORT", htf_candles)
        assert dec_short.passed is False
        assert "HTF Trend Bullish" in dec_short.rejection_reason

    def test_h3_momentum_confirmation(self):
        candles = _generate_synthetic_candles(40, base_price=100.0, trend_step=0.2)
        
        # Check wide corridor
        dec = filter_momentum_confirmation(candles, "LONG", min_rsi=30.0, max_rsi=100.0, require_macd_accel=False)
        assert dec.passed is True

        # Out of bounds RSI corridor should fail
        dec_fail = filter_momentum_confirmation(candles, "LONG", min_rsi=10.0, max_rsi=20.0, require_macd_accel=False)
        assert dec_fail.passed is False
        assert "outside active corridor" in dec_fail.rejection_reason

    def test_h4_volume_confirmation(self):
        candles = _generate_synthetic_candles(30, base_price=100.0, trend_step=0.1)
        dec = filter_volume_confirmation(candles, "LONG", min_rvol=0.80)
        assert dec.passed is True
        assert dec.telemetry["rvol"] >= 0.80

        # High RVOL demand should fail
        dec_high = filter_volume_confirmation(candles, "LONG", min_rvol=5.0)
        assert dec_high.passed is False
        assert "below threshold" in dec_high.rejection_reason

    def test_h5_volatility_bounds(self):
        candles = _generate_synthetic_candles(30, base_price=100.0, trend_step=0.1)
        dec = filter_volatility_bounds(candles, "LONG", min_vol_pct=0.50, max_vol_pct=3.0)
        assert dec.passed is True
        assert 0.50 <= dec.telemetry["volatility_pct"] <= 3.0

        # Excessively tight bounds should reject
        dec_tight = filter_volatility_bounds(candles, "LONG", min_vol_pct=5.0, max_vol_pct=10.0)
        assert dec_tight.passed is False
        assert "below minimum" in dec_tight.rejection_reason

    def test_h6_regime_confidence(self):
        dec_pass = filter_regime_confidence("TRENDING_BULL", 0.80, "LONG", min_confidence=0.65)
        assert dec_pass.passed is True

        # Regime mismatch
        dec_mismatch = filter_regime_confidence("TRENDING_BEAR", 0.80, "LONG", min_confidence=0.65)
        assert dec_mismatch.passed is False

        # Confidence too low
        dec_low_conf = filter_regime_confidence("TRENDING_BULL", 0.50, "LONG", min_confidence=0.65)
        assert dec_low_conf.passed is False

    def test_h7_confluence_ensemble(self):
        start_htf = datetime(2025, 12, 1, 0, 0, tzinfo=timezone.utc)
        htf = _generate_synthetic_candles(80, base_price=100.0, trend_step=0.8, start_dt=start_htf, hours_step=4)
        
        start_ltf = datetime(2025, 12, 10, 0, 0, tzinfo=timezone.utc)
        candles = _generate_synthetic_candles(40, base_price=100.0, trend_step=0.8, start_dt=start_ltf, hours_step=1)
        curr_ts = candles[-1].timestamp

        dec = filter_confluence_ensemble(candles, "LONG", curr_ts, htf_candles=htf, min_adx=20.0, min_rvol=0.80, min_vol_pct=0.50)
        assert dec.passed is True
        assert dec.filter_id == "H7_CONFLUENCE_ENSEMBLE"


class TestChronologicalPartitions:
    """Verifies partition splitting invariants."""

    def test_chronological_trade_split_invariants(self):
        trades = []
        base_dt = datetime(2026, 1, 1, tzinfo=timezone.utc)
        for i in range(100):
            ts = (base_dt + timedelta(hours=i)).isoformat().replace("+00:00", "Z")
            trades.append(
                SimulatedTrade(
                    trade_id=f"t_{i}",
                    symbol="BTCUSDT",
                    timeframe="1h",
                    direction="LONG",
                    signal_timestamp=ts,
                    entry_timestamp=ts,
                    entry_price=Decimal("100.0"),
                    exit_timestamp=(base_dt + timedelta(hours=i + 1)).isoformat().replace("+00:00", "Z"),
                    exit_price=Decimal("101.0"),
                    stop_loss=Decimal("95.0"),
                    take_profit=Decimal("110.0"),
                    position_size=Decimal("1.0"),
                    gross_pnl=Decimal("1.0"),
                    fees=Decimal("0.1"),
                    spread_cost=Decimal("0.05"),
                    slippage_cost=Decimal("0.05"),
                    net_pnl=Decimal("0.80"),
                    exit_reason="TAKE_PROFIT",
                    market_regime="TRENDING_BULL",
                )
            )

        partitions = FilterHypothesisEvaluator.partition_trades_chronologically(trades, train_pct=0.50, val_pct=0.25)
        
        train = partitions["train"]
        val = partitions["validation"]
        oos = partitions["oos"]

        assert len(train) == 50
        assert len(val) == 25
        assert len(oos) == 25

        # Strict chronological ordering without overlap
        assert train[-1].entry_timestamp < val[0].entry_timestamp
        assert val[-1].entry_timestamp < oos[0].entry_timestamp

        # No duplicates
        all_ids = [t.trade_id for t in train + val + oos]
        assert len(all_ids) == len(set(all_ids)) == 100

    def test_metrics_evaluation_calculation(self):
        trades = [
            SimulatedTrade(
                trade_id="t1",
                symbol="BTCUSDT",
                timeframe="1h",
                direction="LONG",
                signal_timestamp="2026-01-01T00:00:00Z",
                entry_timestamp="2026-01-01T00:00:00Z",
                entry_price=Decimal("100.0"),
                exit_timestamp="2026-01-01T01:00:00Z",
                exit_price=Decimal("105.0"),
                stop_loss=Decimal("95.0"),
                take_profit=Decimal("110.0"),
                position_size=Decimal("1.0"),
                gross_pnl=Decimal("5.0"),
                fees=Decimal("0.1"),
                spread_cost=Decimal("0.02"),
                slippage_cost=Decimal("0.03"),
                net_pnl=Decimal("4.85"),
                exit_reason="TAKE_PROFIT",
                market_regime="TRENDING_BULL",
            ),
            SimulatedTrade(
                trade_id="t2",
                symbol="BTCUSDT",
                timeframe="1h",
                direction="LONG",
                signal_timestamp="2026-01-01T02:00:00Z",
                entry_timestamp="2026-01-01T02:00:00Z",
                entry_price=Decimal("100.0"),
                exit_timestamp="2026-01-01T03:00:00Z",
                exit_price=Decimal("98.0"),
                stop_loss=Decimal("95.0"),
                take_profit=Decimal("110.0"),
                position_size=Decimal("1.0"),
                gross_pnl=Decimal("-2.0"),
                fees=Decimal("0.1"),
                spread_cost=Decimal("0.02"),
                slippage_cost=Decimal("0.03"),
                net_pnl=Decimal("-2.15"),
                exit_reason="STOP_LOSS",
                market_regime="TRENDING_BULL",
            ),
        ]

        metrics = FilterHypothesisEvaluator.evaluate_trades(trades, "TEST_FILTER", "TRAIN")
        assert metrics.total_trades == 2
        assert metrics.winning_trades == 1
        assert metrics.losing_trades == 1
        assert metrics.win_rate_pct == 50.0
        assert metrics.net_pnl == 2.70
        assert metrics.profit_factor == 2.26
        assert metrics.expectancy == 1.35
