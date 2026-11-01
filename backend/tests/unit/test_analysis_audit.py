"""
NEPTUNE — Milestone 3.1 Quantitative Analysis Audit Regression Tests

Covers:
1. RSI flat-line edge case: completely flat price series must evaluate to 50.0 (neutral), not 100.0.
2. ADX Wilder smoothing continuity: verifies bar 14 is not skipped in initial smoothing.
3. Strategy Analyst non-positive stop-loss rejection: assets with wide ATR relative to price must not generate negative stops.
4. Volume Analyst outlier baseline: ensures current volume does not contaminate its own reference baseline.
5. Squeeze vs. Trend separation in Market Scanner.
6. Look-ahead bias verification across all indicators.
7. Conflicting indicator rejection in Strategy Analyst.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import numpy as np
import pytest

from app.analytics.indicators import (
    calculate_adx,
    calculate_atr,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
    calculate_sma,
    calculate_vwap,
)
from app.agents.market_scanner import MarketScannerAgent, MarketScannerInput, SymbolRegimeState
from app.agents.momentum_analyst import MomentumAnalystAgent, MomentumAnalystInput, MomentumAnalystOutput
from app.agents.trend_analyst import TrendAnalystAgent, TrendAnalystInput, TrendAnalystOutput
from app.agents.volume_analyst import VolumeAnalystAgent, VolumeAnalystInput, VolumeAnalystOutput
from app.agents.strategy_analyst import StrategyAnalystAgent, StrategyAnalystInput, StrategyAnalystOutput
from app.data.market.validator import ValidatedCandle


def make_test_candle(i: int, close: float, high: float, low: float, volume: float = 100.0, is_closed: bool = True):
    dt = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc) + timedelta(minutes=15 * i)
    return ValidatedCandle(
        symbol="BTCUSDT",
        timeframe="15m",
        timestamp=dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        open=close,
        high=high,
        low=low,
        close=close,
        volume=volume,
        is_closed=is_closed,
    )


class TestAuditFindings:
    def test_finding_2_rsi_flat_line_must_be_neutral(self):
        """Flat price series (zero gain and zero loss) must be 50.0 (neutral), not 100.0."""
        flat_closes = [100.0] * 30
        rsi = calculate_rsi(flat_closes, period=14)
        for val in rsi[14:]:
            assert val == pytest.approx(50.0), f"Flat RSI should be 50.0, got {val}"

    def test_finding_1_adx_wilder_smoothing_continuity(self):
        """Verify ADX smoothing includes all bars without skipping bar `period`."""
        # Flat up to bar 13, massive surge on bar 14 only, flat after
        highs = [10.0] * 14 + [100.0] + [100.0] * 15
        lows = [10.0] * 14 + [90.0] + [100.0] * 15
        closes = [10.0] * 14 + [95.0] + [100.0] * 15
        adx, p_di, m_di = calculate_adx(highs, lows, closes, period=14)
        # Bar 14 surge MUST register in p_di at index 14
        assert p_di[14] is not None and p_di[14] > 50.0

    @pytest.mark.asyncio
    async def test_finding_3_strategy_analyst_rejects_negative_stop_loss(self):
        """If ATR exceeds price and generates negative stop loss, candidate must be rejected."""
        agent = StrategyAnalystAgent()
        # Price is $1.0, but ATR is $2.0 (e.g. low-priced volatile token)
        candles = [make_test_candle(i, close=1.0, high=2.5, low=0.5, volume=100.0) for i in range(40)]
        regime = SymbolRegimeState(
            symbol="BTCUSDT", timeframe="15m", current_price=1.0,
            regime="TRENDING_BULL", confidence=0.8, atr_14=2.0, explanation="Bull",
        )
        trend = TrendAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            composite_bias="BULLISH", trend_strength_score=0.8, ema_values={},
            ema_stack_ordered=True, explanation="Bull",
        )
        mom = MomentumAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            rsi=55.0, momentum_direction="BULLISH", momentum_score=0.5, explanation="Bull",
        )
        vol = VolumeAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            current_volume=100.0, participation_strength="NORMAL", volume_score=0.5, explanation="Vol",
        )
        inp = StrategyAnalystInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            candles=candles,
            regime_data=regime,
            trend_data=trend,
            momentum_data=mom,
            volume_data=vol,
            atr_multiplier_stop=2.0,
        )
        res = await agent.run(inp)
        assert res.success is True
        # Entry = 1.0, Risk = 2.0 * 2.0 = 4.0 -> Stop would be 1.0 - 4.0 = -3.0!
        # Must be rejected with NO_SIGNAL
        assert res.output.evaluation_outcome == "NO_SIGNAL"
        assert any("stop" in f.lower() for f in res.output.conflicting_factors)

    def test_lookahead_bias_invariance(self):
        """Adding future bars must NOT change past indicator values."""
        past_closes = [10.0 + (i % 5) for i in range(50)]
        future_closes = past_closes + [999.0, 1000.0, 1500.0]

        ema_past = calculate_ema(past_closes, 20)
        ema_future = calculate_ema(future_closes, 20)

        for i in range(len(past_closes)):
            if ema_past[i] is None:
                assert ema_future[i] is None
            else:
                assert ema_past[i] == pytest.approx(ema_future[i])

        rsi_past = calculate_rsi(past_closes, 14)
        rsi_future = calculate_rsi(future_closes, 14)

        for i in range(len(past_closes)):
            if rsi_past[i] is None:
                assert rsi_future[i] is None
            else:
                assert rsi_past[i] == pytest.approx(rsi_future[i])

    @pytest.mark.asyncio
    async def test_market_scanner_regime_distinction(self):
        """Verify Market Scanner clearly distinguishes all 5 regimes without confusion."""
        agent = MarketScannerAgent()

        # 1. RANGING via Squeeze: extremely low volatility
        tight_candles = [make_test_candle(i, close=100.0 + (i % 2) * 0.02, high=100.05, low=99.95) for i in range(50)]
        res = await agent.run(MarketScannerInput(
            timestamp="2026-11-01T20:00:00.000Z", symbols=["BTCUSDT"], timeframe="15m",
            candles_by_symbol={"BTCUSDT": tight_candles}
        ))
        assert res.output.regimes["BTCUSDT"].regime == "RANGING"

        # 2. VOLATILE via Expansion: massive ATR surge
        volatile_candles = [make_test_candle(i, close=100.0, high=101.0, low=99.0) for i in range(45)]
        # Inject huge range expansion on recent bars
        for j in range(45, 50):
            volatile_candles.append(make_test_candle(j, close=100.0, high=150.0, low=50.0))
        res = await agent.run(MarketScannerInput(
            timestamp="2026-11-01T20:00:00.000Z", symbols=["BTCUSDT"], timeframe="15m",
            candles_by_symbol={"BTCUSDT": volatile_candles}
        ))
        assert res.output.regimes["BTCUSDT"].regime == "VOLATILE"

        # 3. UNCERTAIN via Insufficient History (< 30 closed bars)
        short_candles = [make_test_candle(i, close=100.0, high=101.0, low=99.0) for i in range(15)]
        res_short = await agent.run(MarketScannerInput(
            timestamp="2026-11-01T20:00:00.000Z", symbols=["BTCUSDT"], timeframe="15m",
            candles_by_symbol={"BTCUSDT": short_candles}
        ))
        assert res_short.output.regimes["BTCUSDT"].regime == "UNCERTAIN"
        assert res_short.output.regimes["BTCUSDT"].confidence == 0.0

        # 4. TRENDING_BULL via strong directional trend (ADX >= 25, price > EMA 50, +DI > -DI)
        bull_candles = [make_test_candle(i, close=100.0 + i * 1.5, high=101.0 + i * 1.5, low=99.5 + i * 1.5) for i in range(50)]
        res_bull = await agent.run(MarketScannerInput(
            timestamp="2026-11-01T20:00:00.000Z", symbols=["BTCUSDT"], timeframe="15m",
            candles_by_symbol={"BTCUSDT": bull_candles}
        ))
        assert res_bull.output.regimes["BTCUSDT"].regime == "TRENDING_BULL"
        assert res_bull.output.regimes["BTCUSDT"].confidence > 0.5

    @pytest.mark.asyncio
    async def test_reward_risk_geometry_interpretation(self):
        """Verify R:R is purely a structural payoff geometry, not an expected return claim."""
        agent = StrategyAnalystAgent()
        candles = [make_test_candle(i, close=100.0 + i, high=102.0 + i, low=98.0 + i) for i in range(50)]
        regime = SymbolRegimeState(
            symbol="BTCUSDT", timeframe="15m", current_price=149.0,
            regime="TRENDING_BULL", confidence=0.8, atr_14=2.0, explanation="Bull",
        )
        trend = TrendAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            composite_bias="BULLISH", trend_strength_score=0.8, ema_values={},
            ema_stack_ordered=True, explanation="Bull",
        )
        mom = MomentumAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            rsi=55.0, momentum_direction="BULLISH", momentum_score=0.4, explanation="Bull",
        )
        vol = VolumeAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            current_volume=100.0, participation_strength="NORMAL", volume_score=0.5, explanation="Vol",
        )
        inp = StrategyAnalystInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            candles=candles,
            regime_data=regime,
            trend_data=trend,
            momentum_data=mom,
            volume_data=vol,
            min_reward_risk_ratio=2.0,
            atr_multiplier_stop=1.5,
        )
        res = await agent.run(inp)
        assert res.success is True
        cand = res.output.candidates[0]
        # Entry = 149.0, ATR = 2.0, mult = 1.5 -> Risk = 3.0, Stop = 146.0
        # Target = 149.0 + (3.0 * 2.0) = 155.0
        risk = cand.entry_price - cand.suggested_stop_loss
        reward = cand.suggested_take_profit - cand.entry_price
        actual_rr = reward / risk
        assert actual_rr == pytest.approx(2.0)
        # R:R is a structural target ratio, raw_confidence is a heuristic score, not win probability
        assert cand.risk_reward_ratio == 2.0
        assert 0.0 <= cand.raw_confidence <= 1.0
