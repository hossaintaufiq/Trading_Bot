"""
NEPTUNE — Milestone 2.1 Live Market Data Integration Verification Script

Executes live read-only verification against public Binance endpoints:
- Test 1: Public REST connectivity across BTCUSDT, ETHUSDT, BNBUSDT on 15m, 1h, 4h.
  Includes pagination test spanning multiple 1,000-candle pages.
- Test 2: Public WebSocket connectivity with live tick reception, open/closed tracking,
  and simulated disconnection recovery.
- Test 3: Persistence and recovery via Parquet, duplicate prevention, gap detection,
  and cache-first backfill verification.
- Test 4: Data quality invariants (OHLC bounds, non-negative volume, chronological ordering,
  no future timestamps, no incomplete candles in closed buffers).
"""
import asyncio
import os
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

import pandas as pd
import structlog

from app.data.market.binance_client import BinancePublicClient
from app.data.market.validator import CandleValidator, ValidatedCandle
from app.data.repositories.parquet_repo import ParquetMarketDataRepository
from app.data.market.service import MarketDataService

logger = structlog.get_logger(__name__)


async def run_test_1_rest():
    print("\n" + "=" * 60)
    print("TEST 1: PUBLIC REST CONNECTIVITY")
    print("=" * 60)
    client = BinancePublicClient()
    validator = CandleValidator()
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    timeframes = ["15m", "1h", "4h"]

    rest_results = {}

    for sym in symbols:
        for tf in timeframes:
            print(f"Fetching {sym} {tf} (limit 50)...", end=" ")
            klines = await client.fetch_klines(sym, tf, limit=50)
            assert len(klines) == 50, f"Expected 50 candles, got {len(klines)}"

            # Validate each candle
            for k in klines:
                vc, issues = validator.validate_candle(k, require_closed=True)
                assert vc is not None, f"Validation failed: {issues}"

            # Validate sequence (ordering & gaps)
            validated = [validator.validate_candle(k)[0] for k in klines]
            seq, seq_issues = validator.validate_sequence(validated, timeframe=tf)
            assert len(seq) == 50, f"Sequence issue in {sym} {tf}: {seq_issues}"

            first_dt = klines[0]["timestamp"]
            last_dt = klines[-1]["timestamp"]
            latest_close = klines[-1]["close"]
            print(f"[OK] 50 candles ({first_dt} -> {last_dt}), latest close: {latest_close}")
            rest_results[f"{sym}_{tf}"] = {
                "count": len(klines),
                "first": first_dt,
                "last": last_dt,
                "close": latest_close,
            }

    # Pagination test: request 1,200 candles for BTCUSDT 15m (spans 2 pages across 1000 limit)
    print("\nTesting REST Pagination (BTCUSDT 15m, requested: 1,200 candles)...", end=" ")
    # Compute start time ~1250 candles ago (1250 * 15 * 60 * 1000 ms)
    start_ms = int((time.time() - (1250 * 15 * 60)) * 1000)
    paginated = await client.fetch_klines_paginated(
        symbol="BTCUSDT",
        interval="15m",
        start_time=start_ms,
        total_limit=1200,
        page_size=1000,
    )
    assert len(paginated) == 1200, f"Expected 1200 paginated candles, got {len(paginated)}"

    # Check timestamps strictly strictly increasing
    prev_dt = None
    for c in paginated:
        curr_dt = datetime.fromisoformat(c["timestamp"].replace("Z", "+00:00"))
        if prev_dt:
            assert curr_dt > prev_dt, f"Non-chronological timestamp: {curr_dt} <= {prev_dt}"
        prev_dt = curr_dt

    print(f"[OK] Fetched {len(paginated)} candles across 2 pages seamlessly!")
    print(f"      Range: {paginated[0]['timestamp']} -> {paginated[-1]['timestamp']}")

    return rest_results, len(paginated)


