"""
NEPTUNE Market Scanner Agent (`market_scanner`)

Identifies market regime across active cryptocurrency symbols:
- TRENDING_BULL, TRENDING_BEAR
- RANGING (consolidation/compression)
- VOLATILE (high expansion/turmoil)
- UNCERTAIN (insufficient history or conflicting signals)

Follows:
- BaseAgent interface (Rule A-06, Rule A-07)
- Closed candles only (Rule A-09)
- Deterministic conditions, no arbitrary guesses.
"""
from typing import Any, Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field

from app.agents.base_agent import BaseAgent
from app.analytics.indicators import (
    calculate_adx,
    calculate_atr,
    calculate_bollinger_bands,
    calculate_ema,
    calculate_keltner_channels,
)
from app.data.market.validator import ValidatedCandle


class MarketScannerInput(BaseModel):
    timestamp: str                                    # ISO 8601 UTC
    symbols: List[str]
    timeframe: str = "15m"
    candles_by_symbol: Dict[str, List[ValidatedCandle]]
    atr_period: int = 14
    bb_period: int = 20
    adx_period: int = 14


class SymbolRegimeState(BaseModel):
    symbol: str
    timeframe: str
    current_price: float
    regime: str                                       # TRENDING_BULL, TRENDING_BEAR, RANGING, VOLATILE, UNCERTAIN
    confidence: float = Field(ge=0.0, le=1.0)
    atr_14: Optional[float] = None
    atr_ratio: Optional[float] = None
    bollinger_bandwidth: Optional[float] = None
    is_squeeze: bool = False
    adx_14: Optional[float] = None
    explanation: str
    supporting_metrics: Dict[str, Any] = {}


class MarketScannerOutput(BaseModel):
    timestamp: str
    timeframe: str
    symbols_evaluated: int
    regimes: Dict[str, SymbolRegimeState]
    global_market_state: str                          # NORMAL, COMPRESSED, HIGH_VOLATILITY, UNCERTAIN
    explanation: str


