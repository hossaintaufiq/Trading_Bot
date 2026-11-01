"""
NEPTUNE Momentum Analyst Agent (`momentum_analyst`)

Measures velocity, acceleration, and momentum exhaustion:
- RSI (14) with divergence detection
- MACD (12, 26, 9) line, signal line, and histogram
- Histogram slope and momentum regime
- Potential exhaustion flags (divergences or decelerating extremes)
- Rule: RSI overbought/oversold is NOT an automatic trading signal.
"""
from typing import List, Optional
import numpy as np
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.analytics.indicators import calculate_macd, calculate_rsi
from app.data.market.validator import ValidatedCandle


class MomentumAnalystInput(BaseModel):
    timestamp: str                                    # ISO 8601 UTC
    symbol: str
    timeframe: str = "15m"
    candles: List[ValidatedCandle]
    rsi_period: int = 14
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9


class MomentumAnalystOutput(BaseModel):
    timestamp: str
    symbol: str
    timeframe: str
    rsi: Optional[float] = None                       # 0.0 to 100.0
    macd_line: Optional[float] = None
    macd_signal_line: Optional[float] = None
    macd_histogram: Optional[float] = None
    macd_histogram_slope: float = 0.0                 # Change in histogram over last 2 bars
    momentum_direction: str                           # BULLISH, BEARISH, NEUTRAL, UNCERTAIN
    momentum_score: float = Field(ge=-1.0, le=1.0)    # -1.0 (strong bear) to +1.0 (strong bull)
    exhaustion_risk: bool = False
    divergence: str = "NONE"                          # NONE, BULLISH_DIVERGENCE, BEARISH_DIVERGENCE
    explanation: str


class MomentumAnalystAgent(BaseAgent[MomentumAnalystInput, MomentumAnalystOutput]):
    """Specialist agent analyzing price momentum, MACD dynamics, and exhaustion."""

    agent_id: str = "momentum_analyst"
    agent_name: str = "Momentum Analyst"

    async def execute(self, input_data: MomentumAnalystInput) -> MomentumAnalystOutput:
        closed = [c for c in input_data.candles if c.is_closed]
        n = len(closed)

        if n < input_data.macd_slow + input_data.macd_signal:
            return MomentumAnalystOutput(
                timestamp=input_data.timestamp,
                symbol=input_data.symbol,
                timeframe=input_data.timeframe,
                momentum_direction="UNCERTAIN",
                momentum_score=0.0,
                explanation=f"Insufficient candles ({n}/{input_data.macd_slow + input_data.macd_signal}) for momentum calculation.",
            )

        closes = [c.close for c in closed]
        highs = [c.high for c in closed]
        lows = [c.low for c in closed]

        # Calculate RSI
        rsi_vals = calculate_rsi(closes, period=input_data.rsi_period)
        curr_rsi = rsi_vals[-1]

        # Calculate MACD
        macd_line, sig_line, hist_vals = calculate_macd(
            closes,
            fast=input_data.macd_fast,
            slow=input_data.macd_slow,
            signal=input_data.macd_signal,
        )
        curr_macd = macd_line[-1]
        curr_sig = sig_line[-1]
        curr_hist = hist_vals[-1]

        # Histogram slope (acceleration)
        valid_hist = [h for h in hist_vals if h is not None]
        hist_slope = 0.0
        if len(valid_hist) >= 2:
            hist_slope = round(valid_hist[-1] - valid_hist[-2], 4)

        # Detect Divergence & Exhaustion over recent swing window (last 15 bars)
        divergence = "NONE"
        exhaustion_risk = False
        exp_notes = []

        if len(closes) >= 15 and curr_rsi is not None and curr_hist is not None:
            recent_closes = closes[-15:]
            recent_rsi = [r for r in rsi_vals[-15:] if r is not None]

            if len(recent_rsi) >= 10:
                price_high_idx = int(np.argmax(recent_closes))
                price_low_idx = int(np.argmin(recent_closes))
                rsi_high_idx = int(np.argmax(recent_rsi))
                rsi_low_idx = int(np.argmin(recent_rsi))

                # Bearish Divergence: Recent high price with lower RSI high
                if price_high_idx == 14 and rsi_high_idx < 10 and recent_rsi[-1] < recent_rsi[rsi_high_idx] - 3.0:
                    divergence = "BEARISH_DIVERGENCE"
                    exhaustion_risk = True
                    exp_notes.append("Bearish RSI divergence: Price made new local high while RSI failed.")
                # Bullish Divergence: Recent low price with higher RSI low
                elif price_low_idx == 14 and rsi_low_idx < 10 and recent_rsi[-1] > recent_rsi[rsi_low_idx] + 3.0:
                    divergence = "BULLISH_DIVERGENCE"
                    exhaustion_risk = True
                    exp_notes.append("Bullish RSI divergence: Price made new local low while RSI formed higher low.")

            # Momentum Deceleration / Exhaustion at extremes
            if curr_rsi >= 70.0 and hist_slope < 0:
                exhaustion_risk = True
                exp_notes.append(f"Overbought momentum decelerating (RSI {curr_rsi:.1f}, histogram slope {hist_slope:+.4f}).")
            elif curr_rsi <= 30.0 and hist_slope > 0:
                exhaustion_risk = True
                exp_notes.append(f"Oversold momentum decelerating (RSI {curr_rsi:.1f}, histogram slope {hist_slope:+.4f}).")

        # Momentum Direction & Score (-1.0 to +1.0)
        score = 0.0
        direction = "NEUTRAL"

        if curr_rsi is not None and curr_hist is not None:
            # RSI component (-0.5 to +0.5) centered at 50
            rsi_norm = (curr_rsi - 50.0) / 50.0  # -1.0 to +1.0
            # MACD histogram component
            if curr_hist > 0:
                macd_comp = 0.5
            elif curr_hist < 0:
                macd_comp = -0.5
            else:
                macd_comp = 0.0

            if hist_slope > 0:
                macd_comp += 0.2
            elif hist_slope < 0:
                macd_comp -= 0.2

            score = float(np.clip((rsi_norm * 0.5) + (macd_comp * 0.5), -1.0, 1.0))

            if score > 0.20 and curr_hist >= 0:
                direction = "BULLISH"
            elif score < -0.20 and curr_hist <= 0:
                direction = "BEARISH"
            else:
                direction = "NEUTRAL"

        rsi_str = f"{curr_rsi:.1f}" if curr_rsi is not None else "N/A"
        hist_str = f"{curr_hist:.2f}" if curr_hist is not None else "N/A"
        exp_str = f"Momentum {direction} (score: {score:+.2f}, RSI: {rsi_str}, MACD hist: {hist_str})."
        if exp_notes:
            exp_str += " " + " ".join(exp_notes)
        else:
            exp_str += " No exhaustion or divergence detected."

        return MomentumAnalystOutput(
            timestamp=input_data.timestamp,
            symbol=input_data.symbol,
            timeframe=input_data.timeframe,
            rsi=round(curr_rsi, 2) if curr_rsi else None,
            macd_line=round(curr_macd, 4) if curr_macd else None,
            macd_signal_line=round(curr_sig, 4) if curr_sig else None,
            macd_histogram=round(curr_hist, 4) if curr_hist else None,
            macd_histogram_slope=hist_slope,
            momentum_direction=direction,
            momentum_score=round(score, 3),
            exhaustion_risk=exhaustion_risk,
            divergence=divergence,
            explanation=exp_str,
        )
