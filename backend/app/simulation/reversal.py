"""
NEPTUNE Multi-Factor Reversal Detection Module (`reversal.py`)

Evaluates analytical evidence across 4 independent specialist domains:
1. Trend Analyst: structural breakdown / bias flip.
2. Momentum Analyst: momentum exhaustion / divergence / counter-extreme.
3. Volume Analyst: volume climax anomaly or severe liquidity dry-up.
4. Market Scanner: regime transition to counter-trend or high uncertainty.

A reversal exit requires at least 2 sufficiently independent confirmations.
A single indicator or RSI threshold is strictly prohibited from triggering an exit alone.
All scores are heuristic confluence ratings, not empirical win probabilities (Rule S-06).
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.agents.market_scanner import SymbolRegimeState
from app.agents.momentum_analyst import MomentumAnalystOutput
from app.agents.trend_analyst import TrendAnalystOutput
from app.agents.volume_analyst import VolumeAnalystOutput
from app.simulation.models import ActivePosition


class ReversalDecision(BaseModel):
    """Structured decision returned by multi-factor reversal evaluation."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    reversal_detected: bool
    confirmation_count: int
    confirmation_sources: List[str] = Field(default_factory=list)
    reason_codes: List[str] = Field(default_factory=list)
    evaluation_timestamp: str
    confidence_score: float = 0.0
    explanation: str


