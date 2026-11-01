"""
NEPTUNE Quantitative Analysis — Deterministic Technical Indicators

Pure mathematical functions for market indicators:
- EMA, SMA, ATR, ADX (with +DI / -DI)
- RSI (Wilder's smoothed)
- MACD (line, signal, histogram)
- Bollinger Bands & Keltner Channels
- VWAP & OBV

Properties:
- Pure functions: no external state, database, or network requests.
- Causal: strict look-ahead prevention (bar i uses only bars 0..i).
- Handles warm-up periods explicitly by returning None for un-warmed values.
"""
from typing import List, Optional, Sequence, Tuple
import math
import numpy as np


def calculate_sma(series: Sequence[float], period: int) -> List[Optional[float]]:
    """Simple Moving Average with None during warm-up period."""
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    n = len(series)
    out: List[Optional[float]] = [None] * n
    if n < period:
        return out

    rolling_sum = sum(series[:period])
    out[period - 1] = float(rolling_sum / period)

    for i in range(period, n):
        rolling_sum += series[i] - series[i - period]
        out[i] = float(rolling_sum / period)

    return out


def calculate_ema(series: Sequence[float], period: int) -> List[Optional[float]]:
    """
    Exponential Moving Average.
    Warm-up: first 'period - 1' items are None.
    Initial seed at index 'period - 1' is the SMA of the first 'period' values.
    Subsequent values use alpha = 2 / (period + 1).
    """
    if period <= 0:
        raise ValueError(f"period must be > 0, got {period}")
    n = len(series)
    out: List[Optional[float]] = [None] * n
    if n < period:
        return out

    alpha = 2.0 / (period + 1.0)
    # Seed with SMA
    sma_seed = sum(series[:period]) / period
    out[period - 1] = float(sma_seed)

    curr_ema = sma_seed
    for i in range(period, n):
        curr_ema = (series[i] * alpha) + (curr_ema * (1.0 - alpha))
        out[i] = float(curr_ema)

    return out


def calculate_atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> List[Optional[float]]:
    """
    Average True Range using Wilder's Smoothing.
    TR_t = max(H_t - L_t, |H_t - C_{t-1}|, |L_t - C_{t-1}|)
    First ATR is SMA of first 'period' True Ranges.
    """
    n = len(highs)
    if n != len(lows) or n != len(closes):
        raise ValueError("highs, lows, closes must be equal length")
    if period <= 0:
        raise ValueError("period must be > 0")

    out: List[Optional[float]] = [None] * n
    if n < period:
        return out

    tr: List[float] = [0.0] * n
    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr[i] = max(hl, hc, lc)

    # Initial SMA of TR
    atr = sum(tr[:period]) / period
    out[period - 1] = float(atr)

    for i in range(period, n):
        atr = ((atr * (period - 1)) + tr[i]) / period
        out[i] = float(atr)

    return out


