#!/usr/bin/env python3
"""
NEPTUNE — Milestone 4.3 Historical Data Expansion CLI (`backfill_history.py`)

Safe, resumable, rate-limit-aware historical market data ingestion:
- Assets: BTCUSDT, ETHUSDT, BNBUSDT
- Timeframes: 15m, 1h, 4h
- Paginates Binance public REST API and saves into Parquet partitions.
"""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.data.market.backfill import HistoricalDataBackfiller


async def main():
    print("=" * 80)
    print("NEPTUNE — HISTORICAL DATA EXPANSION (BINANCE PUBLIC REST)")
    print("=" * 80)

    # Configuration for deep research dataset:
    # 4h: 3,000 candles (~500 days)
    # 1h: 5,000 candles (~208 days)
    # 15m: 5,000 candles (~52 days)
    targets = {
        "4h": 3000,
        "1h": 5000,
        "15m": 5000,
    }
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]

    backfiller = HistoricalDataBackfiller(rate_limit_delay_seconds=0.15)
    t_start = time.time()
    results = []

    for sym in symbols:
        for tf, target_cnt in targets.items():
            print(f"\n>>> Ingesting {sym} [{tf}] (Target: {target_cnt} closed candles)...")
            res = await backfiller.backfill_target_depth(
                symbol=sym,
                timeframe=tf,
                target_candles=target_cnt,
                batch_size=1000,
            )
            results.append(res)
            print(f"    Status: {res.status} | Stored: {res.total_stored_candles} | Added: {res.candles_saved} | Range: {res.earliest_timestamp} -> {res.latest_timestamp} ({res.elapsed_seconds}s)")

    print("\n" + "=" * 80)
    print("DATA EXPANSION SUMMARY")
    print("=" * 80)
    print(f"{'SYMBOL':<10} {'TF':<5} {'STORED':<8} {'FETCHED':<8} {'EARLIEST (UTC)':<28} {'LATEST (UTC)':<28} {'STATUS':<10}")
    print("-" * 100)
    for r in results:
        print(f"{r.symbol:<10} {r.timeframe:<5} {r.total_stored_candles:<8} {r.candles_fetched:<8} {r.earliest_timestamp:<28} {r.latest_timestamp:<28} {r.status:<10}")

    total_bars = sum(r.total_stored_candles for r in results)
    print("-" * 100)
    print(f"Total Closed Historical Candles Available: {total_bars:,} across 9 datasets in {time.time() - t_start:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())

