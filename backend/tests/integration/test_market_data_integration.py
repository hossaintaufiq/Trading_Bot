"""
NEPTUNE — Milestone 2.1 Market Data Integration Tests

Fully automated integration tests using mocked exchange responses:
1. REST pagination across batch limits.
2. WebSocket event parsing.
3. Closed candle routing vs open tick buffer.
4. WebSocket reconnection with exponential backoff on disconnect.
5. Parquet persistence and cold-restart recovery.
6. Deduplication on append.
7. Sequence gap / missing candle detection.
8. Cache-first backfill behavior.

Zero live network dependencies. All tests pass offline.
"""
import asyncio
import json
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
import websockets

from app.data.market.binance_client import BinancePublicClient, BinanceRateLimitError
from app.data.market.service import MarketDataService
from app.data.market.validator import CandleValidator, ValidatedCandle
from app.data.repositories.parquet_repo import ParquetMarketDataRepository


# ============================================================
# 1. REST PAGINATION TEST
# ============================================================

@pytest.mark.asyncio
async def test_rest_pagination_multi_page():
    """Verify fetch_klines_paginated handles multi-page batch retrieval."""
    client = BinancePublicClient()

    base_time_ms = 1730419200000  # 2024-11-01 00:00:00 UTC
    step_ms = 15 * 60 * 1000      # 15m

    # Create mock page 1 (1,000 candles) and page 2 (200 candles)
    def generate_candles(start_ms: int, count: int) -> List[Dict[str, Any]]:
        candles = []
        for i in range(count):
            t = start_ms + (i * step_ms)
            dt = datetime.fromtimestamp(t / 1000.0, tz=timezone.utc)
            candles.append({
                "symbol": "BTCUSDT",
                "timeframe": "15m",
                "timestamp": dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "open": 65000.0 + i,
                "high": 65100.0 + i,
                "low": 64900.0 + i,
                "close": 65050.0 + i,
                "volume": 10.0,
                "quote_volume": 650000.0,
                "trades_count": 100,
                "is_closed": True,
            })
        return candles

    page1 = generate_candles(base_time_ms, 1000)
    page2_start = base_time_ms + (1000 * step_ms)
    page2 = generate_candles(page2_start, 200)

    call_count = 0

    async def mock_fetch_klines(symbol, interval, start_time=None, end_time=None, limit=1000):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return page1
        elif call_count == 2:
            return page2
        return []

    client.fetch_klines = AsyncMock(side_effect=mock_fetch_klines)

    result = await client.fetch_klines_paginated(
        symbol="BTCUSDT",
        interval="15m",
        start_time=base_time_ms,
        total_limit=1200,
        page_size=1000,
    )

    assert len(result) == 1200
    assert call_count == 2
    assert result[0]["timestamp"] == page1[0]["timestamp"]
    assert result[999]["timestamp"] == page1[-1]["timestamp"]
    assert result[1000]["timestamp"] == page2[0]["timestamp"]
    assert result[-1]["timestamp"] == page2[-1]["timestamp"]


# ============================================================
# 2. WEBSOCKET EVENT PARSING TEST
# ============================================================

def test_websocket_event_parsing():
    """Verify WebSocket kline event parsing converts raw payload to normalized format."""
    client = BinancePublicClient()

    raw_kline = {
        "t": 1730419200000,
        "T": 1730420099999,
        "s": "BTCUSDT",
        "i": "15m",
        "f": 100,
        "L": 200,
        "o": "68120.50",
        "c": "68340.00",
        "h": "68400.00",
        "l": "68100.00",
        "v": "45.123",
        "n": 1500,
        "x": False,
        "q": "3080000.0",
        "V": "22.5",
        "Q": "1540000.0",
        "B": "0",
    }

    parsed = client._parse_ws_kline(raw_kline)

    assert parsed["symbol"] == "BTCUSDT"
    assert parsed["timeframe"] == "15m"
    assert parsed["timestamp"] == "2024-11-01T00:00:00.000Z"
    assert parsed["open"] == 68120.50
    assert parsed["high"] == 68400.00
    assert parsed["low"] == 68100.00
    assert parsed["close"] == 68340.00
    assert parsed["volume"] == 45.123
    assert parsed["quote_volume"] == 3080000.0
    assert parsed["trades_count"] == 1500
    assert parsed["is_closed"] is False


# ============================================================
# 3. CLOSED CANDLE ROUTING TEST
# ============================================================

