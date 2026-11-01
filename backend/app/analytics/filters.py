"""
NEPTUNE Quantitative Analysis — Deterministic Entry Filters (`filters.py`)

Specialist filtering library evaluating regime, volatility, momentum, volume,
and multi-timeframe alignment invariants to protect entry expectancy.

Governing Rules:
- Rule S-05: Strict look-ahead bias prevention (HTF lookups strictly <= T).
- Rule A-09: Evaluates strictly closed candles.
- Rule E-01: Single-responsibility, concise implementation (< 300 lines).
- Rule E-03: Typed Pydantic models.
"""
from typing import Any, Dict, List, Optional, Sequence
from pydantic import BaseModel, Field

from app.analytics.indicators import (
    calculate_adx,
    calculate_atr,
    calculate_ema,
    calculate_macd,
    calculate_rsi,
)
from app.data.market.validator import ValidatedCandle


class FilterDecision(BaseModel):
    """Result of an individual entry filter evaluation."""
    filter_id: str
    passed: bool
    direction: str
    rejection_reason: Optional[str] = None
    telemetry: Dict[str, Any] = Field(default_factory=dict)


def filter_trend_strength_adx(
    candles: Sequence[ValidatedCandle],
    direction: str,
    min_adx: float = 25.0,
    require_di: bool = True,
) -> FilterDecision:
    """Hypothesis 1: Require minimum ADX and directional index alignment."""
    if len(candles) < 30:
        return FilterDecision(filter_id="H1_TREND_STRENGTH", passed=False, direction=direction,
                              rejection_reason="Insufficient candles for ADX calculation (< 30).")

    highs, lows, closes = [c.high for c in candles], [c.low for c in candles], [c.close for c in candles]
    adx_vals, plus_di_vals, minus_di_vals = calculate_adx(highs, lows, closes, period=14)
    adx = adx_vals[-1] if adx_vals and adx_vals[-1] is not None else 0.0
    p_di = plus_di_vals[-1] if plus_di_vals and plus_di_vals[-1] is not None else 0.0
    m_di = minus_di_vals[-1] if minus_di_vals and minus_di_vals[-1] is not None else 0.0
    telemetry = {"adx": round(adx, 2), "plus_di": round(p_di, 2), "minus_di": round(m_di, 2)}

    if adx < min_adx:
        return FilterDecision(filter_id="H1_TREND_STRENGTH", passed=False, direction=direction,
                              rejection_reason=f"ADX {adx:.2f} below threshold {min_adx:.2f} (weak trend).", telemetry=telemetry)

    if require_di:
        if direction == "LONG" and p_di <= m_di:
            return FilterDecision(filter_id="H1_TREND_STRENGTH", passed=False, direction=direction,
                                  rejection_reason=f"Direction conflict: Long setup but +DI ({p_di:.2f}) <= -DI ({m_di:.2f}).", telemetry=telemetry)
        elif direction == "SHORT" and m_di <= p_di:
            return FilterDecision(filter_id="H1_TREND_STRENGTH", passed=False, direction=direction,
                                  rejection_reason=f"Direction conflict: Short setup but -DI ({m_di:.2f}) <= +DI ({p_di:.2f}).", telemetry=telemetry)

    return FilterDecision(filter_id="H1_TREND_STRENGTH", passed=True, direction=direction, telemetry=telemetry)


def filter_higher_timeframe_alignment(
    current_ts: str,
    direction: str,
    htf_candles: Sequence[ValidatedCandle],
) -> FilterDecision:
    """Hypothesis 2: Require higher timeframe EMA trend alignment without lookahead."""
    valid_htf = [c for c in htf_candles if c.timestamp <= current_ts and c.is_closed]
    if len(valid_htf) < 50:
        return FilterDecision(filter_id="H2_HTF_ALIGNMENT", passed=False, direction=direction,
                              rejection_reason=f"Insufficient HTF candle history ({len(valid_htf)}/50).")

    htf_closes = [c.close for c in valid_htf]
    ema20 = calculate_ema(htf_closes, period=20)
    ema50 = calculate_ema(htf_closes, period=50)
    e20_val = ema20[-1] if ema20 and ema20[-1] is not None else 0.0
    e50_val = ema50[-1] if ema50 and ema50[-1] is not None else 0.0
    latest_htf_close = htf_closes[-1]
    telemetry = {"htf_timestamp": valid_htf[-1].timestamp, "htf_close": latest_htf_close,
                 "htf_ema20": round(e20_val, 2), "htf_ema50": round(e50_val, 2)}

    if direction == "LONG" and (e20_val <= e50_val or latest_htf_close <= e50_val):
        return FilterDecision(filter_id="H2_HTF_ALIGNMENT", passed=False, direction=direction,
                              rejection_reason=f"HTF Trend Bearish (EMA20 {e20_val:.2f} <= EMA50 {e50_val:.2f} or Close below EMA50).", telemetry=telemetry)
    elif direction == "SHORT" and (e20_val >= e50_val or latest_htf_close >= e50_val):
        return FilterDecision(filter_id="H2_HTF_ALIGNMENT", passed=False, direction=direction,
                              rejection_reason=f"HTF Trend Bullish (EMA20 {e20_val:.2f} >= EMA50 {e50_val:.2f} or Close above EMA50).", telemetry=telemetry)

    return FilterDecision(filter_id="H2_HTF_ALIGNMENT", passed=True, direction=direction, telemetry=telemetry)


