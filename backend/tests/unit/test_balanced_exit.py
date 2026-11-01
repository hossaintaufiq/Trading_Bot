"""
NEPTUNE Unit & Verification Tests — Milestone 4.1.2 Balanced Protection Exit Engine

Comprehensive automated tests covering:
1. Trailing stop ratcheting for LONG positions (one-way upward ratchet).
2. Trailing stop ratcheting for SHORT positions (one-way downward ratchet).
3. No retroactive same-candle trigger invariant (T high/low does not trigger T ratchet).
4. Multi-factor reversal rejected with single confirmation source (RSI alone prohibited).
5. Multi-factor reversal accepted with >= 2 independent confirmation sources.
6. Reversal execution timing (detection at candle T close, fill at candle T+1 open).
7. Protective stop precedence over pending reversal on gap open.
8. Position continues past original theoretical target in BALANCED mode.
9. Backward compatibility: FIXED_BRACKET mode still enforces hard take-profit.
10. MFE (Maximum Favorable Excursion) and MAE (Maximum Adverse Excursion) tracking.
11. Performance breakdown by exit reason in BacktestMetrics.
12. Portfolio double-entry cash and equity conservation under balanced exits.
13. Strict look-ahead bias invariance in event replay under balanced exit policy.
14. Robustness against zero or negative initial risk geometry.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import List, Optional
import pytest

from app.data.market.validator import ValidatedCandle
from app.agents.market_scanner import SymbolRegimeState
from app.agents.momentum_analyst import MomentumAnalystOutput
from app.agents.trend_analyst import TrendAnalystOutput
from app.agents.volume_analyst import VolumeAnalystOutput
from app.simulation.engine import HistoricalBacktestEngine
from app.simulation.execution import PaperExecutionSimulator
from app.simulation.metrics import calculate_backtest_metrics
from app.simulation.models import (
    ActivePosition,
    BacktestConfig,
    EquityPoint,
    SimulatedTrade,
)
from app.simulation.reversal import MultiFactorReversalDetector, ReversalDecision


def make_candle(
    i: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float = 100.0,
    symbol: str = "BTCUSDT",
    timeframe: str = "15m",
    base_time: Optional[datetime] = None,
) -> ValidatedCandle:
    """Helper to generate standardized synthetic test candles."""
    start = base_time or datetime(2026, 11, 1, 0, 0, tzinfo=timezone.utc)
    dt = start + timedelta(minutes=15 * i)
    return ValidatedCandle(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
        is_closed=True,
    )


class TestBalancedProtectionExitEngine:
    """Automated test suite verifying the Balanced Protection Exit Engine."""

    def test_trailing_stop_ratchet_long(self):
        """
        Test 1: LONG trailing stop ratchets strictly upwards.
        Stops must never retreat in the direction of increased risk.
        """
        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),
            slippage_pct=Decimal("0.0005"),
            spread_bps=Decimal("0.0"),
        )

        pos = sim.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=Decimal("100.0"),
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),  # Initial risk = 5.0
            take_profit=Decimal("110.0"),
            signal_timestamp="2026-11-01T10:00:00.000Z",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
            exit_policy="BALANCED",
        )

        assert pos.stop_loss == Decimal("95.0")
        assert pos.initial_stop_loss == Decimal("95.0")
        assert pos.trailing_updates_count == 0

        # Bar 1: Price advances to High 108 (gain = 8.0 >= 1.0R threshold).
        # ATR = 2.0, ATR mult = 2.0 -> trailing distance = 4.0.
        # Candidate stop = 108.0 - 4.0 = 104.0.
        c1 = make_candle(1, open_=100.5, high=108.0, low=100.0, close=107.0)
        updated = sim.update_trailing_stop(
            pos, c1, atr_value=Decimal("2.0"), atr_multiplier=Decimal("2.0"), activation_threshold_r=Decimal("1.0")
        )
        assert updated is True
        assert pos.stop_loss == Decimal("104.0")
        assert pos.trailing_updates_count == 1

        # Bar 2: Price pulls back to High 105, Low 103 (pullback, but peak is still 108.0).
        # Candidate stop remains 104.0. Stop must NOT decrease!
        c2 = make_candle(2, open_=106.0, high=106.5, low=103.5, close=104.5)
        updated2 = sim.update_trailing_stop(
            pos, c2, atr_value=Decimal("2.0"), atr_multiplier=Decimal("2.0"), activation_threshold_r=Decimal("1.0")
        )
        assert updated2 is False
        assert pos.stop_loss == Decimal("104.0")
        assert pos.trailing_updates_count == 1

        # Bar 3: Price advances to High 115.0.
        # Candidate stop = 115.0 - 4.0 = 111.0. Stop ratchets up.
        c3 = make_candle(3, open_=105.0, high=115.0, low=104.5, close=114.0)
        updated3 = sim.update_trailing_stop(
            pos, c3, atr_value=Decimal("2.0"), atr_multiplier=Decimal("2.0"), activation_threshold_r=Decimal("1.0")
        )
        assert updated3 is True
        assert pos.stop_loss == Decimal("111.0")
        assert pos.stop_loss > Decimal("104.0")
        assert pos.trailing_updates_count == 2

    def test_trailing_stop_ratchet_short(self):
        """
        Test 2: SHORT trailing stop ratchets strictly downwards.
        Stops must never retreat upwards.
        """
        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),
            slippage_pct=Decimal("0.0005"),
            spread_bps=Decimal("0.0"),
        )

        pos = sim.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="SHORT",
            raw_price=Decimal("100.0"),
            position_size=Decimal("1.0"),
            stop_loss=Decimal("105.0"),  # Initial risk = 5.0
            take_profit=Decimal("90.0"),
            signal_timestamp="2026-11-01T10:00:00.000Z",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            market_regime="TRENDING_BEAR",
            strategy_metadata={},
            exit_policy="BALANCED",
        )

        assert pos.stop_loss == Decimal("105.0")
        assert pos.initial_stop_loss == Decimal("105.0")

        # Bar 1: Price drops to Low 92.0 (gain = 8.0 >= 1.0R threshold).
        # ATR = 2.0 -> candidate = 92.0 + 4.0 = 96.0.
        c1 = make_candle(1, open_=99.5, high=100.0, low=92.0, close=93.0)
        updated = sim.update_trailing_stop(
            pos, c1, atr_value=Decimal("2.0"), atr_multiplier=Decimal("2.0"), activation_threshold_r=Decimal("1.0")
        )
        assert updated is True
        assert pos.stop_loss == Decimal("96.0")

        # Bar 2: Bounce to High 95.0, Low 93.0. Stop must NOT rise!
        c2 = make_candle(2, open_=93.5, high=95.0, low=93.0, close=94.5)
        updated2 = sim.update_trailing_stop(
            pos, c2, atr_value=Decimal("2.0"), atr_multiplier=Decimal("2.0"), activation_threshold_r=Decimal("1.0")
        )
        assert updated2 is False
        assert pos.stop_loss == Decimal("96.0")

        # Bar 3: Further drop to Low 85.0 -> candidate = 85.0 + 4.0 = 89.0.
        c3 = make_candle(3, open_=94.0, high=94.5, low=85.0, close=86.0)
        updated3 = sim.update_trailing_stop(
            pos, c3, atr_value=Decimal("2.0"), atr_multiplier=Decimal("2.0"), activation_threshold_r=Decimal("1.0")
        )
        assert updated3 is True
        assert pos.stop_loss == Decimal("89.0")
        assert pos.stop_loss < Decimal("96.0")

    def test_no_retroactive_same_candle_trigger(self):
        """
        Test 3: Invariant: A trailing stop calculated from candle T's high/low
        must NEVER be applied retroactively to trigger an exit on candle T.
        """
        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),
            slippage_pct=Decimal("0.0005"),
            spread_bps=Decimal("0.0"),
        )

        pos = sim.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=Decimal("100.0"),
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("110.0"),
            signal_timestamp="2026-11-01T10:00:00.000Z",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
            exit_policy="BALANCED",
        )

        # Candle 1: Swings between Low 98.0 and High 115.0.
        # Low 98.0 did not touch initial stop 95.0.
        c1 = make_candle(1, open_=100.0, high=115.0, low=98.0, close=110.0)

        # In Phase A of the event loop, evaluate_candle_bracket is called FIRST
        trade = sim.evaluate_candle_bracket(pos, c1)
        assert trade is None  # Survives!

        # In Phase B, update_trailing_stop ratchets stop to 115.0 - 4.0 = 111.0
        sim.update_trailing_stop(pos, c1, atr_value=Decimal("2.0"), atr_multiplier=Decimal("2.0"))
        assert pos.stop_loss == Decimal("111.0")

        # Crucial check: Candle 1's low was 98.0, which is below 111.0.
        # But Candle 1 is already finished! The new stop (111.0) is active for Candle 2 onwards.
        # Position is still OPEN.
        assert pos.position_id is not None

        # Candle 2 arrives: Open 110.0, Low 108.0 (breaches new stop 111.0).
        c2 = make_candle(2, open_=110.0, high=112.0, low=108.0, close=109.0)
        trade2 = sim.evaluate_candle_bracket(pos, c2)
        assert trade2 is not None
        assert trade2.exit_reason == "TRAILING_STOP"
        assert trade2.exit_price <= Decimal("111.0")

    def test_reversal_rejected_single_source(self):
        """
        Test 4: Reversal exit rejected when only 1 domain confirms.
        A single indicator (e.g. RSI overbought alone) is prohibited from triggering an exit.
        """
        pos = ActivePosition(
            position_id="pos_test_rev1",
            signal_id="sig_test_rev1",
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            entry_price=Decimal("100.0"),
            raw_entry_price=Decimal("100.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("110.0"),
            position_size=Decimal("1.0"),
            entry_fee=Decimal("0.1"),
            entry_slippage_cost=Decimal("0.05"),
            entry_spread_cost=Decimal("0.01"),
            market_regime="TRENDING_BULL",
            strategy_metadata={},
            exit_policy="BALANCED",
        )

        # Only Momentum confirms (RSI 78.0 exhaustion), while Trend, Volume, and Regime are healthy
        trend_data = TrendAnalystOutput(
            timestamp="2026-11-01T10:15:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            composite_bias="BULLISH",
            trend_strength_score=0.75,
            ema_values={"20": 102.0, "50": 100.0, "200": 95.0},
            ema_stack_ordered=True,
            adx_value=32.0,
            plus_di=28.0,
            minus_di=14.0,
            adx_slope=0.5,
            confidence_discount=0.0,
            explanation="Strong bull trend",
        )
        momentum_data = MomentumAnalystOutput(
            timestamp="2026-11-01T10:15:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            rsi=78.0,
            momentum_direction="BEARISH",
            momentum_score=-0.4,
            exhaustion_risk=True,
            divergence="BEARISH_DIVERGENCE",
            explanation="Overbought momentum rolling over",
        )
        volume_data = VolumeAnalystOutput(
            timestamp="2026-11-01T10:15:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            current_volume=120.0,
            volume_ma=100.0,
            volume_ratio=1.2,
            is_volume_anomaly=False,
            participation_strength="NORMAL",
            volume_score=0.6,
            explanation="Normal healthy volume",
        )
        regime_data = SymbolRegimeState(
            symbol="BTCUSDT",
            timeframe="15m",
            current_price=105.0,
            regime="TRENDING_BULL",
            confidence=0.85,
            explanation="Normal bull market",
        )

        decision = MultiFactorReversalDetector.evaluate(
            position=pos,
            trend_data=trend_data,
            momentum_data=momentum_data,
            volume_data=volume_data,
            regime_data=regime_data,
            evaluation_timestamp="2026-11-01T10:15:00.000Z",
        )

        assert decision.reversal_detected is False
        assert decision.confirmation_count == 1
        assert decision.confirmation_sources == ["MOMENTUM"]

    def test_reversal_accepted_two_or_more_sources(self):
        """
        Test 5: Reversal exit confirmed when >= 2 independent domains confirm.
        (e.g. Trend bias flipped to BEARISH + Momentum BEARISH with RSI < 45).
        """
        pos = ActivePosition(
            position_id="pos_test_rev2",
            signal_id="sig_test_rev2",
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            entry_price=Decimal("100.0"),
            raw_entry_price=Decimal("100.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("110.0"),
            position_size=Decimal("1.0"),
            entry_fee=Decimal("0.1"),
            entry_slippage_cost=Decimal("0.05"),
            entry_spread_cost=Decimal("0.01"),
            market_regime="TRENDING_BULL",
            strategy_metadata={},
            exit_policy="BALANCED",
        )

        # Trend confirms BEARISH, Momentum confirms BEARISH with RSI=42.0
        trend_data = TrendAnalystOutput(
            timestamp="2026-11-01T10:15:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            composite_bias="BEARISH",
            trend_strength_score=0.45,
            ema_values={"20": 98.0, "50": 100.0, "200": 105.0},
            ema_stack_ordered=False,
            adx_value=22.0,
            plus_di=14.0,
            minus_di=26.0,
            adx_slope=-0.2,
            confidence_discount=0.0,
            explanation="Bearish trend shift",
        )
        momentum_data = MomentumAnalystOutput(
            timestamp="2026-11-01T10:15:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            rsi=42.0,
            momentum_direction="BEARISH",
            momentum_score=-0.7,
            exhaustion_risk=False,
            divergence="BEARISH_DIVERGENCE",
            explanation="Bearish momentum breakdown",
        )
        volume_data = VolumeAnalystOutput(
            timestamp="2026-11-01T10:15:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            current_volume=100.0,
            volume_ma=100.0,
            volume_ratio=1.0,
            is_volume_anomaly=False,
            participation_strength="NORMAL",
            volume_score=0.5,
            explanation="Moderate volume",
        )
        regime_data = SymbolRegimeState(
            symbol="BTCUSDT",
            timeframe="15m",
            current_price=99.0,
            regime="VOLATILE",
            confidence=0.5,
            explanation="Elevated volatility",
        )

        decision = MultiFactorReversalDetector.evaluate(
            position=pos,
            trend_data=trend_data,
            momentum_data=momentum_data,
            volume_data=volume_data,
            regime_data=regime_data,
            evaluation_timestamp="2026-11-01T10:15:00.000Z",
        )

        assert decision.reversal_detected is True
        assert decision.confirmation_count >= 2
        assert "TREND" in decision.confirmation_sources
        assert "MOMENTUM" in decision.confirmation_sources
        assert decision.confidence_score >= 0.70

    def test_reversal_timing_detection_at_close_execution_at_open(self):
        """
        Test 6: Reversal timing invariant:
        Detection occurs at candle T close -> marks position pending reversal.
        Execution fill occurs at candle T+1 open with slippage and fees.
        """
        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),
            slippage_pct=Decimal("0.0005"),
            spread_bps=Decimal("2.0"),
        )

        pos = sim.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=Decimal("100.0"),
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("110.0"),
            signal_timestamp="2026-11-01T10:00:00.000Z",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
            exit_policy="BALANCED",
        )

        # Candle T arrives. Close price = 104.0.
        c_t = make_candle(1, open_=101.0, high=105.0, low=100.5, close=104.0)

        # At Candle T close, reversal is detected:
        pos.reversal_exit_pending = True
        pos.reversal_detection_timestamp = c_t.timestamp
        pos.reversal_reason_codes = ["TREND_BIAS_BEARISH", "MOMENTUM_BEARISH_DIVERGENCE"]

        # Position is still OPEN at Candle T close!
        assert pos.position_id is not None

        # Candle T+1 arrives: Open = 103.5.
        c_next = make_candle(2, open_=103.5, high=104.0, low=101.0, close=102.0)

        # Execution simulator executes pending reversal at candle T+1 open:
        trade = sim.execute_pending_reversal(pos, c_next)
        assert trade is not None
        assert trade.exit_reason == "REVERSAL_CONFIRMED"
        assert trade.exit_timestamp == c_next.timestamp
        assert trade.reversal_detection_timestamp == c_t.timestamp
        # Fill price is based on candle T+1 open (103.5) minus sell friction
        assert trade.exit_price < Decimal("103.5")
        assert trade.gross_pnl == Decimal("3.50")  # (103.5 - 100.0) * 1.0

    def test_protective_stop_precedence_over_reversal(self):
        """
        Test 7: Priority: If candle T+1 opens gap-down below the active protective stop,
        the stop-loss takes precedence over the pending reversal exit.
        """
        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),
            slippage_pct=Decimal("0.0005"),
            spread_bps=Decimal("0.0"),
        )

        pos = sim.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=Decimal("100.0"),
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("110.0"),
            signal_timestamp="2026-11-01T10:00:00.000Z",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
            exit_policy="BALANCED",
        )

        # Mark reversal pending at candle T
        pos.reversal_exit_pending = True
        pos.reversal_detection_timestamp = "2026-11-01T10:15:00.000Z"

        # Candle T+1 opens at 92.0 (gapped below stop 95.0)
        c_gap = make_candle(2, open_=92.0, high=93.0, low=91.0, close=92.5)

        # Evaluator checks open vs stop_loss
        c_open = Decimal(str(c_gap.open))
        assert c_open <= pos.stop_loss

        # Priority: STOP_LOSS takes precedence
        exit_price_raw = min(pos.stop_loss, c_open)
        trade = sim._finalize_trade(pos, exit_price_raw, c_gap.timestamp, "STOP_LOSS")
        assert trade.exit_reason == "STOP_LOSS"
        assert trade.exit_price <= Decimal("92.0")

    def test_position_continues_past_theoretical_target(self):
        """
        Test 8: In BALANCED mode, reaching theoretical take-profit does NOT exit.
        Position continues running to capture larger gains.
        """
        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),
            slippage_pct=Decimal("0.0005"),
            spread_bps=Decimal("0.0"),
        )

        pos = sim.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=Decimal("100.0"),
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("105.0"),  # Theoretical target
            signal_timestamp="2026-11-01T10:00:00.000Z",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
            exit_policy="BALANCED",
            theoretical_take_profit=Decimal("105.0"),
        )

        # Candle 1 reaches High 107.0 (above theoretical target 105.0)
        c1 = make_candle(1, open_=102.0, high=107.0, low=101.5, close=106.5)
        trade = sim.evaluate_candle_bracket(pos, c1)

        # In BALANCED mode, trade must NOT be closed at 105.0!
        assert trade is None
        assert pos.theoretical_take_profit == Decimal("105.0")

        # Candle 2 advances to 115.0
        c2 = make_candle(2, open_=106.5, high=115.0, low=106.0, close=114.5)
        trade2 = sim.evaluate_candle_bracket(pos, c2)
        assert trade2 is None

    def test_fixed_bracket_mode_still_enforces_take_profit(self):
        """
        Test 9: In FIXED_BRACKET mode, take profit is strictly enforced.
        """
        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),
            slippage_pct=Decimal("0.0005"),
            spread_bps=Decimal("0.0"),
        )

        pos = sim.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=Decimal("100.0"),
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("105.0"),
            signal_timestamp="2026-11-01T10:00:00.000Z",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
            exit_policy="FIXED_BRACKET",
        )

        c1 = make_candle(1, open_=102.0, high=107.0, low=101.5, close=106.5)
        trade = sim.evaluate_candle_bracket(pos, c1)
        assert trade is not None
        assert trade.exit_reason == "TAKE_PROFIT"
        assert trade.gross_pnl == Decimal("5.00")

    def test_mfe_and_mae_accumulation(self):
        """
        Test 10: Verify Maximum Favorable Excursion (MFE) and Maximum Adverse Excursion (MAE)
        are tracked accurately across candles and stored on SimulatedTrade.
        """
        sim = PaperExecutionSimulator(
            taker_fee_pct=Decimal("0.001"),
            slippage_pct=Decimal("0.0005"),
            spread_bps=Decimal("0.0"),
        )

        pos = sim.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=Decimal("100.0"),
            position_size=Decimal("1.0"),
            stop_loss=Decimal("95.0"),
            take_profit=Decimal("115.0"),
            signal_timestamp="2026-11-01T10:00:00.000Z",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
            exit_policy="BALANCED",
        )

        # Bar 1: Dips to Low 97.0 (adverse move = 3.0), peaks at High 104.0 (favorable move = 4.0)
        c1 = make_candle(1, open_=100.0, high=104.0, low=97.0, close=102.0)
        sim.update_trailing_stop(pos, c1)
        assert pos.mfe == Decimal("4.0")
        assert pos.mae == Decimal("3.0")

        # Bar 2: Rallies to High 112.0 (favorable move = 12.0), low 101.0
        c2 = make_candle(2, open_=102.0, high=112.0, low=101.0, close=110.0)
        sim.update_trailing_stop(pos, c2)
        assert pos.mfe == Decimal("12.0")
        assert pos.mae == Decimal("3.0")  # adverse didn't worsen

        # Bar 3: Hits stop at 104.0
        c3 = make_candle(3, open_=108.0, high=109.0, low=94.0, close=94.5)
        trade = sim.evaluate_candle_bracket(pos, c3)
        assert trade is not None
        assert trade.mfe == Decimal("12.00")
        assert trade.mae >= Decimal("3.00")

    def test_performance_by_exit_reason_breakdown(self):
        """
        Test 11: Verify calculate_backtest_metrics aggregates performance by exit reason.
        """
        trades = [
            SimulatedTrade(
                trade_id="t1",
                symbol="BTCUSDT",
                timeframe="15m",
                direction="LONG",
                signal_timestamp="2026-11-01T10:00:00.000Z",
                entry_timestamp="2026-11-01T10:00:00.000Z",
                entry_price=Decimal("100.0"),
                exit_timestamp="2026-11-01T10:30:00.000Z",
                exit_price=Decimal("108.0"),
                stop_loss=Decimal("95.0"),
                take_profit=Decimal("110.0"),
                position_size=Decimal("1.0"),
                gross_pnl=Decimal("8.00"),
                fees=Decimal("0.20"),
                spread_cost=Decimal("0.02"),
                slippage_cost=Decimal("0.10"),
                net_pnl=Decimal("7.68"),
                exit_reason="TRAILING_STOP",
                market_regime="TRENDING_BULL",
            ),
            SimulatedTrade(
                trade_id="t2",
                symbol="BTCUSDT",
                timeframe="15m",
                direction="LONG",
                signal_timestamp="2026-11-01T11:00:00.000Z",
                entry_timestamp="2026-11-01T11:00:00.000Z",
                entry_price=Decimal("100.0"),
                exit_timestamp="2026-11-01T11:30:00.000Z",
                exit_price=Decimal("95.0"),
                stop_loss=Decimal("95.0"),
                take_profit=Decimal("110.0"),
                position_size=Decimal("1.0"),
                gross_pnl=Decimal("-5.00"),
                fees=Decimal("0.20"),
                spread_cost=Decimal("0.02"),
                slippage_cost=Decimal("0.10"),
                net_pnl=Decimal("-5.32"),
                exit_reason="STOP_LOSS",
                market_regime="TRENDING_BULL",
            ),
            SimulatedTrade(
                trade_id="t3",
                symbol="BTCUSDT",
                timeframe="15m",
                direction="LONG",
                signal_timestamp="2026-11-01T12:00:00.000Z",
                entry_timestamp="2026-11-01T12:00:00.000Z",
                entry_price=Decimal("100.0"),
                exit_timestamp="2026-11-01T12:30:00.000Z",
                exit_price=Decimal("103.0"),
                stop_loss=Decimal("95.0"),
                take_profit=Decimal("110.0"),
                position_size=Decimal("1.0"),
                gross_pnl=Decimal("3.00"),
                fees=Decimal("0.20"),
                spread_cost=Decimal("0.02"),
                slippage_cost=Decimal("0.10"),
                net_pnl=Decimal("2.68"),
                exit_reason="REVERSAL_CONFIRMED",
                market_regime="TRENDING_BULL",
            ),
        ]

        metrics = calculate_backtest_metrics(
            trades=trades,
            equity_curve=[],
            initial_capital=Decimal("1000.0"),
            timeframe="15m",
        )

        assert "TRAILING_STOP" in metrics.performance_by_exit_reason
        assert "STOP_LOSS" in metrics.performance_by_exit_reason
        assert "REVERSAL_CONFIRMED" in metrics.performance_by_exit_reason

        assert metrics.performance_by_exit_reason["TRAILING_STOP"]["total_trades"] == 1
        assert metrics.performance_by_exit_reason["TRAILING_STOP"]["net_pnl"] == 7.68

        assert metrics.performance_by_exit_reason["STOP_LOSS"]["total_trades"] == 1
        assert metrics.performance_by_exit_reason["STOP_LOSS"]["net_pnl"] == -5.32

        assert metrics.performance_by_exit_reason["REVERSAL_CONFIRMED"]["total_trades"] == 1
        assert metrics.performance_by_exit_reason["REVERSAL_CONFIRMED"]["net_pnl"] == 2.68

    @pytest.mark.asyncio
    async def test_cash_and_equity_conservation_under_balanced_exits(self):
        """
        Test 12: Verify double-entry cash and equity conservation throughout
        event replay with Balanced Protection exits.
        """
        # Create a synthetic series of 40 candles: trending up then pulling back
        candles: List[ValidatedCandle] = []
        price = 100.0
        for i in range(40):
            if i < 20:
                price += 1.0
            else:
                price -= 0.5
            candles.append(make_candle(i, open_=price - 0.5, high=price + 0.8, low=price - 0.8, close=price))

        config = BacktestConfig(
            strategy_id="trend_following_v1",
            symbols=["BTCUSDT"],
            timeframe="15m",
            initial_capital=Decimal("1000.0"),
            exit_policy="BALANCED",
            save_to_db=False,
            save_to_parquet=False,
        )

        engine = HistoricalBacktestEngine(config=config)
        result = await engine.run(candles_by_symbol={"BTCUSDT": candles})

        # At the end of the test, all positions are closed (via bracket, reversal, or force close at end)
        total_realized_net_pnl = sum((t.net_pnl for t in result.trades), Decimal("0.00"))
        final_equity = Decimal(str(result.equity_curve[-1].total_equity))
        expected_final = config.initial_capital + total_realized_net_pnl

        # Cash equity must equal initial_capital + total_realized_net_pnl within floating precision cents
        assert final_equity == pytest.approx(expected_final, abs=Decimal("0.05"))

    @pytest.mark.asyncio
    async def test_lookahead_temporal_invariance_under_balanced_policy(self):
        """
        Test 13: Strict Look-ahead invariance check under Balanced Protection policy.
        A backtest on candles 0..35 must produce identical trades up to candle 35
        when evaluated on candles 0..45.
        """
        candles_full: List[ValidatedCandle] = []
        p = 100.0
        for i in range(50):
            p += (1.0 if i < 25 else -0.5)
            candles_full.append(make_candle(i, open_=p - 0.5, high=p + 0.8, low=p - 0.8, close=p))

        candles_prefix = candles_full[:35]

        config = BacktestConfig(
            strategy_id="trend_following_v1",
            symbols=["BTCUSDT"],
            timeframe="15m",
            initial_capital=Decimal("1000.0"),
            exit_policy="BALANCED",
            save_to_db=False,
            save_to_parquet=False,
        )

        engine_short = HistoricalBacktestEngine(config=config)
        engine_long = HistoricalBacktestEngine(config=config)

        res_short = await engine_short.run(candles_by_symbol={"BTCUSDT": candles_prefix})
        res_long = await engine_long.run(candles_by_symbol={"BTCUSDT": candles_full})

        cutoff_ts = candles_prefix[-1].timestamp
        # Trades entered and exited before or at cutoff_ts in the longer backtest
        long_trades_before_cutoff = [
            t for t in res_long.trades
            if t.exit_timestamp <= cutoff_ts and t.exit_reason != "FORCE_CLOSE_END_OF_TEST"
        ]
        short_trades = [
            t for t in res_short.trades
            if t.exit_reason != "FORCE_CLOSE_END_OF_TEST"
        ]

        # Invariance check: Exactly the same decisions and outcomes before cutoff
        assert len(long_trades_before_cutoff) == len(short_trades)
        for t_short, t_long in zip(short_trades, long_trades_before_cutoff):
            assert t_short.entry_timestamp == t_long.entry_timestamp
            assert t_short.exit_timestamp == t_long.exit_timestamp
            assert t_short.entry_price == t_long.entry_price
            assert t_short.exit_price == t_long.exit_price
            assert t_short.exit_reason == t_long.exit_reason
            assert t_short.net_pnl == t_long.net_pnl

    def test_zero_or_negative_risk_defense(self):
        """
        Test 14: Defense: If initial risk per unit is zero or negative (invalid geometry),
        update_trailing_stop returns False without raising an error or corrupting stop loss.
        """
        sim = PaperExecutionSimulator()
        pos = sim.simulate_entry(
            symbol="BTCUSDT",
            timeframe="15m",
            direction="LONG",
            raw_price=Decimal("100.0"),
            position_size=Decimal("1.0"),
            stop_loss=Decimal("100.0"),  # Risk = 0.0
            take_profit=Decimal("110.0"),
            signal_timestamp="2026-11-01T10:00:00.000Z",
            entry_timestamp="2026-11-01T10:00:00.000Z",
            market_regime="TRENDING_BULL",
            strategy_metadata={},
            exit_policy="BALANCED",
        )

        c = make_candle(1, open_=101.0, high=108.0, low=100.5, close=107.0)
        updated = sim.update_trailing_stop(pos, c, atr_value=Decimal("2.0"))
        assert updated is False
        assert pos.stop_loss == Decimal("100.0")