async def run_test_2_websocket():
    print("\n" + "=" * 60)
    print("TEST 2: PUBLIC WEBSOCKET CONNECTIVITY")
    print("=" * 60)
    client = BinancePublicClient()
    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    timeframes = ["15m", "1h", "4h"]

    received_events: List[Dict[str, Any]] = []
    seen_symbols = set()
    seen_timeframes = set()
    open_count = 0
    closed_count = 0

    async def on_candle(candle: Dict[str, Any]):
        nonlocal open_count, closed_count
        received_events.append(candle)
        seen_symbols.add(candle["symbol"])
        seen_timeframes.add(candle["timeframe"])
        if candle["is_closed"]:
            closed_count += 1
        else:
            open_count += 1

    client.add_candle_listener(on_candle)

    # Start WS stream in background task
    print(f"Connecting to Binance combined kline stream for {symbols} across {timeframes}...")
    stream_task = asyncio.create_task(client.start_kline_stream(symbols, timeframes))

    # Wait for initial events (allow up to 25 seconds for connection & ticks)
    print("Observing live stream (waiting for events, up to 25s)...", end=" ", flush=True)
    wait_start = time.time()
    while len(received_events) < 5 and (time.time() - wait_start) < 25.0:
        await asyncio.sleep(0.5)
    print(f"[OK] Received {len(received_events)} live events!")

    assert len(received_events) > 0, "No WebSocket events received within 25 seconds"
    print(f"      Symbols observed: {sorted(list(seen_symbols))}")
    print(f"      Timeframes observed: {sorted(list(seen_timeframes))}")
    print(f"      In-progress (open) ticks: {open_count}, Closed candles: {closed_count}")

    # Inspect first few events for correctness
    sample = received_events[0]
    assert sample["symbol"] in symbols
    assert sample["timeframe"] in timeframes
    assert "Z" in sample["timestamp"]
    assert sample["open"] > 0
    assert sample["high"] >= sample["low"]

    # Test simulated disconnection and reconnection
    print("Testing simulated disconnection recovery...")
    # Force stop client and restart
    await client.stop()
    assert not client._ws_running
    stream_task.cancel()
    try:
        await stream_task
    except asyncio.CancelledError:
        pass

    events_before_reconnect = len(received_events)
    print(f"      WebSocket halted. Restarting stream...")
    reconnect_task = asyncio.create_task(client.start_kline_stream(["BTCUSDT"], ["15m"]))
    
    reconnect_start = time.time()
    while (len(received_events) - events_before_reconnect) < 2 and (time.time() - reconnect_start) < 20.0:
        await asyncio.sleep(0.5)

    events_after_reconnect = len(received_events)
    new_events = events_after_reconnect - events_before_reconnect
    print(f"[OK] Reconnected and received {new_events} new events post-reconnection!")
    assert new_events > 0, "Failed to receive events after reconnection"

    await client.stop()
    reconnect_task.cancel()
    try:
        await reconnect_task
    except asyncio.CancelledError:
        pass

    return len(received_events), list(seen_symbols), open_count, closed_count


async def run_test_3_persistence_recovery():
    print("\n" + "=" * 60)
    print("TEST 3: PERSISTENCE AND RECOVERY")
    print("=" * 60)

    temp_storage = tempfile.mkdtemp(prefix="neptune_recovery_test_")
    repo = ParquetMarketDataRepository(base_dir=temp_storage)
    client = BinancePublicClient()

    # 1. Fetch live historical candles and persist
    print("Step 1: Fetching and persisting 100 closed BTCUSDT 15m candles...", end=" ")
    raw_klines = await client.fetch_klines("BTCUSDT", "15m", limit=100)
    df = pd.DataFrame([{
        "timestamp": k["timestamp"],
        "open": k["open"],
        "high": k["high"],
        "low": k["low"],
        "close": k["close"],
        "volume": k["volume"],
        "quote_volume": k.get("quote_volume", 0.0),
        "trades_count": k.get("trades_count", 0),
    } for k in raw_klines])

    saved_count = await repo.save_candles("BTCUSDT", "15m", df)
    print(f"[OK] Saved {saved_count} candles to Parquet.")

    # 2. Simulate shutdown & restart
    print("Step 2: Simulating backend shutdown and fresh cold restart...", end=" ")
    del repo
    # Restart repository pointing to same directory
    restarted_repo = ParquetMarketDataRepository(base_dir=temp_storage)
    loaded_df = await restarted_repo.load_candles("BTCUSDT", "15m", limit=200)
    assert len(loaded_df) == 100, f"Expected 100 recovered candles, found {len(loaded_df)}"
    assert loaded_df.iloc[0]["timestamp"] == raw_klines[0]["timestamp"]
    assert loaded_df.iloc[-1]["timestamp"] == raw_klines[-1]["timestamp"]
    print(f"[OK] Successfully recovered 100 candles intact!")

    # 3. Duplicate prevention test
    print("Step 3: Appending duplicate candles to test deduplication...", end=" ")
    dup_saved = await restarted_repo.save_candles("BTCUSDT", "15m", df)
    reloaded_df = await restarted_repo.load_candles("BTCUSDT", "15m", limit=200)
    assert len(reloaded_df) == 100, f"Expected 100 unique candles after duplicate append, got {len(reloaded_df)}"
    print(f"[OK] Deduplication verified: exactly {len(reloaded_df)} candles remain.")

    # 4. Gap detection test
    print("Step 4: Testing sequence gap detection...", end=" ")
    validator = CandleValidator()
    # Take candles 0..10, skip 11..13, take 14..20
    gap_sample = [
        ValidatedCandle(
            symbol="BTCUSDT", timeframe="15m",
            timestamp=r["timestamp"], open=r["open"], high=r["high"],
            low=r["low"], close=r["close"], volume=r["volume"]
        )
        for _, r in loaded_df.iloc[list(range(10)) + list(range(14, 20))].iterrows()
    ]
    _, gap_issues = validator.validate_sequence(gap_sample, timeframe="15m")
    gap_detected = any(i.field == "missing_candles_gap" for i in gap_issues)
    assert gap_detected, "Failed to detect sequence gap"
    print(f"[OK] Sequence gap detected successfully ({len(gap_issues)} issue flags).")

    # 5. Cache-first backfill behavior test
    print("Step 5: Testing cache-first service initialization...", end=" ")
    mock_client = BinancePublicClient()
    service = MarketDataService(
        client=mock_client,
        repository=restarted_repo,
        symbols=["BTCUSDT"],
        timeframes=["15m"]
    )
    # The stored candles are very recent, so service initialization should load them directly
    await service.initialize()
    cached = service.get_candles("BTCUSDT", "15m", limit=100)
    assert len(cached) == 100, f"Expected 100 cached candles in memory, got {len(cached)}"
    print(f"[OK] Memory buffer populated with {len(cached)} candles via cache-first loader.")

    shutil.rmtree(temp_storage, ignore_errors=True)
    return True