def filter_momentum_confirmation(
    candles: Sequence[ValidatedCandle],
    direction: str,
    min_rsi: float = 40.0,
    max_rsi: float = 62.0,
    require_macd_accel: bool = True,
) -> FilterDecision:
    """Hypothesis 3: Corridor RSI and MACD histogram acceleration in trade direction."""
    if len(candles) < 35:
        return FilterDecision(filter_id="H3_MOMENTUM_CONFIRMATION", passed=False, direction=direction,
                              rejection_reason="Insufficient candles for MACD/RSI (< 35).")

    closes = [c.close for c in candles]
    rsi_vals = calculate_rsi(closes, period=14)
    rsi = rsi_vals[-1] if rsi_vals and rsi_vals[-1] is not None else 50.0

    _, _, hist_vals = calculate_macd(closes)
    curr_hist = hist_vals[-1] if hist_vals and hist_vals[-1] is not None else 0.0
    prev_hist = hist_vals[-2] if hist_vals and len(hist_vals) >= 2 and hist_vals[-2] is not None else 0.0
    telemetry = {"rsi": round(rsi, 2), "macd_hist_curr": round(curr_hist, 4), "macd_hist_prev": round(prev_hist, 4)}

    if direction == "LONG":
        if rsi < min_rsi or rsi > max_rsi:
            return FilterDecision(filter_id="H3_MOMENTUM_CONFIRMATION", passed=False, direction=direction,
                                  rejection_reason=f"Long RSI {rsi:.2f} outside active corridor [{min_rsi}, {max_rsi}].", telemetry=telemetry)
        if require_macd_accel and curr_hist <= prev_hist:
            return FilterDecision(filter_id="H3_MOMENTUM_CONFIRMATION", passed=False, direction=direction,
                                  rejection_reason=f"MACD histogram decelerating ({curr_hist:.4f} <= {prev_hist:.4f}).", telemetry=telemetry)
    elif direction == "SHORT":
        s_min, s_max = 100.0 - max_rsi, 100.0 - min_rsi
        if rsi < s_min or rsi > s_max:
            return FilterDecision(filter_id="H3_MOMENTUM_CONFIRMATION", passed=False, direction=direction,
                                  rejection_reason=f"Short RSI {rsi:.2f} outside corridor [{s_min}, {s_max}].", telemetry=telemetry)
        if require_macd_accel and curr_hist >= prev_hist:
            return FilterDecision(filter_id="H3_MOMENTUM_CONFIRMATION", passed=False, direction=direction,
                                  rejection_reason=f"MACD histogram accelerating upward against short ({curr_hist:.4f} >= {prev_hist:.4f}).", telemetry=telemetry)

    return FilterDecision(filter_id="H3_MOMENTUM_CONFIRMATION", passed=True, direction=direction, telemetry=telemetry)


def filter_volume_confirmation(
    candles: Sequence[ValidatedCandle],
    direction: str,
    min_rvol: float = 0.85,
) -> FilterDecision:
    """Hypothesis 4: Require relative volume above threshold to avoid low-liquidity drift."""
    if len(candles) < 20:
        return FilterDecision(filter_id="H4_VOLUME_CONFIRMATION", passed=False, direction=direction,
                              rejection_reason="Insufficient candles for volume SMA (< 20).")

    vols = [c.volume for c in candles]
    recent_vols = vols[-20:]
    avg_v = sum(recent_vols) / len(recent_vols) if recent_vols else 1.0
    rvol = (vols[-1] / avg_v) if avg_v > 0 else 1.0
    telemetry = {"rvol": round(rvol, 3), "curr_vol": vols[-1], "avg_vol": round(avg_v, 2)}

    if rvol < min_rvol:
        return FilterDecision(filter_id="H4_VOLUME_CONFIRMATION", passed=False, direction=direction,
                              rejection_reason=f"RVOL {rvol:.2f} below threshold {min_rvol:.2f} (illiquid setup).", telemetry=telemetry)

    return FilterDecision(filter_id="H4_VOLUME_CONFIRMATION", passed=True, direction=direction, telemetry=telemetry)


