"""
Binance Historical Data Downloader & Survivorship Audit for Proposal A.
Downloads 1d and 4h historical klines from 2019-01-01 to 2026-10-30 for 17 liquid spot symbols.
Audits date ranges, detects late-listing dates (survivorship bias analysis), and validates data integrity.
"""

import os
import sys
import time
import json
import urllib.request
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List

sys.path.insert(0, os.getcwd())

SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT",
    "DOGE/USDT", "SOL/USDT", "TRX/USDT", "LTC/USDT", "LINK/USDT",
    "AVAX/USDT", "DOT/USDT", "MATIC/USDT", "NEAR/USDT", "ATOM/USDT",
    "UNI/USDT", "SUI/USDT"
]

TIMEFRAMES = ["1d", "4h"]
START_TIME_MS = int(datetime(2019, 1, 1, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
END_TIME_MS = int(datetime(2026, 10, 30, 0, 0, tzinfo=timezone.utc).timestamp() * 1000)
CACHE_DIR = "backtest/data/proposal_a"


def download_klines(symbol: str, timeframe: str) -> pd.DataFrame:
    api_sym = symbol.replace("/", "").upper()
    interval_ms = (24 * 3600 * 1000) if timeframe == "1d" else (4 * 3600 * 1000)
    current_start = START_TIME_MS
    all_bars = []
    limit = 1000

    while current_start < END_TIME_MS:
        url = (
            f"https://api.binance.com/api/v3/klines?"
            f"symbol={api_sym}&interval={timeframe}&startTime={current_start}&endTime={END_TIME_MS}&limit={limit}"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status != 200:
                    print(f"[{symbol} {timeframe}] HTTP {resp.status}")
                    break
                raw = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            # If symbol not found or network glitch, retry once
            time.sleep(1.0)
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw = json.loads(resp.read().decode("utf-8"))
            except Exception as e2:
                print(f"[{symbol} {timeframe}] Fetch error: {e2}")
                break

        if not raw:
            break

        for k in raw:
            all_bars.append({
                "time": int(k[0] / 1000),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5])
            })

        last_ms = int(raw[-1][0])
        if last_ms <= current_start or len(raw) < limit:
            break
        current_start = last_ms + interval_ms
        time.sleep(0.04)

    if not all_bars:
        return pd.DataFrame()

    df = pd.DataFrame(all_bars)
    df.drop_duplicates(subset=["time"], inplace=True)
    df.sort_values(by="time", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df


def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    audit_records = []

    print("=" * 80)
    print("PROPOSAL A HISTORICAL DATA INGESTION & SURVIVORSHIP AUDIT")
    print("=" * 80)

    for tf in TIMEFRAMES:
        print(f"\n--- Downloading Timeframe: {tf} ---")
        for sym in SYMBOLS:
            safe_sym = sym.replace("/", "_")
            out_path = os.path.join(CACHE_DIR, f"{safe_sym}_{tf}.csv")
            
            if os.path.exists(out_path):
                df = pd.read_csv(out_path)
            else:
                print(f"Downloading {sym} ({tf})...", end=" ", flush=True)
                df = download_klines(sym, tf)
                if not df.empty:
                    df.to_csv(out_path, index=False)
                    print(f"Saved {len(df)} bars.")
                else:
                    print("FAILED / NO DATA.")

            if not df.empty:
                t_first = datetime.fromtimestamp(df["time"].iloc[0], tz=timezone.utc)
                t_last = datetime.fromtimestamp(df["time"].iloc[-1], tz=timezone.utc)
                is_full = t_first <= datetime(2019, 1, 5, tzinfo=timezone.utc)
                
                audit_records.append({
                    "symbol": sym,
                    "timeframe": tf,
                    "bars": len(df),
                    "first_bar": t_first.strftime("%Y-%m-%d"),
                    "last_bar": t_last.strftime("%Y-%m-%d"),
                    "full_period": "YES (Full 2019-2026)" if is_full else f"NO (Listed {t_first.strftime('%Y-%m-%d')})"
                })

    df_audit = pd.DataFrame(audit_records)
    audit_csv = os.path.join(CACHE_DIR, "data_survivorship_audit.csv")
    df_audit.to_csv(audit_csv, index=False)
    print("\n" + "=" * 80)
    print("DATA AUDIT SUMMARY TABLE")
    print("=" * 80)
    print(df_audit.to_string(index=False))
    print("=" * 80)


if __name__ == "__main__":
    main()