@pytest.mark.asyncio
async def test_closed_candle_routing():
    """Verify open ticks update current candle only, while closed candles route to subscribers."""
    repo = AsyncMock()
    mock_client = MagicMock()
    service = MarketDataService(client=mock_client, repository=repo, symbols=["BTCUSDT"], timeframes=["15m"])

    routed_closed_candles: List[ValidatedCandle] = []

    async def closed_subscriber(candle: ValidatedCandle):
        routed_closed_candles.append(candle)

    service.subscribe_closed_candles(closed_subscriber)

    # 1. Dispatch in-progress tick (is_closed = False)
    tick1 = {
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "timestamp": "2026-11-01T20:00:00.000Z",
        "open": 65000.0,
        "high": 65200.0,
        "low": 64900.0,
        "close": 65150.0,
        "volume": 12.0,
        "is_closed": False,
    }
    await service._handle_live_candle(tick1)

    # Open tick should NOT route to subscriber, but SHOULD update current candle
    assert len(routed_closed_candles) == 0
    current = service.get_current_candle("BTCUSDT", "15m")
    assert current is not None
    assert current.close == 65150.0
    assert current.is_closed is False
    assert len(service.get_candles("BTCUSDT", "15m")) == 0

    # 2. Dispatch closing tick (is_closed = True)
    tick2 = {
        "symbol": "BTCUSDT",
        "timeframe": "15m",
        "timestamp": "2026-11-01T20:00:00.000Z",
        "open": 65000.0,
        "high": 65300.0,
        "low": 64900.0,
        "close": 65250.0,
        "volume": 25.0,
        "is_closed": True,
    }
    await service._handle_live_candle(tick2)

    # Closed candle MUST route to subscriber and enter closed candle buffer
    assert len(routed_closed_candles) == 1
    assert routed_closed_candles[0].close == 65250.0
    assert routed_closed_candles[0].is_closed is True

    cached = service.get_candles("BTCUSDT", "15m")
    assert len(cached) == 1
    assert cached[0].close == 65250.0


# ============================================================
# 4. WEBSOCKET RECONNECTION TEST
# ============================================================

@pytest.mark.asyncio
async def test_websocket_reconnection_after_disconnect():
    """Verify client reconnects automatically when WebSocket connection closes."""
    client = BinancePublicClient()

    connection_attempts = 0
    received_candles = []

    async def mock_listener(c):
        received_candles.append(c)

    client.add_candle_listener(mock_listener)

    # Mock websockets.connect to succeed once, drop, then succeed again
    class MockWS:
        def __init__(self, fail_first=False):
            self.fail_first = fail_first
            self.msg_count = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

        async def recv(self):
            await asyncio.sleep(0.02)
            self.msg_count += 1
            if self.fail_first and self.msg_count == 1:
                # Deliver one message and drop
                payload = {
                    "stream": "btcusdt@kline_15m",
                    "data": {
                        "k": {
                            "t": 1730419200000, "T": 1730420099999, "s": "BTCUSDT",
                            "i": "15m", "o": "65000", "c": "65100", "h": "65200",
                            "l": "64900", "v": "10", "q": "650000", "n": 50, "x": False
                        }
                    }
                }
                return json.dumps(payload)
            elif self.fail_first and self.msg_count == 2:
                raise websockets.ConnectionClosed(None, None)
            else:
                # Second connection message
                payload = {
                    "stream": "btcusdt@kline_15m",
                    "data": {
                        "k": {
                            "t": 1730420100000, "T": 1730420999999, "s": "BTCUSDT",
                            "i": "15m", "o": "65100", "c": "65200", "h": "65300",
                            "l": "65000", "v": "12", "q": "780000", "n": 60, "x": False
                        }
                    }
                }
                return json.dumps(payload)

    def mock_connect_factory(*args, **kwargs):
        nonlocal connection_attempts
        connection_attempts += 1
        if connection_attempts == 1:
            return MockWS(fail_first=True)
        return MockWS(fail_first=False)

    with patch("websockets.connect", side_effect=mock_connect_factory):
        # Start stream in background
        stream_task = asyncio.create_task(client.start_kline_stream(["BTCUSDT"], ["15m"]))

        # Wait for reconnection cycle to occur
        for _ in range(50):
            if connection_attempts >= 2 and len(received_candles) >= 2:
                break
            await asyncio.sleep(0.05)

        await client.stop()
        stream_task.cancel()
        try:
            await stream_task
        except asyncio.CancelledError:
            pass

    assert connection_attempts >= 2
    assert len(received_candles) >= 2


# ============================================================
# 5. PERSISTENCE AND RECOVERY TEST
# ============================================================