def filter_volatility_bounds(
    candles: Sequence[ValidatedCandle],
    direction: str,
    min_vol_pct: float = 0.80,
    max_vol_pct: float = 3.00,
) -> FilterDecision:
    """Hypothesis 5: Enforce ATR volatility band relative to price."""
    if len(candles) < 15:
        return FilterDecision(filter_id="H5_VOLATILITY_BOUNDS", passed=False, direction=direction,
                              rejection_reason="Insufficient candles for ATR (< 15).")

    highs, lows, closes = [c.high for c in candles], [c.low for c in candles], [c.close for c in candles]
    atr_vals = calculate_atr(highs, lows, closes, period=14)
    atr = atr_vals[-1] if atr_vals and atr_vals[-1] is not None else 0.0
    vol_pct = (atr / closes[-1] * 100.0) if closes[-1] > 0 else 0.0
    telemetry = {"atr": round(atr, 4), "volatility_pct": round(vol_pct, 3)}

    if vol_pct < min_vol_pct:
        return FilterDecision(filter_id="H5_VOLATILITY_BOUNDS", passed=False, direction=direction,
                              rejection_reason=f"Volatility {vol_pct:.3f}% below minimum {min_vol_pct:.2f}% (ranging chop).", telemetry=telemetry)
    if vol_pct > max_vol_pct:
        return FilterDecision(filter_id="H5_VOLATILITY_BOUNDS", passed=False, direction=direction,
                              rejection_reason=f"Volatility {vol_pct:.3f}% exceeds maximum {max_vol_pct:.2f}% (blowout hazard).", telemetry=telemetry)

    return FilterDecision(filter_id="H5_VOLATILITY_BOUNDS", passed=True, direction=direction, telemetry=telemetry)


def filter_regime_confidence(
    regime: str,
    confidence: float,
    direction: str,
    min_confidence: float = 0.65,
) -> FilterDecision:
    """Hypothesis 6: Require high-confidence trending market regime."""
    expected_regime = "TRENDING_BULL" if direction == "LONG" else "TRENDING_BEAR"
    telemetry = {"regime": regime, "confidence": round(confidence, 3)}

    if regime != expected_regime:
        return FilterDecision(filter_id="H6_REGIME_CONFIDENCE", passed=False, direction=direction,
                              rejection_reason=f"Regime {regime} does not match required {expected_regime}.", telemetry=telemetry)

    if confidence < min_confidence:
        return FilterDecision(filter_id="H6_REGIME_CONFIDENCE", passed=False, direction=direction,
                              rejection_reason=f"Regime confidence {confidence:.2f} below {min_confidence:.2f}.", telemetry=telemetry)

    return FilterDecision(filter_id="H6_REGIME_CONFIDENCE", passed=True, direction=direction, telemetry=telemetry)


def filter_confluence_ensemble(
    candles: Sequence[ValidatedCandle],
    direction: str,
    current_ts: str,
    htf_candles: Optional[Sequence[ValidatedCandle]] = None,
    min_adx: float = 25.0,
    min_rvol: float = 0.85,
    min_vol_pct: float = 0.80,
) -> FilterDecision:
    """Hypothesis 7: Multi-factor confluence combining top orthogonal filters."""
    d_adx = filter_trend_strength_adx(candles, direction, min_adx=min_adx, require_di=True)
    if not d_adx.passed:
        return d_adx

    d_vol = filter_volume_confirmation(candles, direction, min_rvol=min_rvol)
    if not d_vol.passed:
        return d_vol

    d_vola = filter_volatility_bounds(candles, direction, min_vol_pct=min_vol_pct)
    if not d_vola.passed:
        return d_vola

    if htf_candles:
        d_htf = filter_higher_timeframe_alignment(current_ts, direction, htf_candles)
        if not d_htf.passed:
            return d_htf

    return FilterDecision(
        filter_id="H7_CONFLUENCE_ENSEMBLE",
        passed=True,
        direction=direction,
        telemetry={**d_adx.telemetry, **d_vol.telemetry, **d_vola.telemetry},
    )
