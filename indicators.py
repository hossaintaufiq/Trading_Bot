"""
Technical Indicators Engine for Binance Trading Bot.
High-speed vectorized computations using NumPy and Pandas.
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


def calculate_bollinger_bands(
    series: pd.Series, period: int = 20, std_dev: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """Calculate Bollinger Bands (Upper, Middle, Lower)."""
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    return upper, middle, lower


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

    # Volatility
    upper, mid, lower = calculate_bollinger_bands(close, bb_period, bb_std)
    df["bb_upper"] = upper
    df["bb_middle"] = mid
    df["bb_lower"] = lower

    # MACD
    macd, macd_sig, macd_hist = calculate_macd(close)
    df["macd"] = macd
    df["macd_signal"] = macd_sig
    df["macd_hist"] = macd_hist

    # ATR
    if "high" in df.columns and "low" in df.columns:
        df["atr"] = calculate_atr(df["high"], df["low"], close, 14)

    return df