class MarketScannerAgent(BaseAgent[MarketScannerInput, MarketScannerOutput]):
    """Specialist agent detecting market volatility and regime structures."""

    agent_id: str = "market_scanner"
    agent_name: str = "Market Scanner"

    async def execute(self, input_data: MarketScannerInput) -> MarketScannerOutput:
        regimes: Dict[str, SymbolRegimeState] = {}
        tf = input_data.timeframe

        for sym in input_data.symbols:
            candles = input_data.candles_by_symbol.get(sym, [])
            # Filter strictly to closed candles (Rule A-09)
            closed_candles = [c for c in candles if c.is_closed]

            if len(closed_candles) < 30:
                regimes[sym] = SymbolRegimeState(
                    symbol=sym,
                    timeframe=tf,
                    current_price=closed_candles[-1].close if closed_candles else 0.0,
                    regime="UNCERTAIN",
                    confidence=0.0,
                    explanation=f"Insufficient closed candle history ({len(closed_candles)}/30 min).",
                )
                continue

            highs = [c.high for c in closed_candles]
            lows = [c.low for c in closed_candles]
            closes = [c.close for c in closed_candles]
            curr_price = closes[-1]

            # Indicators
            atr_vals = calculate_atr(highs, lows, closes, period=input_data.atr_period)
            curr_atr = atr_vals[-1]
            valid_atrs = [a for a in atr_vals if a is not None]
            rolling_atr_mean = float(np.mean(valid_atrs[-50:])) if len(valid_atrs) >= 10 else curr_atr
            atr_ratio = (curr_atr / rolling_atr_mean) if (curr_atr and rolling_atr_mean and rolling_atr_mean > 0) else 1.0

            bb_upper, _, bb_lower, bw_vals = calculate_bollinger_bands(closes, period=input_data.bb_period)
            curr_bw = bw_vals[-1]

            kc_upper, _, kc_lower = calculate_keltner_channels(highs, lows, closes, ema_period=20, atr_period=10)

            is_squeeze = False
            if (
                bb_upper[-1] is not None
                and bb_lower[-1] is not None
                and kc_upper[-1] is not None
                and kc_lower[-1] is not None
            ):
                is_squeeze = bool(bb_upper[-1] < kc_upper[-1] and bb_lower[-1] > kc_lower[-1])

            adx_vals, plus_di, minus_di = calculate_adx(highs, lows, closes, period=input_data.adx_period)
            curr_adx = adx_vals[-1]
            curr_p_di = plus_di[-1]
            curr_m_di = minus_di[-1]

            ema_50 = calculate_ema(closes, 50)
            curr_ema_50 = ema_50[-1]

            # Deterministic regime classification
            regime = "UNCERTAIN"
            confidence = 0.5
            explanation = ""

            if atr_ratio is not None and atr_ratio > 1.8:
                regime = "VOLATILE"
                confidence = float(min(1.0, 0.6 + (atr_ratio - 1.8) * 0.2))
                explanation = f"High volatility expansion: ATR ratio {atr_ratio:.2f}x above baseline."
            elif is_squeeze:
                regime = "RANGING"
                confidence = 0.85
                explanation = "Volatility squeeze: Bollinger Bands compressed within Keltner Channels."
            elif curr_adx is not None and curr_adx >= 25.0:
                p_di = curr_p_di or 0.0
                m_di = curr_m_di or 0.0
                if curr_ema_50 and curr_price > curr_ema_50 and p_di > m_di:
                    regime = "TRENDING_BULL"
                    confidence = float(min(0.95, curr_adx / 50.0))
                    explanation = f"Bullish trend confirmed: ADX {curr_adx:.1f} >= 25, price above EMA 50, +DI > -DI."
                elif curr_ema_50 and curr_price < curr_ema_50 and m_di > p_di:
                    regime = "TRENDING_BEAR"
                    confidence = float(min(0.95, curr_adx / 50.0))
                    explanation = f"Bearish trend confirmed: ADX {curr_adx:.1f} >= 25, price below EMA 50, -DI > +DI."
                else:
                    regime = "UNCERTAIN"
                    confidence = 0.40
                    explanation = f"Conflicting trend signals: ADX is {curr_adx:.1f} but price/DI alignment is mixed."
            elif curr_adx is not None and curr_adx < 20.0:
                regime = "RANGING"
                confidence = float(max(0.5, 1.0 - (curr_adx / 20.0)))
                explanation = f"Ranging / non-trending market: ADX {curr_adx:.1f} < 20 indicates weak directional movement."
            else:
                regime = "UNCERTAIN"
                confidence = 0.40
                adx_str = f"{curr_adx:.1f}" if curr_adx is not None else "N/A"
                explanation = f"Transitional regime (ADX {adx_str}): neither strong trend nor clear squeeze."

            regimes[sym] = SymbolRegimeState(
                symbol=sym,
                timeframe=tf,
                current_price=curr_price,
                regime=regime,
                confidence=round(confidence, 3),
                atr_14=round(curr_atr, 4) if curr_atr else None,
                atr_ratio=round(atr_ratio, 3) if atr_ratio else None,
                bollinger_bandwidth=round(curr_bw, 4) if curr_bw else None,
                is_squeeze=is_squeeze,
                adx_14=round(curr_adx, 2) if curr_adx else None,
                explanation=explanation,
                supporting_metrics={
                    "plus_di": round(curr_p_di, 2) if curr_p_di else None,
                    "minus_di": round(curr_m_di, 2) if curr_m_di else None,
                    "ema_50": round(curr_ema_50, 4) if curr_ema_50 else None,
                },
            )

        # Global market state summary
        regime_list = [r.regime for r in regimes.values()]
        if any(r == "VOLATILE" for r in regime_list):
            global_state = "HIGH_VOLATILITY"
            global_exp = "Elevated volatility detected across tracked assets."
        elif all(r == "RANGING" for r in regime_list):
            global_state = "COMPRESSED"
            global_exp = "Widespread consolidation / compression across tracked symbols."
        elif any(r in ("TRENDING_BULL", "TRENDING_BEAR") for r in regime_list):
            global_state = "NORMAL"
            global_exp = "Active directional trending detected in one or more pairs."
        else:
            global_state = "UNCERTAIN"
            global_exp = "Mixed or insufficient market conditions across symbols."

        return MarketScannerOutput(
            timestamp=input_data.timestamp,
            timeframe=tf,
            symbols_evaluated=len(regimes),
            regimes=regimes,
            global_market_state=global_state,
            explanation=global_exp,
        )

