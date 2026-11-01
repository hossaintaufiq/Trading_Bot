"""
NEPTUNE Base Strategy Evaluator Agent (`strategy_analyst`)

Synthesizes outputs from Market Scanner, Trend, Momentum, and Volume analysts:
- Consumes closed, validated candles only (Rule A-09).
- Evaluates multi-factor confluence across all analytical domains.
- Detects conflicting indicators and defaults cleanly to NO_SIGNAL.
- Calculates monetary levels using Python Decimal (Rule A-01).
- Generates raw candidate research signals (never executes orders; Rule S-01, S-04).
"""
import uuid
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.agents.market_scanner import SymbolRegimeState
from app.agents.momentum_analyst import MomentumAnalystOutput
from app.agents.trend_analyst import TrendAnalystOutput
from app.agents.volume_analyst import VolumeAnalystOutput
from app.data.market.validator import ValidatedCandle


class RawCandidateSignal(BaseModel):
    signal_id: str                                    # Unique UUID
    timestamp: str                                    # ISO 8601 UTC
    strategy_id: str
    symbol: str
    timeframe: str
    direction: str                                    # LONG or SHORT
    entry_price: float
    suggested_stop_loss: float
    suggested_take_profit: float
    risk_reward_ratio: float = Field(ge=1.5)          # Minimum 1.5:1
    raw_confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    invalidation_rules: List[str] = []
    metadata: Dict[str, Any] = {}


class StrategyAnalystInput(BaseModel):
    timestamp: str                                    # ISO 8601 UTC
    symbol: str
    timeframe: str = "15m"
    candles: List[ValidatedCandle]
    regime_data: SymbolRegimeState
    trend_data: TrendAnalystOutput
    momentum_data: MomentumAnalystOutput
    volume_data: VolumeAnalystOutput
    active_strategies: Optional[List[str]] = None
    min_reward_risk_ratio: float = 1.5
    atr_multiplier_stop: float = 2.0


class StrategyAnalystOutput(BaseModel):
    timestamp: str
    symbol: str
    timeframe: str
    evaluation_outcome: str                          # LONG, SHORT, NO_SIGNAL
    candidates: List[RawCandidateSignal] = []
    conflicting_factors: List[str] = []
    explanation: str


