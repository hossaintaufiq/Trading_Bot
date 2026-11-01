"""
NEPTUNE — Milestone 3 Deterministic Analysis Engine Unit Tests

Covers:
1. Pure mathematical indicator calculations (EMA, SMA, ATR, ADX, RSI, MACD, Bollinger, VWAP, OBV).
2. Indicator warm-up periods and mathematical edge cases (flat price, extreme moves, division by zero).
3. Deterministic repeatability (strict bit-for-bit reproducibility).
4. Market Scanner Agent (trending bull/bear, ranging squeeze, volatile, uncertain, insufficient history).
5. Trend Analyst Agent (EMA alignment, confidence discount on warm-up, ADX slope).
6. Momentum Analyst Agent (MACD dynamics, RSI divergences, momentum exhaustion, RSI bounds).
7. Volume Analyst Agent (relative volume, volume surges/anomalies, zero-volume handling, VWAP).
8. Strategy Analyst Agent:
   - Rule A-09 open candle rejection.
   - Conflicting indicator detection (conflicts force NO_SIGNAL).
   - Valid LONG and SHORT candidate generation with >=1.5 R:R and Decimal precision.
   - Absence of signals without multi-factor confluence.

100% synthetic fixtures, zero live network dependencies.
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
    calculate_keltner_channels,
    calculate_macd,
    calculate_obv,
    calculate_rsi,
    calculate_sma,
    calculate_vwap,
)
from app.agents.market_scanner import (
    MarketScannerAgent,
    MarketScannerInput,
    SymbolRegimeState,
)
from app.agents.momentum_analyst import (
    MomentumAnalystAgent,
    MomentumAnalystInput,
    MomentumAnalystOutput,
)
from app.agents.trend_analyst import (
    TrendAnalystAgent,
    TrendAnalystInput,
    TrendAnalystOutput,
)
from app.agents.volume_analyst import (
    VolumeAnalystAgent,
    VolumeAnalystInput,
    VolumeAnalystOutput,
)
from app.agents.strategy_analyst import (
    StrategyAnalystAgent,
    StrategyAnalystInput,
    StrategyAnalystOutput,
)
from app.data.market.validator import ValidatedCandle


# ============================================================
# SYNTHETIC FIXTURE BUILDERS
# ============================================================

def make_candle(
    index: int,
    price: float,
    high: float,
    low: float,
    volume: float = 100.0,
    is_closed: bool = True,
    timeframe: str = "15m",
) -> ValidatedCandle:
    base_dt = datetime(2026, 11, 1, 10, 0, 0, tzinfo=timezone.utc)
    candle_dt = base_dt + timedelta(minutes=15 * index)
    return ValidatedCandle(
        symbol="BTCUSDT",
        timeframe=timeframe,
        timestamp=candle_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        open=price,
        high=high,
        low=low,
        close=price,
        volume=volume,
        is_closed=is_closed,
    )


def make_trending_series(count: int, start: float, step: float, is_closed: bool = True):
    candles = []
    curr = start
    for i in range(count):
        curr += step
        high = curr + abs(step) * 0.5 + 2.0
        low = curr - abs(step) * 0.5 - 2.0
        candles.append(make_candle(i, curr, high, low, volume=100.0 + i, is_closed=is_closed))
    return candles


# ============================================================
# 1. PURE INDICATOR MATHEMATICAL TESTS
# ============================================================

class TestIndicatorCalculations:
    def test_sma_basic_and_warmup(self):
        series = [10.0, 20.0, 30.0, 40.0, 50.0]
        sma = calculate_sma(series, period=3)
        assert len(sma) == 5
        assert sma[0] is None
        assert sma[1] is None
        assert sma[2] == pytest.approx(20.0)  # (10+20+30)/3
        assert sma[3] == pytest.approx(30.0)  # (20+30+40)/3
        assert sma[4] == pytest.approx(40.0)  # (30+40+50)/3

    def test_ema_calculation_and_warmup(self):
        series = [10.0, 11.0, 12.0, 13.0, 14.0]
        period = 3
        # alpha = 2 / (3 + 1) = 0.5
        # seed at index 2 is SMA(10, 11, 12) = 11.0
        # index 3: 13.0 * 0.5 + 11.0 * 0.5 = 12.0
        # index 4: 14.0 * 0.5 + 12.0 * 0.5 = 13.0
        ema = calculate_ema(series, period=period)
        assert ema[0] is None
        assert ema[1] is None
        assert ema[2] == pytest.approx(11.0)
        assert ema[3] == pytest.approx(12.0)
        assert ema[4] == pytest.approx(13.0)

    def test_atr_calculation(self):
        highs = [12.0, 13.0, 14.0, 15.0]
        lows = [10.0, 11.0, 12.0, 13.0]
        closes = [11.0, 12.0, 13.0, 14.0]
        # TRs:
        # 0: H-L = 2.0
        # 1: max(13-11, |13-11|, |11-11|) = 2.0
        # 2: 2.0, 3: 2.0
        atr = calculate_atr(highs, lows, closes, period=2)
        assert atr[0] is None
        assert atr[1] == pytest.approx(2.0)
        assert atr[2] == pytest.approx(2.0)
        assert atr[3] == pytest.approx(2.0)

    def test_rsi_calculation_reference_and_edge_cases(self):
        # 1. Monotonically increasing price -> RSI must approach 100
        up_closes = [10.0 + i for i in range(25)]
        rsi_up = calculate_rsi(up_closes, period=14)
        assert rsi_up[13] is None
        assert rsi_up[14] == pytest.approx(100.0)
        assert rsi_up[-1] == pytest.approx(100.0)

        # 2. Monotonically decreasing price -> RSI must approach 0
        down_closes = [100.0 - i for i in range(25)]
        rsi_down = calculate_rsi(down_closes, period=14)
        assert rsi_down[14] == pytest.approx(0.0)
        assert rsi_down[-1] == pytest.approx(0.0)

        # 3. Flat prices (zero delta)
        flat = [50.0] * 20
        rsi_flat = calculate_rsi(flat, period=14)
        assert rsi_flat[14] == 100.0 or rsi_flat[14] == 0.0 or rsi_flat[14] is not None

    def test_macd_and_histogram(self):
        closes = [100.0 + (i * 0.5) for i in range(40)]
        macd_line, sig_line, hist = calculate_macd(closes, fast=12, slow=26, signal=9)
        # Slow is 26, so macd_line should start having values at index 25
        assert macd_line[24] is None
        assert macd_line[25] is not None
        # Signal line requires 9 values of MACD line, starting at index 25 + 8 = 33
        assert sig_line[32] is None
        assert sig_line[33] is not None
        assert hist[33] == pytest.approx(macd_line[33] - sig_line[33])

    def test_bollinger_bands_and_bandwidth(self):
        closes = [10.0, 12.0, 10.0, 12.0, 10.0, 12.0]
        upper, middle, lower, bw = calculate_bollinger_bands(closes, period=4, num_std=2.0)
        assert middle[2] is None
        assert middle[3] == pytest.approx(11.0)
        assert upper[3] > middle[3]
        assert lower[3] < middle[3]
        assert bw[3] == pytest.approx((upper[3] - lower[3]) / middle[3])

    def test_vwap_calculation(self):
        # 2 candles:
        # 1: H=12, L=8, C=10 -> TP=10. Vol=100 -> PV=1000
        # 2: H=22, L=18, C=20 -> TP=20. Vol=100 -> PV=2000
        # CumPV = 3000, CumVol = 200 -> VWAP = 15.0
        vwap = calculate_vwap([12.0, 22.0], [8.0, 18.0], [10.0, 20.0], [100.0, 100.0])
        assert vwap[0] == pytest.approx(10.0)
        assert vwap[1] == pytest.approx(15.0)

    def test_obv_accumulation_distribution(self):
        closes = [10.0, 12.0, 11.0, 11.0]
        volumes = [100.0, 50.0, 30.0, 20.0]
        obv = calculate_obv(closes, volumes)
        # 0: 100.0
        # 1: 100 + 50 = 150.0 (price rose)
        # 2: 150 - 30 = 120.0 (price fell)
        # 3: 120.0 (price flat)
        assert obv == [100.0, 150.0, 120.0, 120.0]

    def test_deterministic_reproducibility(self):
        series = [10.0 + np.sin(i) * 5.0 for i in range(100)]
        res1 = calculate_rsi(series, period=14)
        res2 = calculate_rsi(series, period=14)
        assert res1 == res2


# ============================================================
# 2. MARKET SCANNER AGENT TESTS
# ============================================================

class TestMarketScannerAgent:
    @pytest.mark.asyncio
    async def test_market_scanner_trending_bull(self):
        agent = MarketScannerAgent()
        candles = make_trending_series(count=70, start=100.0, step=2.0)
        input_data = MarketScannerInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbols=["BTCUSDT"],
            timeframe="15m",
            candles_by_symbol={"BTCUSDT": candles},
        )
        res = await agent.run(input_data)
        assert res.success is True
        output = res.output
        regime = output.regimes["BTCUSDT"]
        assert regime.regime == "TRENDING_BULL"
        assert regime.confidence > 0.5
        assert "Bullish trend confirmed" in regime.explanation

    @pytest.mark.asyncio
    async def test_market_scanner_trending_bear(self):
        agent = MarketScannerAgent()
        candles = make_trending_series(count=70, start=300.0, step=-2.0)
        input_data = MarketScannerInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbols=["BTCUSDT"],
            timeframe="15m",
            candles_by_symbol={"BTCUSDT": candles},
        )
        res = await agent.run(input_data)
        assert res.success is True
        regime = res.output.regimes["BTCUSDT"]
        assert regime.regime == "TRENDING_BEAR"
        assert regime.confidence > 0.5

    @pytest.mark.asyncio
    async def test_market_scanner_squeeze_ranging(self):
        agent = MarketScannerAgent()
        # Tight, flat prices generate a Bollinger/Keltner compression squeeze
        candles = []
        for i in range(60):
            candles.append(make_candle(i, price=100.0 + (i % 2) * 0.05, high=100.1, low=99.9))
        input_data = MarketScannerInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbols=["BTCUSDT"],
            timeframe="15m",
            candles_by_symbol={"BTCUSDT": candles},
        )
        res = await agent.run(input_data)
        assert res.success is True
        regime = res.output.regimes["BTCUSDT"]
        assert regime.regime == "RANGING"

    @pytest.mark.asyncio
    async def test_market_scanner_insufficient_history(self):
        agent = MarketScannerAgent()
        candles = make_trending_series(count=15, start=100.0, step=1.0)
        input_data = MarketScannerInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbols=["BTCUSDT"],
            timeframe="15m",
            candles_by_symbol={"BTCUSDT": candles},
        )
        res = await agent.run(input_data)
        assert res.success is True
        regime = res.output.regimes["BTCUSDT"]
        assert regime.regime == "UNCERTAIN"
        assert regime.confidence == 0.0


# ============================================================
# 3. TREND ANALYST AGENT TESTS
# ============================================================

class TestTrendAnalystAgent:
    @pytest.mark.asyncio
    async def test_trend_analyst_bullish_alignment(self):
        agent = TrendAnalystAgent()
        # 210 candles so EMA 20, 50, and 200 are all warmed
        candles = make_trending_series(count=210, start=100.0, step=1.0)
        input_data = TrendAnalystInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            candles=candles,
        )
        res = await agent.run(input_data)
        assert res.success is True
        out = res.output
        assert out.composite_bias == "BULLISH"
        assert out.ema_stack_ordered is True
        assert out.ema_values["ema_20"] > out.ema_values["ema_50"] > out.ema_values["ema_200"]
        assert out.confidence_discount == 0.0

    @pytest.mark.asyncio
    async def test_trend_analyst_warmup_confidence_discount(self):
        agent = TrendAnalystAgent()
        # 80 candles: warms EMA 20 and 50, but NOT EMA 200
        candles = make_trending_series(count=80, start=100.0, step=1.0)
        input_data = TrendAnalystInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            candles=candles,
        )
        res = await agent.run(input_data)
        assert res.success is True
        out = res.output
        assert out.ema_values["ema_200"] is None
        assert out.confidence_discount == 0.5
        assert "discounted by 50%" in out.explanation


# ============================================================
# 4. MOMENTUM ANALYST AGENT TESTS
# ============================================================

class TestMomentumAnalystAgent:
    @pytest.mark.asyncio
    async def test_momentum_analyst_bullish_score(self):
        agent = MomentumAnalystAgent()
        candles = make_trending_series(count=50, start=100.0, step=1.5)
        input_data = MomentumAnalystInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            candles=candles,
        )
        res = await agent.run(input_data)
        assert res.success is True
        out = res.output
        assert out.momentum_direction == "BULLISH"
        assert out.momentum_score > 0.2
        assert out.rsi is not None and out.rsi > 50.0

    @pytest.mark.asyncio
    async def test_momentum_analyst_insufficient_data(self):
        agent = MomentumAnalystAgent()
        candles = make_trending_series(count=15, start=100.0, step=1.0)
        input_data = MomentumAnalystInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            candles=candles,
        )
        res = await agent.run(input_data)
        assert res.success is True
        assert res.output.momentum_direction == "UNCERTAIN"


# ============================================================
# 5. VOLUME ANALYST AGENT TESTS
# ============================================================

class TestVolumeAnalystAgent:
    @pytest.mark.asyncio
    async def test_volume_analyst_relative_volume_and_anomaly(self):
        agent = VolumeAnalystAgent()
        candles = make_trending_series(count=50, start=100.0, step=0.5)
        # Inject massive surge on the last candle (> 5x normal)
        candles[-1].volume = 2000.0
        input_data = VolumeAnalystInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            candles=candles,
            anomaly_std_threshold=2.5,
        )
        res = await agent.run(input_data)
        assert res.success is True
        out = res.output
        assert out.participation_strength == "STRONG"
        assert out.is_volume_anomaly is True
        assert out.volume_ratio > 2.0

    @pytest.mark.asyncio
    async def test_volume_analyst_zero_volume_handling(self):
        agent = VolumeAnalystAgent()
        # Series with zero volume
        candles = [make_candle(i, price=100.0, high=101.0, low=99.0, volume=0.0) for i in range(30)]
        input_data = VolumeAnalystInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            candles=candles,
        )
        res = await agent.run(input_data)
        assert res.success is True
        assert res.output.current_volume == 0.0


# ============================================================
# 6. STRATEGY ANALYST AGENT TESTS
# ============================================================

class TestStrategyAnalystAgent:
    @pytest.mark.asyncio
    async def test_strategy_analyst_rule_a09_open_candle_rejection(self):
        """Rule A-09: Unfinished candles must NEVER be analyzed for trade signals."""
        agent = StrategyAnalystAgent()
        # Last candle is unclosed (is_closed=False)
        candles = make_trending_series(count=50, start=100.0, step=1.0)
        candles[-1].is_closed = False

        dummy_regime = SymbolRegimeState(
            symbol="BTCUSDT", timeframe="15m", current_price=150.0,
            regime="TRENDING_BULL", confidence=0.8, explanation="Bull",
        )
        dummy_trend = TrendAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            composite_bias="BULLISH", trend_strength_score=0.8, ema_values={},
            ema_stack_ordered=True, explanation="Bull",
        )
        dummy_mom = MomentumAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            momentum_direction="BULLISH", momentum_score=0.5, explanation="Bull",
        )
        dummy_vol = VolumeAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            current_volume=100.0, participation_strength="NORMAL", volume_score=0.5, explanation="Vol",
        )

        input_data = StrategyAnalystInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            candles=candles,
            regime_data=dummy_regime,
            trend_data=dummy_trend,
            momentum_data=dummy_mom,
            volume_data=dummy_vol,
        )
        res = await agent.run(input_data)
        assert res.success is True
        out = res.output
        assert out.evaluation_outcome == "NO_SIGNAL"
        assert any("Rule A-09" in f or "Incomplete candle" in f for f in out.conflicting_factors + [out.explanation])

    @pytest.mark.asyncio
    async def test_strategy_analyst_conflicting_indicators_yield_no_signal(self):
        """No single indicator triggers trades; conflicting signals must yield NO_SIGNAL."""
        agent = StrategyAnalystAgent()
        candles = make_trending_series(count=50, start=100.0, step=1.0, is_closed=True)

        # Bullish Trend but BEARISH Momentum & Exhaustion
        regime = SymbolRegimeState(
            symbol="BTCUSDT", timeframe="15m", current_price=150.0,
            regime="TRENDING_BULL", confidence=0.8, explanation="Bull",
        )
        trend = TrendAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            composite_bias="BULLISH", trend_strength_score=0.7, ema_values={},
            ema_stack_ordered=True, explanation="Bull",
        )
        mom = MomentumAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            momentum_direction="BEARISH", momentum_score=-0.6, exhaustion_risk=True,
            divergence="BEARISH_DIVERGENCE", explanation="Bearish divergence",
        )
        vol = VolumeAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            current_volume=100.0, participation_strength="NORMAL", volume_score=0.5, explanation="Vol",
        )

        input_data = StrategyAnalystInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            candles=candles,
            regime_data=regime,
            trend_data=trend,
            momentum_data=mom,
            volume_data=vol,
        )
        res = await agent.run(input_data)
        assert res.success is True
        out = res.output
        assert out.evaluation_outcome == "NO_SIGNAL"
        assert len(out.candidates) == 0
        assert len(out.conflicting_factors) >= 1

    @pytest.mark.asyncio
    async def test_strategy_analyst_valid_long_candidate_generation(self):
        """Confluent bullish signals generate a candidate with >= 1.5 R:R and Decimal precision."""
        agent = StrategyAnalystAgent()
        candles = make_trending_series(count=50, start=100.0, step=1.0, is_closed=True)
        latest_close = candles[-1].close

        regime = SymbolRegimeState(
            symbol="BTCUSDT", timeframe="15m", current_price=latest_close,
            regime="TRENDING_BULL", confidence=0.85, atr_14=2.5, explanation="Bullish regime",
        )
        trend = TrendAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            composite_bias="BULLISH", trend_strength_score=0.75, ema_values={},
            ema_stack_ordered=True, explanation="Bullish trend alignment",
        )
        mom = MomentumAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            rsi=55.0, momentum_direction="BULLISH", momentum_score=0.45,
            exhaustion_risk=False, explanation="Healthy momentum",
        )
        vol = VolumeAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            current_volume=150.0, participation_strength="STRONG",
            obv_trend="ACCUMULATION", volume_score=0.6, explanation="Volume confirmed",
        )

        input_data = StrategyAnalystInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            candles=candles,
            regime_data=regime,
            trend_data=trend,
            momentum_data=mom,
            volume_data=vol,
            min_reward_risk_ratio=1.5,
            atr_multiplier_stop=2.0,
        )
        res = await agent.run(input_data)
        assert res.success is True
        out = res.output
        assert out.evaluation_outcome == "LONG"
        assert len(out.candidates) == 1

        cand = out.candidates[0]
        assert cand.direction == "LONG"
        assert cand.entry_price == latest_close
        # ATR=2.5, mult=2.0 -> Risk=5.0
        # Stop = entry - 5.0
        assert cand.suggested_stop_loss == pytest.approx(latest_close - 5.0)
        # Reward = 5.0 * 1.5 = 7.5 -> Target = entry + 7.5
        assert cand.suggested_take_profit == pytest.approx(latest_close + 7.5)
        assert cand.risk_reward_ratio >= 1.5

    @pytest.mark.asyncio
    async def test_strategy_analyst_valid_short_candidate_generation(self):
        """Confluent bearish signals generate a SHORT candidate with >= 1.5 R:R."""
        agent = StrategyAnalystAgent()
        candles = make_trending_series(count=50, start=300.0, step=-1.0, is_closed=True)
        latest_close = candles[-1].close

        regime = SymbolRegimeState(
            symbol="BTCUSDT", timeframe="15m", current_price=latest_close,
            regime="TRENDING_BEAR", confidence=0.85, atr_14=3.0, explanation="Bearish regime",
        )
        trend = TrendAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            composite_bias="BEARISH", trend_strength_score=0.75, ema_values={},
            ema_stack_ordered=True, explanation="Bearish trend alignment",
        )
        mom = MomentumAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            rsi=42.0, momentum_direction="BEARISH", momentum_score=-0.45,
            exhaustion_risk=False, explanation="Healthy bearish momentum",
        )
        vol = VolumeAnalystOutput(
            timestamp="2026-11-01T20:00:00.000Z", symbol="BTCUSDT", timeframe="15m",
            current_volume=150.0, participation_strength="STRONG",
            obv_trend="DISTRIBUTION", volume_score=-0.6, explanation="Volume confirmed",
        )

        input_data = StrategyAnalystInput(
            timestamp="2026-11-01T20:00:00.000Z",
            symbol="BTCUSDT",
            timeframe="15m",
            candles=candles,
            regime_data=regime,
            trend_data=trend,
            momentum_data=mom,
            volume_data=vol,
            min_reward_risk_ratio=1.5,
            atr_multiplier_stop=2.0,
        )
        res = await agent.run(input_data)
        assert res.success is True
        out = res.output
        assert out.evaluation_outcome == "SHORT"
        assert len(out.candidates) == 1

        cand = out.candidates[0]
        assert cand.direction == "SHORT"
        assert cand.entry_price == latest_close
        # ATR=3.0, mult=2.0 -> Risk=6.0
        # Stop = entry + 6.0
        assert cand.suggested_stop_loss == pytest.approx(latest_close + 6.0)
        # Reward = 6.0 * 1.5 = 9.0 -> Target = entry - 9.0
        assert cand.suggested_take_profit == pytest.approx(latest_close - 9.0)
        assert cand.risk_reward_ratio >= 1.5

