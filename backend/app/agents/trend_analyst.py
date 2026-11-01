"""
NEPTUNE Trend Analyst Agent (`trend_analyst`)

Performs multi-timeframe directional bias and trend stability analysis:
- EMA 20, 50, 200 stacks and order alignment
- ADX strength, +DI / -DI directional movement
- Distance from EMA 200 and ADX slope over recent bars
- Warm-up tracking: flags confidence discounts when <200 candles are present.
"""
from typing import Dict, List, Optional
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.analytics.indicators import calculate_adx, calculate_ema
from app.data.market.validator import ValidatedCandle


class TrendAnalystInput(BaseModel):
    timestamp: str                                    # ISO 8601 UTC
    symbol: str
    timeframe: str = "15m"
    candles: List[ValidatedCandle]
    ema_lengths: List[int] = [20, 50, 200]
    adx_period: int = 14


class TrendAnalystOutput(BaseModel):
    timestamp: str
    symbol: str
    timeframe: str
    composite_bias: str                               # BULLISH, BEARISH, NEUTRAL, UNCERTAIN
    trend_strength_score: float = Field(ge=0.0, le=1.0)
    ema_values: Dict[str, Optional[float]]
    ema_stack_ordered: bool                           # True if 20 > 50 > 200 (bull) or 20 < 50 < 200 (bear)
    adx_value: Optional[float] = None
    plus_di: Optional[float] = None
    minus_di: Optional[float] = None
    adx_slope: float = 0.0                            # Change in ADX over last 3 bars
    distance_from_200_ema_pct: Optional[float] = None
    confidence_discount: float = 0.0                  # e.g. 0.5 if EMA 200 is un-warmed
    explanation: str


class TrendAnalystAgent(BaseAgent[TrendAnalystInput, TrendAnalystOutput]):
    """Specialist agent for trend bias, EMA stack alignment, and trend strength."""

    agent_id: str = "trend_analyst"
    agent_name: str = "Trend Analyst"

    async def execute(self, input_data: TrendAnalystInput) -> TrendAnalystOutput:
        closed = [c for c in input_data.candles if c.is_closed]
        n = len(closed)

        if n < 20:
            return TrendAnalystOutput(
                timestamp=input_data.timestamp,
                symbol=input_data.symbol,
                timeframe=input_data.timeframe,
                composite_bias="UNCERTAIN",
                trend_strength_score=0.0,
                ema_values={"ema_20": None, "ema_50": None, "ema_200": None},
                ema_stack_ordered=False,
                confidence_discount=1.0,
                explanation=f"Insufficient candles ({n}/20 min) for trend evaluation.",
            )

        closes = [c.close for c in closed]
        highs = [c.high for c in closed]
        lows = [c.low for c in closed]
        curr_price = closes[-1]

        # Calculate EMAs
        ema_20 = calculate_ema(closes, 20)[-1]
        ema_50 = calculate_ema(closes, 50)[-1] if n >= 50 else None
        ema_200 = calculate_ema(closes, 200)[-1] if n >= 200 else None

        ema_dict = {
            "ema_20": round(ema_20, 4) if ema_20 else None,
            "ema_50": round(ema_50, 4) if ema_50 else None,
            "ema_200": round(ema_200, 4) if ema_200 else None,
        }

        # Calculate ADX, +DI, -DI
        adx_vals, plus_di_vals, minus_di_vals = calculate_adx(highs, lows, closes, period=input_data.adx_period)
        curr_adx = adx_vals[-1]
        curr_p_di = plus_di_vals[-1]
        curr_m_di = minus_di_vals[-1]

        # ADX slope over last 3 valid bars
        valid_adxs = [a for a in adx_vals if a is not None]
        adx_slope = 0.0
        if len(valid_adxs) >= 4:
            adx_slope = round(valid_adxs[-1] - valid_adxs[-4], 3)

        # Distance from 200 EMA
        dist_200_pct = None
        if ema_200 and ema_200 > 0:
            dist_200_pct = round(((curr_price - ema_200) / ema_200) * 100.0, 3)

        # Evaluate EMA stack order
        ema_stack_ordered = False
        bullish_stack = False
        bearish_stack = False

        if ema_20 and ema_50 and ema_200:
            if ema_20 > ema_50 > ema_200:
                ema_stack_ordered = True
                bullish_stack = True
            elif ema_20 < ema_50 < ema_200:
                ema_stack_ordered = True
                bearish_stack = True
        elif ema_20 and ema_50:
            # Partial stack when <200 bars
            bullish_stack = bool(ema_20 > ema_50 and curr_price > ema_50)
            bearish_stack = bool(ema_20 < ema_50 and curr_price < ema_50)

        # Confidence discount when history is incomplete
        confidence_discount = 0.0
        if n < 200:
            confidence_discount = 0.5

        # Composite bias and strength score
        bias = "NEUTRAL"
        strength = 0.0
        explanation_parts = []

        if bullish_stack and curr_price > (ema_20 or curr_price):
            p_di = curr_p_di or 0.0
            m_di = curr_m_di or 0.0
            if p_di >= m_di:
                bias = "BULLISH"
                adx_contrib = min(0.5, (curr_adx or 20.0) / 60.0)
                stack_contrib = 0.5 if ema_stack_ordered else 0.3
                strength = min(1.0, stack_contrib + adx_contrib)
                explanation_parts.append("Bullish EMA alignment with +DI leading.")
            else:
                bias = "NEUTRAL"
                strength = 0.3
                explanation_parts.append("Bullish EMAs but -DI is diverging higher.")
        elif bearish_stack and curr_price < (ema_20 or curr_price):
            p_di = curr_p_di or 0.0
            m_di = curr_m_di or 0.0
            if m_di >= p_di:
                bias = "BEARISH"
                adx_contrib = min(0.5, (curr_adx or 20.0) / 60.0)
                stack_contrib = 0.5 if ema_stack_ordered else 0.3
                strength = min(1.0, stack_contrib + adx_contrib)
                explanation_parts.append("Bearish EMA alignment with -DI leading.")
            else:
                bias = "NEUTRAL"
                strength = 0.3
                explanation_parts.append("Bearish EMAs but +DI is diverging higher.")
        else:
            bias = "NEUTRAL"
            strength = 0.2
            explanation_parts.append("Mixed price action relative to moving averages.")

        # Apply confidence discount
        strength = max(0.0, strength * (1.0 - confidence_discount))

        if confidence_discount > 0:
            explanation_parts.append(f"Confidence discounted by {confidence_discount*100:.0f}% (warm-up {n}/200 bars).")
        if curr_adx is not None:
            explanation_parts.append(f"ADX: {curr_adx:.1f} (slope: {adx_slope:+.2f}).")

        return TrendAnalystOutput(
            timestamp=input_data.timestamp,
            symbol=input_data.symbol,
            timeframe=input_data.timeframe,
            composite_bias=bias,
            trend_strength_score=round(strength, 3),
            ema_values=ema_dict,
            ema_stack_ordered=ema_stack_ordered,
            adx_value=round(curr_adx, 2) if curr_adx else None,
            plus_di=round(curr_p_di, 2) if curr_p_di else None,
            minus_di=round(curr_m_di, 2) if curr_m_di else None,
            adx_slope=adx_slope,
            distance_from_200_ema_pct=dist_200_pct,
            confidence_discount=confidence_discount,
            explanation=" ".join(explanation_parts),
        )