class MultiFactorReversalDetector:
    """
    Detects potential trend reversals for active paper positions using
    confluence across Trend, Momentum, Volume, and Regime analytics.
    """

    MIN_CONFIRMATIONS_REQUIRED: int = 2

    @classmethod
    def evaluate(
        cls,
        position: ActivePosition,
        trend_data: TrendAnalystOutput,
        momentum_data: MomentumAnalystOutput,
        volume_data: VolumeAnalystOutput,
        regime_data: SymbolRegimeState,
        evaluation_timestamp: str,
    ) -> ReversalDecision:
        """
        Evaluate position against analytical evidence.
        Returns ReversalDecision requiring >= 2 independent confirmations.
        """
        direction = position.direction.upper()
        sources: List[str] = []
        reason_codes: List[str] = []
        explanation_parts: List[str] = []

        if direction == "LONG":
            # 1. Trend Domain: Bearish breakdown or clear bias shift
            trend_confirmed = False
            if trend_data.composite_bias == "BEARISH":
                trend_confirmed = True
                reason_codes.append("TREND_BIAS_BEARISH")
                explanation_parts.append("Trend analyst shifted to BEARISH bias.")
            elif not trend_data.ema_stack_ordered and trend_data.trend_strength_score < 0.35:
                trend_confirmed = True
                reason_codes.append("TREND_STRUCTURE_BREAKDOWN")
                explanation_parts.append(
                    f"Trend structure collapsed (strength={trend_data.trend_strength_score:.2f}, unordered EMAs)."
                )

            if trend_confirmed:
                sources.append("TREND")

            # 2. Momentum Domain: Bearish divergence, counter-momentum, or overbought exhaustion
            momentum_confirmed = False
            if momentum_data.momentum_direction == "BEARISH" and momentum_data.rsi < 45.0:
                momentum_confirmed = True
                reason_codes.append("MOMENTUM_BEARISH_DIVERGENCE")
                explanation_parts.append(
                    f"Momentum turned bearish with RSI={momentum_data.rsi:.1f} < 45.0."
                )
            elif momentum_data.rsi >= 75.0 and momentum_data.momentum_direction == "BEARISH":
                momentum_confirmed = True
                reason_codes.append("MOMENTUM_OVERBOUGHT_EXHAUSTION")
                explanation_parts.append(f"RSI overbought exhaustion ({momentum_data.rsi:.1f}) rolling over.")

            if momentum_confirmed:
                sources.append("MOMENTUM")

            # 3. Volume Domain: Volume climax exhaustion or dry-up
            volume_confirmed = False
            if volume_data.participation_strength == "CLIMACTIC" or (
                volume_data.is_volume_anomaly and volume_data.volume_ratio >= 2.5
            ):
                volume_confirmed = True
                reason_codes.append("VOLUME_CLIMAX_ANOMALY")
                explanation_parts.append(
                    f"Volume climax anomaly detected ({volume_data.volume_ratio:.2f}x average)."
                )
            elif volume_data.volume_score < 0.20 and volume_data.participation_strength == "WEAK":
                volume_confirmed = True
                reason_codes.append("VOLUME_PARTICIPATION_DRYUP")
                explanation_parts.append("Severe volume dry-up indicates trend exhaustion.")

            if volume_confirmed:
                sources.append("VOLUME")

            # 4. Regime Domain: Scanner regime flipped to bearish or high uncertainty
            regime_confirmed = False
            if regime_data.regime == "TRENDING_BEAR":
                regime_confirmed = True
                reason_codes.append("REGIME_BEARISH_TRANSITION")
                explanation_parts.append("Market regime transitioned to TRENDING_BEAR.")
            elif regime_data.regime in ("VOLATILE", "UNCERTAIN") and regime_data.confidence < 0.40:
                regime_confirmed = True
                reason_codes.append("REGIME_DETERIORATION")
                explanation_parts.append(f"Market regime deteriorated into {regime_data.regime}.")

            if regime_confirmed:
                sources.append("REGIME")

        else:  # SHORT
            # 1. Trend Domain: Bullish reversal or structure shift
            trend_confirmed = False
            if trend_data.composite_bias == "BULLISH":
                trend_confirmed = True
                reason_codes.append("TREND_BIAS_BULLISH")
                explanation_parts.append("Trend analyst shifted to BULLISH bias.")
            elif not trend_data.ema_stack_ordered and trend_data.trend_strength_score < 0.35:
                trend_confirmed = True
                reason_codes.append("TREND_STRUCTURE_BREAKDOWN")
                explanation_parts.append(
                    f"Bearish trend structure collapsed (strength={trend_data.trend_strength_score:.2f})."
                )

            if trend_confirmed:
                sources.append("TREND")

            # 2. Momentum Domain: Bullish momentum flip or oversold exhaustion
            momentum_confirmed = False
            if momentum_data.momentum_direction == "BULLISH" and momentum_data.rsi > 55.0:
                momentum_confirmed = True
                reason_codes.append("MOMENTUM_BULLISH_DIVERGENCE")
                explanation_parts.append(
                    f"Momentum turned bullish with RSI={momentum_data.rsi:.1f} > 55.0."
                )
            elif momentum_data.rsi <= 25.0 and momentum_data.momentum_direction == "BULLISH":
                momentum_confirmed = True
                reason_codes.append("MOMENTUM_OVERSOLD_EXHAUSTION")
                explanation_parts.append(f"RSI oversold exhaustion ({momentum_data.rsi:.1f}) rebounding.")

            if momentum_confirmed:
                sources.append("MOMENTUM")

            # 3. Volume Domain: Volume climax anomaly
            volume_confirmed = False
            if volume_data.participation_strength == "CLIMACTIC" or (
                volume_data.is_volume_anomaly and volume_data.volume_ratio >= 2.5
            ):
                volume_confirmed = True
                reason_codes.append("VOLUME_CLIMAX_ANOMALY")
                explanation_parts.append(
                    f"Volume climax anomaly detected ({volume_data.volume_ratio:.2f}x average)."
                )

            if volume_confirmed:
                sources.append("VOLUME")

            # 4. Regime Domain: Scanner regime flipped to bullish
            regime_confirmed = False
            if regime_data.regime == "TRENDING_BULL":
                regime_confirmed = True
                reason_codes.append("REGIME_BULLISH_TRANSITION")
                explanation_parts.append("Market regime transitioned to TRENDING_BULL.")

            if regime_confirmed:
                sources.append("REGIME")

        count = len(sources)
        reversal_detected = bool(count >= cls.MIN_CONFIRMATIONS_REQUIRED)

        # Heuristic confidence calculation (not empirical probability)
        confidence_score = round(min(1.0, 0.40 + (0.15 * count)), 2) if reversal_detected else 0.0
        explanation = (
            f"Reversal confirmed by {count} sources ({', '.join(sources)}): " + " ".join(explanation_parts)
            if reversal_detected
            else f"Reversal not confirmed (found {count}/{cls.MIN_CONFIRMATIONS_REQUIRED} sources: {', '.join(sources) or 'None'})."
        )

        return ReversalDecision(
            reversal_detected=reversal_detected,
            confirmation_count=count,
            confirmation_sources=sources,
            reason_codes=reason_codes,
            evaluation_timestamp=evaluation_timestamp,
            confidence_score=confidence_score,
            explanation=explanation,
        )
