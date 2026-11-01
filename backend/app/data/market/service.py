"""
NEPTUNE Market Data — Market Data Service

Master orchestrator for market data:
- Coordinates BinancePublicClient, CandleValidator, and ParquetMarketDataRepository.
- Maintains in-memory ring buffer (1,000 closed candles per symbol/timeframe) for zero-latency agent access.
- Implements cache-first historical backfill policy (ADR-014).
- Dispatches closed candles to Central Brain and WebSocket broadcaster.
- Never serves incomplete candles to closed-candle strategies (Rule A-09).
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Coroutine, Dict, List, Optional

import pandas as pd
import structlog

from app.config.settings import get_settings
from app.data.market.binance_client import BinancePublicClient
from app.data.market.validator import CandleValidator, ValidatedCandle
from app.data.repositories.parquet_repo import ParquetMarketDataRepository

logger = structlog.get_logger(__name__)


class MarketDataService:
    """
    Coordinates historical backfill, real-time ingestion, validation, and storage.
    """

    def __init__(
        self,
        client: Optional[BinancePublicClient] = None,
        repository: Optional[ParquetMarketDataRepository] = None,
        symbols: Optional[List[str]] = None,
        timeframes: Optional[List[str]] = None,
    ):
        settings = get_settings()
        self.settings = settings
        self.symbols = symbols if symbols is not None else settings.symbols_list
        self.timeframes = timeframes if timeframes is not None else settings.timeframes_list
        self.client = client or BinancePublicClient()
        self.repository = repository or ParquetMarketDataRepository()
        self.validator = CandleValidator()

        # In-memory circular ring buffers: symbol -> timeframe -> list of ValidatedCandle
        self._cache: Dict[str, Dict[str, List[ValidatedCandle]]] = {}
        # Latest partial/unclosed candle: symbol -> timeframe -> ValidatedCandle
        self._current_candle: Dict[str, Dict[str, ValidatedCandle]] = {}

        # Downstream broadcast listeners
        self._closed_candle_subscribers: List[
            Callable[[ValidatedCandle], Coroutine[Any, Any, None]]
        ] = []

        # Connect live client callback
        self.client.add_candle_listener(self._handle_live_candle)

    def subscribe_closed_candles(
        self, subscriber: Callable[[ValidatedCandle], Coroutine[Any, Any, None]]
    ) -> None:
        """Register downstream listeners (e.g. Central Brain, WS hub)."""
        self._closed_candle_subscribers.append(subscriber)

    async def initialize(self) -> None:
        """
        Execute cache-first initialization across all configured symbols and timeframes.
        """
        symbols = self.symbols
        timeframes = self.timeframes

        logger.info(
            "market_data_service_initializing",
            symbols=symbols,
            timeframes=timeframes,
        )

        for sym in symbols:
            self._cache.setdefault(sym, {})
            self._current_candle.setdefault(sym, {})
            for tf in timeframes:
                self._cache[sym].setdefault(tf, [])
                await self._backfill_timeframe(sym, tf)

        logger.info("market_data_service_initialized")

    async def _backfill_timeframe(self, symbol: str, timeframe: str) -> None:
        """
        Cache-first historical backfill (ADR-014):
        1. Query local Parquet storage first.
        2. If local candles exist, load into memory buffer.
        3. Check delta against now: only query Binance for missing delta.
        4. If local storage is empty, fetch full backfill limit.
        """
        # 1. Load from local Parquet archive
        local_df = await self.repository.load_candles(symbol, timeframe, limit=1000)

        if not local_df.empty:
            # Parse into validated models
            validated_list: List[ValidatedCandle] = []
            for _, row in local_df.iterrows():
                candle_dict = row.to_dict()
                candle_dict["symbol"] = symbol
                candle_dict["timeframe"] = timeframe
                candle_dict["is_closed"] = True
                vc, issues = self.validator.validate_candle(candle_dict, require_closed=True)
                if vc:
                    validated_list.append(vc)

            self._cache[symbol][timeframe] = validated_list[-1000:]
            latest_time = await self.repository.get_latest_candle_time(symbol, timeframe)

            logger.info(
                "parquet_cache_loaded",
                symbol=symbol,
                timeframe=timeframe,
                candle_count=len(self._cache[symbol][timeframe]),
                latest_stored_time=latest_time.isoformat() if latest_time else None,
            )

            # Check if delta fetch is needed
            if latest_time:
                interval_mins = CandleValidator.TIMEFRAME_MINUTES.get(timeframe, 15)
                age = datetime.now(timezone.utc) - latest_time
                if age <= timedelta(minutes=interval_mins):
                    # Data is completely up to date, skip REST call
                    return

                start_ms = int(latest_time.timestamp() * 1000) + 1
                try:
                    delta_klines = await self.client.fetch_klines(
                        symbol=symbol,
                        interval=timeframe,
                        start_time=start_ms,
                        limit=500,
                    )
                    if delta_klines:
                        await self._persist_and_cache_raw(symbol, timeframe, delta_klines)
                except Exception as exc:
                    logger.warning("delta_backfill_failed", symbol=symbol, timeframe=timeframe, error=str(exc))
                return

        # 2. Local storage was empty — full initial backfill from public REST
        try:
            logger.info("fetching_initial_history", symbol=symbol, timeframe=timeframe)
            raw_klines = await self.client.fetch_klines(
                symbol=symbol,
                interval=timeframe,
                limit=self.settings.historical_backfill_limit,
            )
            if raw_klines:
                await self._persist_and_cache_raw(symbol, timeframe, raw_klines)
        except Exception as exc:
            logger.error("initial_backfill_failed", symbol=symbol, timeframe=timeframe, error=str(exc))

    async def _persist_and_cache_raw(
        self, symbol: str, timeframe: str, raw_klines: List[Dict[str, Any]]
    ) -> None:
        """Validate, persist, and update memory ring buffer from raw kline dicts."""
        validated_candidates: List[ValidatedCandle] = []
        for raw in raw_klines:
            vc, issues = self.validator.validate_candle(raw, require_closed=True)
            if vc:
                validated_candidates.append(vc)

        # Validate sequence, drop duplicates
        valid_seq, seq_issues = self.validator.validate_sequence(
            validated_candidates, timeframe=timeframe, allow_duplicates=False
        )
        if not valid_seq:
            return

        # Convert to DataFrame for Parquet persistence
        records = [
            {
                "timestamp": c.timestamp,
                "open": c.open,
                "high": c.high,
                "low": c.low,
                "close": c.close,
                "volume": c.volume,
                "quote_volume": c.quote_volume or 0.0,
                "trades_count": c.trades_count or 0,
            }
            for c in valid_seq
        ]
        df = pd.DataFrame(records)
        await self.repository.save_candles(symbol, timeframe, df)

        # Update in-memory ring buffer
        existing = self._cache[symbol][timeframe]
        combined = existing + valid_seq
        # Deduplicate memory cache by timestamp
        seen = set()
        deduped = []
        for c in combined:
            if c.timestamp not in seen:
                seen.add(c.timestamp)
                deduped.append(c)
        self._cache[symbol][timeframe] = deduped[-1000:]

    async def _handle_live_candle(self, raw_candle: Dict[str, Any]) -> None:
        """Handle incoming tick/kline from WebSocket stream."""
        symbol = raw_candle.get("symbol", "")
        timeframe = raw_candle.get("timeframe", "")

        if symbol not in self._cache or timeframe not in self._cache[symbol]:
            self._cache.setdefault(symbol, {}).setdefault(timeframe, [])
        self._current_candle.setdefault(symbol, {})

        # Validate candle (allow incomplete candle for UI streaming)
        vc, issues = self.validator.validate_candle(raw_candle, require_closed=False)
        if not vc:
            return

        self._current_candle[symbol][timeframe] = vc

        # If the candle just closed, add to closed ring buffer and broadcast to agents
        if vc.is_closed:
            existing = self._cache[symbol][timeframe]
            # Replace if timestamp matches existing, or append
            if existing and existing[-1].timestamp == vc.timestamp:
                existing[-1] = vc
            else:
                existing.append(vc)
                if len(existing) > 1000:
                    existing.pop(0)

            # Persist closed candle to Parquet in background
            records = [{
                "timestamp": vc.timestamp,
                "open": vc.open,
                "high": vc.high,
                "low": vc.low,
                "close": vc.close,
                "volume": vc.volume,
                "quote_volume": vc.quote_volume or 0.0,
                "trades_count": vc.trades_count or 0,
            }]
            df = pd.DataFrame(records)
            asyncio.create_task(self.repository.save_candles(symbol, timeframe, df))

            # Broadcast to subscribers (Central Brain, WS broadcaster)
            for sub in self._closed_candle_subscribers:
                try:
                    await sub(vc)
                except Exception as exc:
                    logger.error("closed_candle_broadcast_failed", error=str(exc))

    def get_candles(
        self, symbol: str, timeframe: str, limit: int = 100
    ) -> List[ValidatedCandle]:
        """
        Return the latest closed candles from zero-latency in-memory cache.
        Guaranteed to contain closed candles only.
        """
        candles = self._cache.get(symbol, {}).get(timeframe, [])
        return candles[-limit:]

    def get_latest_candle(
        self, symbol: str, timeframe: str
    ) -> Optional[ValidatedCandle]:
        """Return the most recently closed candle for a symbol and timeframe."""
        candles = self._cache.get(symbol, {}).get(timeframe, [])
        return candles[-1] if candles else None

    def get_current_candle(
        self, symbol: str, timeframe: str
    ) -> Optional[ValidatedCandle]:
        """Return the latest unclosed/in-progress candle for UI displays."""
        return self._current_candle.get(symbol, {}).get(timeframe)
