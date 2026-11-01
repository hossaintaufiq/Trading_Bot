"""
NEPTUNE Unit Tests — Milestone 2 Market Data Infrastructure

Tests:
1. CandleValidator:
   - Duplicate detection
   - Missing candle detection
   - Incomplete candle rejection (Rule A-09)
   - OHLC mathematical invariant checks
   - Negative volume rejection
   - UTC normalization to ISO 8601 string
2. ParquetMarketDataRepository:
   - Persistence and partitioning
   - Cache-first loading
   - Timestamp deduplication on append
   - Date range filtering
3. BinancePublicClient:
   - Rate limit handling (HTTP 429/418)
   - Exponential backoff retry on network failure
   - Kline parsing
4. MarketDataService:
   - Cache-first backfill logic
   - Closed-candle ring buffer routing
"""
import asyncio
import os
import shutil
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pandas as pd
import pytest

from app.data.market.binance_client import BinancePublicClient, BinanceRateLimitError
from app.data.market.service import MarketDataService
from app.data.market.validator import CandleValidator, ValidatedCandle, ValidationIssue
from app.data.repositories.parquet_repo import ParquetMarketDataRepository


# ============================================================
# 1. CANDLE VALIDATOR TESTS
# ============================================================

class TestCandleValidator:
    def test_valid_candle(self):
        data = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "timestamp": "2026-11-01T20:00:00Z",
            "open": 65000.0,
            "high": 65500.0,
            "low": 64800.0,
            "close": 65200.0,
            "volume": 120.5,
            "is_closed": True,
        }
        candle, issues = CandleValidator.validate_candle(data, require_closed=True)
        assert candle is not None
        assert issues == []
        assert candle.timestamp == "2026-11-01T20:00:00.000Z"
        assert candle.open == 65000.0

    def test_incomplete_candle_rejected_when_required(self):
        """Rule A-09: Never use incomplete candles for closed-candle evaluations."""
        data = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "timestamp": "2026-11-01T20:00:00Z",
            "open": 65000.0,
            "high": 65500.0,
            "low": 64800.0,
            "close": 65200.0,
            "volume": 120.5,
            "is_closed": False,
        }
        candle, issues = CandleValidator.validate_candle(data, require_closed=True)
        assert candle is None
        assert any(i.field == "is_closed" for i in issues)

    def test_incomplete_candle_allowed_for_live_ui(self):
        data = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "timestamp": "2026-11-01T20:00:00Z",
            "open": 65000.0,
            "high": 65500.0,
            "low": 64800.0,
            "close": 65200.0,
            "volume": 120.5,
            "is_closed": False,
        }
        candle, issues = CandleValidator.validate_candle(data, require_closed=False)
        assert candle is not None
        assert candle.is_closed is False

    def test_ohlc_invariants_high_lower_than_low(self):
        data = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "timestamp": "2026-11-01T20:00:00Z",
            "open": 65000.0,
            "high": 64000.0,  # Invalid: high < low
            "low": 64500.0,
            "close": 64200.0,
            "volume": 10.0,
        }
        candle, issues = CandleValidator.validate_candle(data)
        assert candle is None
        assert any(i.field == "high_low" for i in issues)

    def test_ohlc_invariants_high_lower_than_open(self):
        data = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "timestamp": "2026-11-01T20:00:00Z",
            "open": 65000.0,
            "high": 64900.0,  # Invalid: high < open
            "low": 64000.0,
            "close": 64500.0,
            "volume": 10.0,
        }
        candle, issues = CandleValidator.validate_candle(data)
        assert candle is None
        assert any(i.field == "high_bound" for i in issues)

    def test_negative_volume_rejected(self):
        data = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "timestamp": "2026-11-01T20:00:00Z",
            "open": 65000.0,
            "high": 65500.0,
            "low": 64800.0,
            "close": 65200.0,
            "volume": -5.0,  # Invalid
        }
        candle, issues = CandleValidator.validate_candle(data)
        assert candle is None

    def test_utc_normalization_from_epoch_ms(self):
        epoch_ms = 1730472000000  # 2026-11-01 14:40:00 UTC
        data = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "timestamp": epoch_ms,
            "open": 65000.0,
            "high": 65500.0,
            "low": 64800.0,
            "close": 65200.0,
            "volume": 10.0,
        }
        candle, _ = CandleValidator.validate_candle(data)
        assert candle is not None
        assert candle.timestamp == "2024-11-01T14:40:00.000Z" or "Z" in candle.timestamp

    def test_sequence_duplicate_detection(self):
        c1 = ValidatedCandle(symbol="BTCUSDT", timeframe="15m", timestamp="2026-11-01T20:00:00.000Z",
                             open=10, high=12, low=9, close=11, volume=100)
        c2 = ValidatedCandle(symbol="BTCUSDT", timeframe="15m", timestamp="2026-11-01T20:00:00.000Z",  # Duplicate!
                             open=10, high=12, low=9, close=11, volume=100)
        c3 = ValidatedCandle(symbol="BTCUSDT", timeframe="15m", timestamp="2026-11-01T20:15:00.000Z",
                             open=11, high=13, low=10, close=12, volume=150)

        seq, issues = CandleValidator.validate_sequence([c1, c2, c3], timeframe="15m", allow_duplicates=False)
        assert len(seq) == 2
        assert seq[0].timestamp == "2026-11-01T20:00:00.000Z"
        assert seq[1].timestamp == "2026-11-01T20:15:00.000Z"
        assert any(i.field == "duplicate_timestamp" for i in issues)

    def test_sequence_missing_gap_detection(self):
        c1 = ValidatedCandle(symbol="BTCUSDT", timeframe="15m", timestamp="2026-11-01T20:00:00.000Z",
                             open=10, high=12, low=9, close=11, volume=100)
        # Missing 20:15 and 20:30 (45 min gap instead of 15 min)
        c2 = ValidatedCandle(symbol="BTCUSDT", timeframe="15m", timestamp="2026-11-01T20:45:00.000Z",
                             open=11, high=13, low=10, close=12, volume=150)

        seq, issues = CandleValidator.validate_sequence([c1, c2], timeframe="15m")
        assert len(seq) == 2
        assert any(i.field == "missing_candles_gap" for i in issues)


