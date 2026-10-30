"""
Historical Data Downloader and Validator for Binance Spot Markets.
Downloads and validates historical klines from Binance API and data.binance.vision.
Caches cleaned data locally in CSV format.
"""

import os
import time
import json
import logging
import urllib.request
import urllib.error
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("backtest_data_loader")

TIMEFRAME_MS = {
    "1m": 60 * 1000,
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "4h": 4 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000
}


class BinanceDataLoader:
    def __init__(self, cache_dir: str = "backtest/data"):
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)

    def _format_symbol_for_api(self, symbol: str) -> str:
        return symbol.replace("/", "").upper()

    def fetch_klines_rest(
        self,
        symbol: str,
        timeframe: str,
        start_time_ms: int,
        end_time_ms: int
    ) -> pd.DataFrame:
        """
        Download historical klines from Binance public REST API with pagination.
        Handles rate limits (0.05s pause) and joins bars up to end_time_ms.
        """
        api_symbol = self._format_symbol_for_api(symbol)
        all_bars = []
        current_start = start_time_ms
        limit = 1000
        interval_ms = TIMEFRAME_MS.get(timeframe, 60000)

        while current_start < end_time_ms:
            url = (
                f"https://api.binance.com/api/v3/klines?"
                f"symbol={api_symbol}&interval={timeframe}&startTime={current_start}&endTime={end_time_ms}&limit={limit}"
            )
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            try:
                with urllib.request.urlopen(req, timeout=12) as resp:
                    if resp.status != 200:
                        logger.error(f"HTTP {resp.status} for {symbol} at {current_start}")
                        break
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception as e:
                logger.error(f"Error fetching klines for {symbol} ({current_start}): {e}")
                time.sleep(1.0)
                continue

            if not data:
                break

            for k in data:
                all_bars.append({
                    "time": int(k[0] / 1000),  # unix timestamp in seconds
                    "time_ms": int(k[0]),
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                    "is_closed": True
                })

            last_bar_ms = int(data[-1][0])
            if last_bar_ms <= current_start or len(data) < limit:
                break
            current_start = last_bar_ms + interval_ms
            time.sleep(0.04)

        if not all_bars:
            return pd.DataFrame()

        df = pd.DataFrame(all_bars)
        return df

    def validate_and_clean_data(self, df: pd.DataFrame, timeframe: str, symbol: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Validate historical klines for gaps, duplicates, zero prices, and bad candles.
        Returns (cleaned_df, validation_report).
        """
        if df.empty:
            return df, {"symbol": symbol, "error": "Empty dataframe"}

        initial_count = len(df)
        report = {
            "symbol": symbol,
            "timeframe": timeframe,
            "initial_rows": initial_count,
            "duplicates_dropped": 0,
            "bad_candles_dropped": 0,
            "detected_gaps": 0,
            "final_rows": 0,
            "start_time": "",
            "end_time": ""
        }

        # 1. Drop duplicates by timestamp
        df = df.drop_duplicates(subset=["time"]).copy()
        report["duplicates_dropped"] = initial_count - len(df)

        # 2. Sort chronologically
        df = df.sort_values(by="time").reset_index(drop=True)

        # 3. Filter out invalid/corrupted candles:
        # high must be >= low, open/high/low/close must be > 0, volume >= 0
        valid_mask = (
            (df["high"] >= df["low"]) &
            (df["high"] >= df["open"]) &
            (df["high"] >= df["close"]) &
            (df["low"] <= df["open"]) &
            (df["low"] <= df["close"]) &
            (df["open"] > 0) &
            (df["close"] > 0) &
            (df["high"] > 0) &
            (df["low"] > 0) &
            (df["volume"] >= 0)
        )
        bad_count = int((~valid_mask).sum())
        if bad_count > 0:
            df = df[valid_mask].reset_index(drop=True)
            report["bad_candles_dropped"] = bad_count

        # 4. Check for gaps in timestamps
        interval_sec = TIMEFRAME_MS.get(timeframe, 60000) // 1000
        time_diffs = df["time"].diff()
        # Any gap strictly greater than 1 interval
        gaps = time_diffs[time_diffs > (interval_sec * 1.5)]
        report["detected_gaps"] = int(len(gaps))

        report["final_rows"] = len(df)
        if len(df) > 0:
            report["start_time"] = datetime.fromtimestamp(df.iloc[0]["time"], tz=timezone.utc).isoformat()
            report["end_time"] = datetime.fromtimestamp(df.iloc[-1]["time"], tz=timezone.utc).isoformat()

        return df, report

    def get_or_download_data(
        self,
        symbol: str,
        timeframe: str,
        start_time_ms: int,
        end_time_ms: int,
        force_refresh: bool = False
    ) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Retrieve data from local cache or download and validate from Binance.
        """
        safe_sym = symbol.replace("/", "_")
        cache_path = os.path.join(self.cache_dir, f"{safe_sym}_{timeframe}.csv")

        if os.path.exists(cache_path) and not force_refresh:
            try:
                df = pd.read_csv(cache_path)
                df, report = self.validate_and_clean_data(df, timeframe, symbol)
                # Verify cache covers the requested range
                if not df.empty and df.iloc[0]["time_ms"] <= start_time_ms and df.iloc[-1]["time_ms"] >= end_time_ms - TIMEFRAME_MS.get(timeframe, 60000) * 2:
                    return df, report
            except Exception as e:
                logger.warning(f"Error reading cache {cache_path}: {e}")

        # Download from REST API
        raw_df = self.fetch_klines_rest(symbol, timeframe, start_time_ms, end_time_ms)
        clean_df, report = self.validate_and_clean_data(raw_df, timeframe, symbol)

        if not clean_df.empty:
            clean_df.to_csv(cache_path, index=False)

        return clean_df, report

