"""
Technical Indicators Engine for Binance Trading Bot.
High-speed vectorized computations using NumPy and Pandas.
Enhanced with ADX (Regime Detection), Stochastic RSI, Relative Volume (RVOL),
and Bollinger Bandwidth (Squeeze Detection).
"""

from typing import Tuple
import numpy as np
import pandas as pd


def calculate_ema(series: pd.Series, period: int) -> pd.Series:
    """Calculate Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Calculate Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()

    rs = avg_gain / (avg_loss + 1e-10)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def calculate_stoch_rsi(
    series: pd.Series, period: int = 14, smooth_k: int = 3, smooth_d: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """Calculate Stochastic RSI (%K, %D) for precise scalp overbought/oversold turns."""
    rsi = calculate_rsi(series, period)
    rsi_low = rsi.rolling(window=period).min()
    rsi_high = rsi.rolling(window=period).max()
    rsi_range = rsi_high - rsi_low

    stoch = np.where(rsi_range > 1e-6, (rsi - rsi_low) / rsi_range * 100, 50.0)
    stoch_series = pd.Series(stoch, index=series.index)
    k = stoch_series.rolling(window=smooth_k).mean().fillna(50.0)
    d = k.rolling(window=smooth_d).mean().fillna(50.0)
    return k, d


def calculate_bollinger_bands(
    series: pd.Series, period: int = 20, std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands (Upper, Middle, Lower)."""
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    return upper, middle, lower


def calculate_bbw(upper: pd.Series, lower: pd.Series, middle: pd.Series) -> pd.Series:
    """Calculate Bollinger Bandwidth Percentage ((Upper - Lower) / Middle * 100)."""
    bbw = ((upper - lower) / (middle + 1e-10)) * 100
    return bbw.fillna(0.0)


def calculate_macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate MACD line, Signal line, and Histogram."""
    fast_ema = calculate_ema(series, fast)
    slow_ema = calculate_ema(series, slow)
    macd = fast_ema - slow_ema
    signal_line = calculate_ema(macd, signal)
    hist = macd - signal_line
    return macd, signal_line, hist


def calculate_atr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    """Calculate Average True Range (ATR) for dynamic volatility measurement."""
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()


def calculate_adx(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Average Directional Index (ADX) along with +DI and -DI.
    Used for Regime Detection: ADX >= 22 = Trending, ADX < 20 = Choppy / Ranging.
    """
    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0.0)

    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    atr_smooth = tr.rolling(window=period).mean()
    plus_di = 100 * (pd.Series(plus_dm, index=high.index).rolling(window=period).mean() / (atr_smooth + 1e-10))
    minus_di = 100 * (pd.Series(minus_dm, index=high.index).rolling(window=period).mean() / (atr_smooth + 1e-10))

    dx = 100 * ((plus_di - minus_di).abs() / ((plus_di + minus_di) + 1e-10))
    adx = dx.rolling(window=period).mean().fillna(20.0)

    return adx, plus_di.fillna(0.0), minus_di.fillna(0.0)


def calculate_rvol(volume: pd.Series, period: int = 20) -> pd.Series:
    """Calculate Relative Volume (RVOL = current volume / 20-period volume SMA)."""
    vol_sma = volume.rolling(window=period).mean()
    rvol = volume / (vol_sma + 1e-10)
    return rvol.fillna(1.0)


def enrich_dataframe(df: pd.DataFrame, strategy_params: dict = None) -> pd.DataFrame:
    """
    Enrich OHLCV dataframe with all technical indicators.
    df columns expected: ['timestamp', 'open', 'high', 'low', 'close', 'volume']
    """
    if len(df) < 5:
        return df

    params = strategy_params or {}
    fast_ema_p = params.get("fast_ema", 9)
    slow_ema_p = params.get("slow_ema", 21)
    rsi_p = params.get("rsi_period", 14)
    bb_period = params.get("period", 20)
    bb_std = params.get("std_dev", 2.0)

    close = df["close"]

    # Moving Averages
    df["ema_fast"] = calculate_ema(close, fast_ema_p)
    df["ema_slow"] = calculate_ema(close, slow_ema_p)

    # Momentum
    df["rsi"] = calculate_rsi(close, rsi_p)
    stoch_k, stoch_d = calculate_stoch_rsi(close, rsi_p)
    df["stoch_k"] = stoch_k
    df["stoch_d"] = stoch_d

    # Volatility & Bollinger Bands
    upper, mid, lower = calculate_bollinger_bands(close, bb_period, bb_std)
    df["bb_upper"] = upper
    df["bb_middle"] = mid
    df["bb_lower"] = lower
    df["bbw"] = calculate_bbw(upper, lower, mid)

    # MACD
    macd, macd_sig, macd_hist = calculate_macd(close)
    df["macd"] = macd
    df["macd_signal"] = macd_sig
    df["macd_hist"] = macd_hist

    # ATR & Relative Volatility
    if "high" in df.columns and "low" in df.columns:
        atr = calculate_atr(df["high"], df["low"], close, 14)
        df["atr"] = atr
        df["atr_pct"] = (atr / (close + 1e-10)) * 100

        # ADX Regime Detection
        adx, p_di, m_di = calculate_adx(df["high"], df["low"], close, 14)
        df["adx"] = adx
        df["plus_di"] = p_di
        df["minus_di"] = m_di

    # Relative Volume (RVOL)
    if "volume" in df.columns:
        df["rvol"] = calculate_rvol(df["volume"], 20)

    return df