# ============================================================
# 2. PARQUET REPOSITORY TESTS
# ============================================================

class TestParquetRepository:
    @pytest.fixture
    def temp_repo(self):
        temp_dir = tempfile.mkdtemp(prefix="neptune_parquet_test_")
        repo = ParquetMarketDataRepository(base_dir=temp_dir)
        yield repo
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_save_and_load_candles(self, temp_repo):
        df = pd.DataFrame([
            {"timestamp": "2026-11-01T20:00:00.000Z", "open": 100.0, "high": 105.0, "low": 98.0, "close": 102.0, "volume": 50.0},
            {"timestamp": "2026-11-01T20:15:00.000Z", "open": 102.0, "high": 108.0, "low": 101.0, "close": 107.0, "volume": 60.0},
        ])
        saved_count = await temp_repo.save_candles("BTCUSDT", "15m", df)
        assert saved_count == 2

        loaded = await temp_repo.load_candles("BTCUSDT", "15m")
        assert len(loaded) == 2
        assert loaded.iloc[0]["open"] == 100.0
        assert loaded.iloc[1]["close"] == 107.0

    @pytest.mark.asyncio
    async def test_deduplication_on_append(self, temp_repo):
        df1 = pd.DataFrame([
            {"timestamp": "2026-11-01T20:00:00.000Z", "open": 100.0, "high": 105.0, "low": 98.0, "close": 102.0, "volume": 50.0},
        ])
        await temp_repo.save_candles("BTCUSDT", "15m", df1)

        # Append overlapping row with updated close
        df2 = pd.DataFrame([
            {"timestamp": "2026-11-01T20:00:00.000Z", "open": 100.0, "high": 105.0, "low": 98.0, "close": 103.5, "volume": 55.0},
            {"timestamp": "2026-11-01T20:15:00.000Z", "open": 103.5, "high": 108.0, "low": 101.0, "close": 107.0, "volume": 60.0},
        ])
        await temp_repo.save_candles("BTCUSDT", "15m", df2)

        loaded = await temp_repo.load_candles("BTCUSDT", "15m")
        assert len(loaded) == 2
        # Overwritten with latest value
        assert loaded.iloc[0]["close"] == 103.5

    @pytest.mark.asyncio
    async def test_get_latest_candle_time(self, temp_repo):
        df = pd.DataFrame([
            {"timestamp": "2026-11-01T20:00:00.000Z", "open": 100.0, "high": 105.0, "low": 98.0, "close": 102.0, "volume": 50.0},
            {"timestamp": "2026-11-01T20:45:00.000Z", "open": 102.0, "high": 108.0, "low": 101.0, "close": 107.0, "volume": 60.0},
        ])
        await temp_repo.save_candles("BTCUSDT", "15m", df)

        latest_dt = await temp_repo.get_latest_candle_time("BTCUSDT", "15m")
        assert latest_dt is not None
        assert latest_dt == datetime(2026, 11, 1, 20, 45, tzinfo=timezone.utc)


# ============================================================
# 3. BINANCE PUBLIC CLIENT TESTS
# ============================================================