def calculate_adx(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """
    Average Directional Index (ADX) with +DI and -DI.
    Returns (adx, plus_di, minus_di).
    """
    n = len(highs)
    if n != len(lows) or n != len(closes):
        raise ValueError("highs, lows, closes must have same length")

    adx_out: List[Optional[float]] = [None] * n
    plus_di_out: List[Optional[float]] = [None] * n
    minus_di_out: List[Optional[float]] = [None] * n

    # Warm-up requirement: at least (2 * period) candles needed for smoothed ADX
    if n < (2 * period):
        return adx_out, plus_di_out, minus_di_out

    tr: List[float] = [0.0] * n
    plus_dm: List[float] = [0.0] * n
    minus_dm: List[float] = [0.0] * n

    tr[0] = highs[0] - lows[0]
    for i in range(1, n):
        up_move = highs[i] - highs[i - 1]
        down_move = lows[i - 1] - lows[i]

        plus_dm[i] = up_move if (up_move > down_move and up_move > 0) else 0.0
        minus_dm[i] = down_move if (down_move > up_move and down_move > 0) else 0.0

        hl = highs[i] - lows[i]
        hc = abs(highs[i] - closes[i - 1])
        lc = abs(lows[i] - closes[i - 1])
        tr[i] = max(hl, hc, lc)

    # Wilder smoothing for TR and DMs
    # First valid directional changes occur on bars 1..period (period items)
    smooth_tr = sum(tr[1 : period + 1])
    smooth_plus_dm = sum(plus_dm[1 : period + 1])
    smooth_minus_dm = sum(minus_dm[1 : period + 1])

    dx: List[Optional[float]] = [None] * n

    for i in range(period, n):
        if i > period:
            smooth_tr = smooth_tr - (smooth_tr / period) + tr[i]
            smooth_plus_dm = smooth_plus_dm - (smooth_plus_dm / period) + plus_dm[i]
            smooth_minus_dm = smooth_minus_dm - (smooth_minus_dm / period) + minus_dm[i]

        p_di = 100.0 * (smooth_plus_dm / smooth_tr) if smooth_tr > 0 else 0.0
        m_di = 100.0 * (smooth_minus_dm / smooth_tr) if smooth_tr > 0 else 0.0

        plus_di_out[i] = float(p_di)
        minus_di_out[i] = float(m_di)

        di_sum = p_di + m_di
        di_diff = abs(p_di - m_di)
        dx[i] = 100.0 * (di_diff / di_sum) if di_sum > 0 else 0.0

    # Calculate ADX as Wilder's smoothed DX
    first_adx_idx = (2 * period) - 1
    valid_dx = [x for x in dx[period:first_adx_idx + 1] if x is not None]
    if len(valid_dx) == period:
        curr_adx = sum(valid_dx) / period
        adx_out[first_adx_idx] = float(curr_adx)

        for i in range(first_adx_idx + 1, n):
            curr_dx = dx[i] if dx[i] is not None else 0.0
            curr_adx = ((curr_adx * (period - 1)) + curr_dx) / period
            adx_out[i] = float(curr_adx)

    return adx_out, plus_di_out, minus_di_out


def calculate_rsi(closes: Sequence[float], period: int = 14) -> List[Optional[float]]:
    """
    Relative Strength Index using Wilder's smoothed averages.
    Returns 0.0 to 100.0. Warm-up is 'period' items.
    """
    n = len(closes)
    out: List[Optional[float]] = [None] * n
    if n <= period or period <= 0:
        return out

    gains = [0.0] * n
    losses = [0.0] * n

    for i in range(1, n):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            gains[i] = delta
        else:
            losses[i] = -delta

    avg_gain = sum(gains[1:period + 1]) / period
    avg_loss = sum(losses[1:period + 1]) / period

    if avg_loss == 0.0 and avg_gain == 0.0:
        out[period] = 50.0
    elif avg_loss == 0.0:
        out[period] = 100.0
    elif avg_gain == 0.0:
        out[period] = 0.0
    else:
        rs = avg_gain / avg_loss
        out[period] = float(100.0 - (100.0 / (1.0 + rs)))

    for i in range(period + 1, n):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

        if avg_loss == 0.0 and avg_gain == 0.0:
            out[i] = 50.0
        elif avg_loss == 0.0:
            out[i] = 100.0
        elif avg_gain == 0.0:
            out[i] = 0.0
        else:
            rs = avg_gain / avg_loss
            out[i] = float(100.0 - (100.0 / (1.0 + rs)))

    return out


def calculate_macd(
    closes: Sequence[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """
    Moving Average Convergence Divergence.
    Returns (macd_line, signal_line, histogram).
    """
    n = len(closes)
    macd_line: List[Optional[float]] = [None] * n
    signal_line: List[Optional[float]] = [None] * n
    histogram: List[Optional[float]] = [None] * n

    if n < slow:
        return macd_line, signal_line, histogram

    fast_ema = calculate_ema(closes, fast)
    slow_ema = calculate_ema(closes, slow)

    valid_macd_values: List[float] = []
    macd_start_idx = slow - 1

    for i in range(macd_start_idx, n):
        if fast_ema[i] is not None and slow_ema[i] is not None:
            val = fast_ema[i] - slow_ema[i]
            macd_line[i] = float(val)
            valid_macd_values.append(val)

    if len(valid_macd_values) >= signal:
        sig_ema = calculate_ema(valid_macd_values, signal)
        offset = macd_start_idx
        for j, s_val in enumerate(sig_ema):
            idx = offset + j
            signal_line[idx] = s_val
            if macd_line[idx] is not None and s_val is not None:
                histogram[idx] = float(macd_line[idx] - s_val)

    return macd_line, signal_line, histogram


def calculate_bollinger_bands(
    closes: Sequence[float],
    period: int = 20,
    num_std: float = 2.0,
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """
    Bollinger Bands: returns (upper, middle, lower, bandwidth).
    bandwidth = (upper - lower) / middle.
    """
    n = len(closes)
    upper: List[Optional[float]] = [None] * n
    middle: List[Optional[float]] = [None] * n
    lower: List[Optional[float]] = [None] * n
    bandwidth: List[Optional[float]] = [None] * n

    if n < period:
        return upper, middle, lower, bandwidth

    sma = calculate_sma(closes, period)

    for i in range(period - 1, n):
        window = closes[i - period + 1 : i + 1]
        m = sma[i]
        std = float(np.std(window, ddof=0))
        u = m + (num_std * std)
        l = m - (num_std * std)
        bw = (u - l) / m if m > 0 else 0.0

        upper[i] = float(u)
        middle[i] = float(m)
        lower[i] = float(l)
        bandwidth[i] = float(bw)

    return upper, middle, lower, bandwidth


def calculate_keltner_channels(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    ema_period: int = 20,
    atr_period: int = 10,
    multiplier: float = 1.5,
) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """Keltner Channels: returns (upper, center, lower)."""
    n = len(closes)
    upper: List[Optional[float]] = [None] * n
    center = calculate_ema(closes, ema_period)
    atr = calculate_atr(highs, lows, closes, atr_period)
    lower: List[Optional[float]] = [None] * n

    start = max(ema_period, atr_period) - 1
    for i in range(start, n):
        c = center[i]
        a = atr[i]
        if c is not None and a is not None:
            upper[i] = float(c + (multiplier * a))
            lower[i] = float(c - (multiplier * a))

    return upper, center, lower


def calculate_vwap(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    volumes: Sequence[float],
) -> List[Optional[float]]:
    """Volume-Weighted Average Price across sequence."""
    n = len(closes)
    out: List[Optional[float]] = [None] * n
    cum_pv = 0.0
    cum_vol = 0.0

    for i in range(n):
        tp = (highs[i] + lows[i] + closes[i]) / 3.0
        v = volumes[i]
        cum_pv += tp * v
        cum_vol += v
        out[i] = float(cum_pv / cum_vol) if cum_vol > 0 else None

    return out


def calculate_obv(
    closes: Sequence[float],
    volumes: Sequence[float],
) -> List[Optional[float]]:
    """On-Balance Volume (OBV)."""
    n = len(closes)
    if n == 0:
        return []
    out: List[Optional[float]] = [None] * n
    curr_obv = float(volumes[0])
    out[0] = curr_obv

    for i in range(1, n):
        if closes[i] > closes[i - 1]:
            curr_obv += volumes[i]
        elif closes[i] < closes[i - 1]:
            curr_obv -= volumes[i]
        out[i] = float(curr_obv)

    return out