class StrategyAnalystAgent(BaseAgent[StrategyAnalystInput, StrategyAnalystOutput]):
    """Specialist agent synthesizing perception inputs into raw hypothesis candidates."""

    agent_id: str = "strategy_analyst"
    agent_name: str = "Strategy Analyst"

    async def execute(self, input_data: StrategyAnalystInput) -> StrategyAnalystOutput:
        candles = input_data.candles
        if not candles:
            return StrategyAnalystOutput(
                timestamp=input_data.timestamp,
                symbol=input_data.symbol,
                timeframe=input_data.timeframe,
                evaluation_outcome="NO_SIGNAL",
                explanation="No candles provided for strategy evaluation.",
            )

        # Rule A-09: Analysis must ONLY evaluate closed candles
        latest_candle = candles[-1]
        if not latest_candle.is_closed:
            return StrategyAnalystOutput(
                timestamp=input_data.timestamp,
                symbol=input_data.symbol,
                timeframe=input_data.timeframe,
                evaluation_outcome="NO_SIGNAL",
                conflicting_factors=["Incomplete candle detected"],
                explanation="Rule A-09 violation rejected: Latest candle is not closed.",
            )

        regime = input_data.regime_data
        trend = input_data.trend_data
        momentum = input_data.momentum_data
        volume = input_data.volume_data

        conflicts: List[str] = []

        # 1. Inspect Regime Barriers
        if regime.regime == "VOLATILE":
            conflicts.append("Market regime is VOLATILE: Elevated volatility / expansion hazard.")
        elif regime.regime == "UNCERTAIN":
            conflicts.append("Market regime is UNCERTAIN: Ambiguous baseline structure.")

        # 2. Inspect Trend vs. Momentum Conflicts
        if trend.composite_bias == "BULLISH" and momentum.momentum_direction == "BEARISH":
            conflicts.append("Trend/Momentum conflict: Trend is BULLISH but Momentum is BEARISH.")
        elif trend.composite_bias == "BEARISH" and momentum.momentum_direction == "BULLISH":
            conflicts.append("Trend/Momentum conflict: Trend is BEARISH but Momentum is BULLISH.")

        # 3. Inspect Exhaustion and Divergences
        if trend.composite_bias == "BULLISH" and momentum.exhaustion_risk:
            conflicts.append(f"Momentum exhaustion warning: {momentum.explanation}")
        elif trend.composite_bias == "BEARISH" and momentum.exhaustion_risk:
            conflicts.append(f"Momentum exhaustion warning: {momentum.explanation}")

        # 4. Inspect Volume Divergence
        if trend.composite_bias == "BULLISH" and volume.obv_trend == "DISTRIBUTION":
            conflicts.append("Volume anomaly: Bullish price action accompanied by institutional distribution.")
        elif trend.composite_bias == "BEARISH" and volume.obv_trend == "ACCUMULATION":
            conflicts.append("Volume anomaly: Bearish price action accompanied by institutional accumulation.")

        # If any major conflicting indicators exist, strictly emit NO_SIGNAL
        if conflicts:
            return StrategyAnalystOutput(
                timestamp=input_data.timestamp,
                symbol=input_data.symbol,
                timeframe=input_data.timeframe,
                evaluation_outcome="NO_SIGNAL",
                candidates=[],
                conflicting_factors=conflicts,
                explanation=f"NO_SIGNAL: Evaluation inhibited by {len(conflicts)} conflicting factors.",
            )

        # 5. Check Confluence for LONG Setup
        # Requires:
        # - Regime: TRENDING_BULL
        # - Trend: BULLISH (strength >= 0.40)
        # - Momentum: BULLISH or neutral-positive (score >= 0.15), RSI between 40 and 68
        # - Volume: NORMAL or STRONG participation, not distributing
        is_long_setup = (
            regime.regime == "TRENDING_BULL"
            and trend.composite_bias == "BULLISH"
            and trend.trend_strength_score >= 0.40
            and momentum.momentum_score >= 0.15
            and (momentum.rsi is None or (40.0 <= momentum.rsi <= 68.0))
            and not momentum.exhaustion_risk
            and volume.participation_strength in ("STRONG", "NORMAL")
            and volume.obv_trend != "DISTRIBUTION"
        )

        # 6. Check Confluence for SHORT Setup
        # Requires:
        # - Regime: TRENDING_BEAR
        # - Trend: BEARISH (strength >= 0.40)
        # - Momentum: BEARISH (score <= -0.15), RSI between 32 and 60
        # - Volume: NORMAL or STRONG participation, not accumulating
        is_short_setup = (
            regime.regime == "TRENDING_BEAR"
            and trend.composite_bias == "BEARISH"
            and trend.trend_strength_score >= 0.40
            and momentum.momentum_score <= -0.15
            and (momentum.rsi is None or (32.0 <= momentum.rsi <= 60.0))
            and not momentum.exhaustion_risk
            and volume.participation_strength in ("STRONG", "NORMAL")
            and volume.obv_trend != "ACCUMULATION"
        )

        candidates: List[RawCandidateSignal] = []
        outcome = "NO_SIGNAL"
        explanation = "NO_SIGNAL: No setup achieved complete multi-factor confluence."

        if is_long_setup or is_short_setup:
            direction = "LONG" if is_long_setup else "SHORT"
            outcome = direction

            # Calculate Monetary Levels using Decimal (Rule A-01)
            entry_dec = Decimal(str(latest_candle.close))
            raw_atr = regime.atr_14 or (latest_candle.close * 0.015)
            atr_dec = Decimal(str(round(raw_atr, 4)))
            risk_mult_dec = Decimal(str(input_data.atr_multiplier_stop))
            risk_amount = (atr_dec * risk_mult_dec).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
            rr_dec = Decimal(str(input_data.min_reward_risk_ratio))
            reward_amount = (risk_amount * rr_dec).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

            if direction == "LONG":
                stop_dec = entry_dec - risk_amount
                target_dec = entry_dec + reward_amount
            else:
                stop_dec = entry_dec + risk_amount
                target_dec = entry_dec - reward_amount

            # Confidence weighting
            combined_conf = float(
                (trend.trend_strength_score * 0.4)
                + (regime.confidence * 0.3)
                + (abs(momentum.momentum_score) * 0.3)
            )

            rationale = (
                f"{direction} setup identified with multi-factor confluence: "
                f"Regime={regime.regime} (conf: {regime.confidence:.2f}), "
                f"Trend={trend.composite_bias} (strength: {trend.trend_strength_score:.2f}), "
                f"Momentum score={momentum.momentum_score:+.2f}, "
                f"Volume participation={volume.participation_strength}."
            )

            invalidation_rules = [
                f"Price violates stop loss level at {float(stop_dec)}.",
                "Opposing regime shift or volatility surge occurs before fill.",
                "Momentum divergence appears on higher timeframe.",
            ]

            candidate = RawCandidateSignal(
                signal_id=str(uuid.uuid4()),
                timestamp=input_data.timestamp,
                strategy_id="trend_continuation_v1",
                symbol=input_data.symbol,
                timeframe=input_data.timeframe,
                direction=direction,
                entry_price=float(entry_dec),
                suggested_stop_loss=float(stop_dec),
                suggested_take_profit=float(target_dec),
                risk_reward_ratio=float(rr_dec),
                raw_confidence=round(combined_conf, 3),
                rationale=rationale,
                invalidation_rules=invalidation_rules,
                metadata={
                    "atr_used": float(atr_dec),
                    "risk_amount": float(risk_amount),
                    "reward_amount": float(reward_amount),
                },
            )
            candidates.append(candidate)
            explanation = f"Generated 1 raw {direction} candidate signal pending validation and risk authorization."

        return StrategyAnalystOutput(
            timestamp=input_data.timestamp,
            symbol=input_data.symbol,
            timeframe=input_data.timeframe,
            evaluation_outcome=outcome,
            candidates=candidates,
            conflicting_factors=conflicts,
            explanation=explanation,
        )