async def run_test_4_data_quality():
    print("\n" + "=" * 60)
    print("TEST 4: DATA QUALITY AND INVARIANTS")
    print("=" * 60)
    client = BinancePublicClient()
    validator = CandleValidator()
    now_utc = datetime.now(timezone.utc)

    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    total_checked = 0

    for sym in symbols:
        klines = await client.fetch_klines(sym, "15m", limit=100)
        total_checked += len(klines)

        timestamps = set()
        for k in klines:
            # 1. Prices > 0
            assert k["open"] > 0 and k["high"] > 0 and k["low"] > 0 and k["close"] > 0
            # 2. Volume >= 0
            assert k["volume"] >= 0 and k["quote_volume"] >= 0
            # 3. Mathematical invariants
            assert k["high"] >= k["low"], f"High < Low: {k}"
            assert k["high"] >= max(k["open"], k["close"]), f"High < max(O,C): {k}"
            assert k["low"] <= min(k["open"], k["close"]), f"Low > min(O,C): {k}"
            # 4. No future timestamps
            k_dt = datetime.fromisoformat(k["timestamp"].replace("Z", "+00:00"))
            assert k_dt <= now_utc + timedelta(minutes=1), f"Future timestamp detected: {k_dt} > {now_utc}"
            # 5. No duplicates in batch
            assert k["timestamp"] not in timestamps, f"Duplicate timestamp in batch: {k['timestamp']}"
            timestamps.add(k["timestamp"])

            # 6. Test validator rejects incomplete candles when require_closed=True
            incomplete_k = dict(k)
            incomplete_k["is_closed"] = False
            vc_inc, issues = validator.validate_candle(incomplete_k, require_closed=True)
            assert vc_inc is None
            assert any(i.field == "is_closed" for i in issues)

    print(f"[OK] Verified data quality invariants across {total_checked} live exchange candles!")
    print(f"      - Zero negative prices")
    print(f"      - Zero negative volume")
    print(f"      - 100% OHLC mathematical consistency (High >= Max(O,C), Low <= Min(O,C))")
    print(f"      - Zero future timestamps")
    print(f"      - Zero duplicates")
    print(f"      - Incomplete candles strictly rejected when require_closed=True")

    return total_checked


async def main():
    print("STARTING NEPTUNE MILESTONE 2.1 LIVE INTEGRATION VERIFICATION")
    print(f"Local Time: {datetime.now().isoformat()} | UTC: {datetime.now(timezone.utc).isoformat()}")

    t1_results, paginated_count = await run_test_1_rest()
    t2_count, t2_syms, t2_open, t2_closed = await run_test_2_websocket()
    t3_status = await run_test_3_persistence_recovery()
    t4_checked = await run_test_4_data_quality()

    print("\n" + "=" * 60)
    print("ALL LIVE INTEGRATION TESTS COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
