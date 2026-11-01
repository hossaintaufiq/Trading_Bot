"""
NEPTUNE Volume Analyst Agent (`volume_analyst`)

Analyzes liquidity, volume profile, VWAP divergence, and accumulation:
- Relative volume against configurable rolling baseline (SMA 20)
- Session / Rolling VWAP and price deviation percentage
- Volume surges and anomaly detection (> 2.5 standard deviations)
- On-Balance Volume (OBV) accumulation vs distribution
- Graceful handling of zero volume or insufficient history.
"""
from typing import List, Optional
import numpy as np
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.analytics.indicators import calculate_obv, calculate_sma, calculate_vwap
from app.data.market.validator import ValidatedCandle


class VolumeAnalystInput(BaseModel):
    timestamp: str                                    # ISO 8601 UTC
    symbol: str
    timeframe: str = "15m"
    candles: List[ValidatedCandle]
    volume_ma_period: int = 20
    anomaly_std_threshold: float = 2.5


class VolumeAnalystOutput(BaseModel):
    timestamp: str
    symbol: str
    timeframe: str
    current_volume: float
    volume_ma: Optional[float] = None
    volume_ratio: Optional[float] = None              # current / volume_ma
    is_volume_anomaly: bool = False
    vwap: Optional[float] = None
    distance_from_vwap_pct: Optional[float] = None
    obv: Optional[float] = None
    obv_trend: str = "NEUTRAL"                        # ACCUMULATION, DISTRIBUTION, NEUTRAL, INSUFFICIENT_DATA
    participation_strength: str                       # STRONG, NORMAL, WEAK, INSUFFICIENT_DATA
    volume_score: float = Field(ge=-1.0, le=1.0)      # -1.0 to +1.0
    explanation: str


class VolumeAnalystAgent(BaseAgent[VolumeAnalystInput, VolumeAnalystOutput]):
    """Specialist agent analyzing trading volume, VWAP benchmarks, and liquidity anomalies."""

    agent_id: str = "volume_analyst"
    agent_name: str = "Volume Analyst"

    async def execute(self, input_data: VolumeAnalystInput) -> VolumeAnalystOutput:
        closed = [c for c in input_data.candles if c.is_closed]
        n = len(closed)

        if n < input_data.volume_ma_period:
            curr_v = closed[-1].volume if closed else 0.0
            return VolumeAnalystOutput(
                timestamp=input_data.timestamp,
                symbol=input_data.symbol,
                timeframe=input_data.timeframe,
                current_volume=curr_v,
                participation_strength="INSUFFICIENT_DATA",
                volume_score=0.0,
                explanation=f"Insufficient history ({n}/{input_data.volume_ma_period} bars) for volume analysis.",
            )

        volumes = [c.volume for c in closed]
        closes = [c.close for c in closed]
        highs = [c.high for c in closed]
        lows = [c.low for c in closed]

        curr_vol = volumes[-1]
        curr_price = closes[-1]

        # Calculate Volume SMA
        vol_smas = calculate_sma(volumes, period=input_data.volume_ma_period)
        curr_vol_ma = vol_smas[-1]

        # Relative Volume Ratio
        vol_ratio = 1.0
        if curr_vol_ma and curr_vol_ma > 0:
            vol_ratio = curr_vol / curr_vol_ma

        # Volume Anomaly Detection (> 2.5 std devs over recent window)
        recent_vols = volumes[-max(50, input_data.volume_ma_period):]
        vol_mean = float(np.mean(recent_vols))
        vol_std = float(np.std(recent_vols, ddof=0))
        is_anomaly = bool(vol_std > 0 and curr_vol > (vol_mean + (input_data.anomaly_std_threshold * vol_std)))

        # Calculate VWAP
        vwap_vals = calculate_vwap(highs, lows, closes, volumes)
        curr_vwap = vwap_vals[-1]
        dist_vwap_pct = None
        if curr_vwap and curr_vwap > 0:
            dist_vwap_pct = round(((curr_price - curr_vwap) / curr_vwap) * 100.0, 3)

        # Calculate OBV and Trend over last 10 bars
        obv_vals = calculate_obv(closes, volumes)
        curr_obv = obv_vals[-1]
        obv_trend = "NEUTRAL"
        if len(obv_vals) >= 10:
            obv_slope = obv_vals[-1] - obv_vals[-10]
            if obv_slope > 0:
                obv_trend = "ACCUMULATION"
            elif obv_slope < 0:
                obv_trend = "DISTRIBUTION"

        # Participation Strength
        if vol_ratio >= 1.5:
            participation = "STRONG"
        elif vol_ratio >= 0.8:
            participation = "NORMAL"
        else:
            participation = "WEAK"

        # Volume Score (-1.0 to +1.0)
        # Combines relative volume with OBV direction and price position vs VWAP
        obv_mult = 1.0 if obv_trend == "ACCUMULATION" else (-1.0 if obv_trend == "DISTRIBUTION" else 0.0)
        vwap_dir = 1.0 if (dist_vwap_pct and dist_vwap_pct > 0) else (-1.0 if (dist_vwap_pct and dist_vwap_pct < 0) else 0.0)
        vol_magnitude = min(1.0, vol_ratio / 2.0)
        score = float(np.clip((obv_mult * 0.6 + vwap_dir * 0.4) * vol_magnitude, -1.0, 1.0))

        # Explainable summary
        exp_parts = [
            f"Volume {participation} ({curr_vol:.2f}, {vol_ratio:.2f}x SMA).",
            f"OBV {obv_trend}.",
        ]
        if is_anomaly:
            exp_parts.append(f"Volume anomaly surge detected ({curr_vol:.2f} > {input_data.anomaly_std_threshold}x std).")
        if dist_vwap_pct is not None:
            exp_parts.append(f"Price is {dist_vwap_pct:+.2f}% relative to VWAP.")

        return VolumeAnalystOutput(
            timestamp=input_data.timestamp,
            symbol=input_data.symbol,
            timeframe=input_data.timeframe,
            current_volume=round(curr_vol, 4),
            volume_ma=round(curr_vol_ma, 4) if curr_vol_ma else None,
            volume_ratio=round(vol_ratio, 3) if vol_ratio else None,
            is_volume_anomaly=is_anomaly,
            vwap=round(curr_vwap, 4) if curr_vwap else None,
            distance_from_vwap_pct=dist_vwap_pct,
            obv=round(curr_obv, 2) if curr_obv else None,
            obv_trend=obv_trend,
            participation_strength=participation,
            volume_score=round(score, 3),
            explanation=" ".join(exp_parts),
        )