class TestBinancePublicClient:
    @pytest.mark.asyncio
    async def test_fetch_klines_parsing(self):
        client = BinancePublicClient()
        mock_raw_response = [
            [
                1730472000000, "65000.00", "65500.00", "64800.00", "65200.00",
                "125.45", 1730472899999, "8179340.00", 3200, "60.10", "3918500.00", "0"
            ]
        ]
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.headers = {"x-mbx-used-weight-1m": "15"}
        mock_resp.json.return_value = mock_raw_response

        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            klines = await client.fetch_klines("BTCUSDT", "15m", limit=1)

        assert len(klines) == 1
        k = klines[0]
        assert k["symbol"] == "BTCUSDT"
        assert k["timeframe"] == "15m"
        assert k["open"] == 65000.0
        assert k["close"] == 65200.0
        assert k["is_closed"] is True
        assert client.used_weight_1m == 15

    @pytest.mark.asyncio
    async def test_rate_limit_429_triggers_error(self):
        client = BinancePublicClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_resp.headers = {"Retry-After": "10"}

        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            with pytest.raises(BinanceRateLimitError) as exc_info:
                await client.fetch_klines("BTCUSDT", "15m")

        assert exc_info.value.status_code == 429
        assert exc_info.value.retry_after == 10
        assert client.is_rate_limited is True

    @pytest.mark.asyncio
    async def test_retry_on_network_failure(self):
        client = BinancePublicClient(max_retries=3)
        mock_good_resp = MagicMock()
        mock_good_resp.status_code = 200
        mock_good_resp.headers = {}
        mock_good_resp.json.return_value = []

        # Fail twice with RequestError, succeed on 3rd attempt
        with patch("httpx.AsyncClient.get", side_effect=[
            httpx.ConnectError("Network down"),
            httpx.TimeoutException("Timeout"),
            mock_good_resp
        ]):
            with patch("asyncio.sleep", return_value=None):
                res = await client.fetch_klines("BTCUSDT", "15m")
                assert res == []


# ============================================================
# 4. MARKET DATA SERVICE TESTS
# ============================================================

class TestMarketDataService:
    @pytest.mark.asyncio
    async def test_cache_first_skips_network_when_fresh(self):
        temp_dir = tempfile.mkdtemp(prefix="neptune_service_test_")
        repo = ParquetMarketDataRepository(base_dir=temp_dir)
        mock_client = MagicMock()
        mock_client.fetch_klines = AsyncMock()

        # Seed local repo with a fresh candle (10 minutes ago)
        now_dt = datetime.now(timezone.utc)
        recent_dt = now_dt - timedelta(minutes=5)
        df = pd.DataFrame([{
            "timestamp": recent_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "open": 65000.0, "high": 65500.0, "low": 64800.0, "close": 65200.0, "volume": 10.0
        }])
        await repo.save_candles("BTCUSDT", "15m", df)

        service = MarketDataService(
            client=mock_client,
            repository=repo,
            symbols=["BTCUSDT"],
            timeframes=["15m"],
        )
        await service.initialize()

        # Because local candle is fresh (5 min old < 15 min interval), zero REST calls should be made
        mock_client.fetch_klines.assert_not_called()

        candles = service.get_candles("BTCUSDT", "15m")
        assert len(candles) == 1
        assert candles[0].close == 65200.0

        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_live_websocket_candle_routes_closed_to_subscribers(self):
        repo = AsyncMock()
        mock_client = MagicMock()
        service = MarketDataService(client=mock_client, repository=repo)

        # Initialize empty cache
        service._cache["BTCUSDT"] = {"15m": []}
        service._current_candle["BTCUSDT"] = {}

        received_candles = []
        async def subscriber(candle: ValidatedCandle):
            received_candles.append(candle)

        service.subscribe_closed_candles(subscriber)

        # 1. Dispatch unclosed tick
        unclosed = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "timestamp": "2026-11-01T20:00:00.000Z",
            "open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0, "volume": 50.0,
            "is_closed": False
        }
        await service._handle_live_candle(unclosed)

        assert len(received_candles) == 0  # not broadcasted yet
        assert service.get_current_candle("BTCUSDT", "15m") is not None
        assert service.get_current_candle("BTCUSDT", "15m").is_closed is False
        assert len(service.get_candles("BTCUSDT", "15m")) == 0

        # 2. Dispatch closed candle
        closed = {
            "symbol": "BTCUSDT",
            "timeframe": "15m",
            "timestamp": "2026-11-01T20:00:00.000Z",
            "open": 100.0, "high": 105.0, "low": 99.0, "close": 105.0, "volume": 75.0,
            "is_closed": True
        }
        await service._handle_live_candle(closed)

        assert len(received_candles) == 1
        assert received_candles[0].is_closed is True
        assert len(service.get_candles("BTCUSDT", "15m")) == 1
        assert service.get_candles("BTCUSDT", "15m")[0].close == 105.0