@pytest.mark.asyncio
async def test_persistence_and_recovery():
    """Verify saved Parquet candles are recovered exactly after backend restart."""
    temp_dir = tempfile.mkdtemp(prefix="neptune_recovery_test_")

    repo1 = ParquetMarketDataRepository(base_dir=temp_dir)
    candles_df = pd.DataFrame([
        {
            "timestamp": f"2026-11-01T{10+i:02d}:00:00.000Z",
            "open": 65000.0 + i,
            "high": 65100.0 + i,
            "low": 64900.0 + i,
            "close": 65050.0 + i,
            "volume": 100.0,
            "quote_volume": 6500000.0,
            "trades_count": 500,
        }
        for i in range(5)
    ])
    await repo1.save_candles("BTCUSDT", "1h", candles_df)

    # Cold shutdown
    del repo1

    # Restart
    repo2 = ParquetMarketDataRepository(base_dir=temp_dir)
    recovered = await repo2.load_candles("BTCUSDT", "1h")

    assert len(recovered) == 5
    assert recovered.iloc[0]["timestamp"] == "2026-11-01T10:00:00.000Z"
    assert recovered.iloc[-1]["timestamp"] == "2026-11-01T14:00:00.000Z"
    assert recovered.iloc[0]["close"] == 65050.0
    assert recovered.iloc[-1]["close"] == 65054.0

    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================
# 6. DUPLICATE PREVENTION TEST
# ============================================================

@pytest.mark.asyncio
async def test_duplicate_prevention_on_append():
    """Verify appending identical candles does not produce duplicates in storage."""
    temp_dir = tempfile.mkdtemp(prefix="neptune_dedup_test_")
    repo = ParquetMarketDataRepository(base_dir=temp_dir)

    df1 = pd.DataFrame([
        {"timestamp": "2026-11-01T12:00:00.000Z", "open": 10.0, "high": 12.0, "low": 9.0, "close": 11.0, "volume": 100.0},
        {"timestamp": "2026-11-01T12:15:00.000Z", "open": 11.0, "high": 13.0, "low": 10.0, "close": 12.0, "volume": 120.0},
    ])
    await repo.save_candles("BTCUSDT", "15m", df1)

    # Append overlapping data (second candle identical, third new)
    df2 = pd.DataFrame([
        {"timestamp": "2026-11-01T12:15:00.000Z", "open": 11.0, "high": 13.0, "low": 10.0, "close": 12.0, "volume": 120.0},
        {"timestamp": "2026-11-01T12:30:00.000Z", "open": 12.0, "high": 14.0, "low": 11.0, "close": 13.0, "volume": 130.0},
    ])
    await repo.save_candles("BTCUSDT", "15m", df2)

    result = await repo.load_candles("BTCUSDT", "15m")
    assert len(result) == 3
    assert list(result["timestamp"]) == [
        "2026-11-01T12:00:00.000Z",
        "2026-11-01T12:15:00.000Z",
        "2026-11-01T12:30:00.000Z",
    ]

    shutil.rmtree(temp_dir, ignore_errors=True)


# ============================================================
# 7. MISSING CANDLE / SEQUENCE GAP HANDLING TEST
# ============================================================

def test_missing_candle_gap_handling():
    """Verify sequence validation flags missing candles when intervals have gaps."""
    validator = CandleValidator()

    candles = [
        ValidatedCandle(symbol="BTCUSDT", timeframe="15m", timestamp="2026-11-01T12:00:00.000Z",
                        open=10, high=12, low=9, close=11, volume=50),
        # Gap: 12:15 and 12:30 are missing
        ValidatedCandle(symbol="BTCUSDT", timeframe="15m", timestamp="2026-11-01T12:45:00.000Z",
                        open=11, high=13, low=10, close=12, volume=60),
    ]

    valid_seq, issues = validator.validate_sequence(candles, timeframe="15m")

    assert len(valid_seq) == 2
    gap_issues = [i for i in issues if i.field == "missing_candles_gap"]
    assert len(gap_issues) == 1
    assert "2 missing candles" in gap_issues[0].message


# ============================================================
# 8. CACHE-FIRST BEHAVIOR TEST
# ============================================================

@pytest.mark.asyncio
async def test_cache_first_behavior_skips_network():
    """Verify cache-first backfill skips REST request when local storage is fresh."""
    temp_dir = tempfile.mkdtemp(prefix="neptune_cache_first_test_")
    repo = ParquetMarketDataRepository(base_dir=temp_dir)
    mock_client = MagicMock()
    mock_client.fetch_klines = AsyncMock()

    # Pre-seed repository with a recent candle
    recent_time = datetime.now(timezone.utc) - timedelta(minutes=4)
    df = pd.DataFrame([{
        "timestamp": recent_time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "open": 65000.0, "high": 65200.0, "low": 64900.0, "close": 65100.0, "volume": 10.0
    }])
    await repo.save_candles("BTCUSDT", "15m", df)

    service = MarketDataService(
        client=mock_client,
        repository=repo,
        symbols=["BTCUSDT"],
        timeframes=["15m"]
    )
    await service.initialize()

    # Zero REST calls should be executed
    mock_client.fetch_klines.assert_not_called()

    candles = service.get_candles("BTCUSDT", "15m")
    assert len(candles) == 1
    assert candles[0].close == 65100.0

    shutil.rmtree(temp_dir, ignore_errors=True)

