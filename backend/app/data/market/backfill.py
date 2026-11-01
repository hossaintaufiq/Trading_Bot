"""
NEPTUNE Market Data — Paginated Historical Backfill Module (`backfill.py`)

Safe, resumable, rate-limit-aware historical market data ingestion:
- Respects Binance public unauthenticated REST limits (Rule S-02, ADR-011).
- Detects existing local Parquet coverage; avoids re-downloading existing bars (ADR-014).
- Paginates chronologically backward or forward in 1,000-candle batches.
- Validates OHLCV integrity and sequence consistency (CandleValidator).
- Merges and deduplicates into monthly Parquet partitions.
"""
import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import pandas as pd
from pydantic import BaseModel, ConfigDict
import structlog

from app.data.market.binance_client import BinancePublicClient, BinanceRateLimitError
from app.data.market.validator import CandleValidator, ValidatedCandle
from app.data.repositories.parquet_repo import ParquetMarketDataRepository

logger = structlog.get_logger(__name__)


class BackfillDatasetSummary(BaseModel):
    """Telemetry report for a single backfill operation."""
    symbol: str
    timeframe: str
    candles_fetched: int
    candles_saved: int
    total_stored_candles: int
    earliest_timestamp: str
    latest_timestamp: str
    elapsed_seconds: float
    status: str
    message: str = ""


class HistoricalDataBackfiller:
    """
    Orchestrates historical candle backfilling from Binance public REST into Parquet storage.
    """

    def __init__(
        self,
        client: Optional[BinancePublicClient] = None,
        repository: Optional[ParquetMarketDataRepository] = None,
        validator: Optional[CandleValidator] = None,
        rate_limit_delay_seconds: float = 0.1,
    ):
        self.client = client or BinancePublicClient()
        self.repository = repository or ParquetMarketDataRepository()
        self.validator = validator or CandleValidator()
        self.delay_sec = rate_limit_delay_seconds

    async def backfill_target_depth(
        self,
        symbol: str,
        timeframe: str,
        target_candles: int = 5000,
        batch_size: int = 1000,
    ) -> BackfillDatasetSummary:
        """
        Backfill historical candles until at least `target_candles` are stored locally.
        Fetches backward in time from earliest existing candle.
        """
        t0 = time.time()
        sym_clean = symbol.upper().replace("/", "")

        # 1. Inspect existing storage
        existing_df = await self.repository.load_candles(sym_clean, timeframe)
        current_count = len(existing_df)
        earliest_time = await self.repository.get_earliest_candle_time(sym_clean, timeframe)
        latest_time = await self.repository.get_latest_candle_time(sym_clean, timeframe)

        if current_count >= target_candles:
            return BackfillDatasetSummary(
                symbol=sym_clean,
                timeframe=timeframe,
                candles_fetched=0,
                candles_saved=0,
                total_stored_candles=current_count,
                earliest_timestamp=earliest_time.isoformat() if earliest_time else "",
                latest_timestamp=latest_time.isoformat() if latest_time else "",
                elapsed_seconds=round(time.time() - t0, 2),
                status="UP_TO_DATE",
                message=f"Storage already has {current_count} >= target {target_candles} candles.",
            )

        needed = target_candles - current_count
        logger.info(
            "backfill_started",
            symbol=sym_clean,
            timeframe=timeframe,
            existing=current_count,
            target=target_candles,
            needed=needed,
        )

        total_fetched = 0
        total_saved = 0

        # Backfill direction: if we have data, paginate backward from earliest_time
        # end_time for the backward page is earliest_time epoch ms - 1
        end_ms = int(earliest_time.timestamp() * 1000) - 1 if earliest_time else None

        while current_count + total_saved < target_candles:
            fetch_limit = min(batch_size, target_candles - (current_count + total_saved))
            if fetch_limit <= 0:
                break

            try:
                # Binance REST returns up to limit candles ending at end_time
                batch = await self.client.fetch_klines(
                    symbol=sym_clean,
                    interval=timeframe,
                    start_time=None,
                    end_time=end_ms,
                    limit=fetch_limit,
                )
            except BinanceRateLimitError as e:
                logger.warning("backfill_rate_limited", retry_after=e.retry_after)
                await asyncio.sleep(e.retry_after)
                continue
            except Exception as e:
                logger.error("backfill_batch_error", error=str(e))
                break

            if not batch:
                logger.info("backfill_no_more_history_available", symbol=sym_clean, timeframe=timeframe)
                break

            total_fetched += len(batch)

            # Validate batch
            valid_candles: List[ValidatedCandle] = []
            for item in batch:
                try:
                    c, issues = self.validator.validate_candle(item, require_closed=True)
                    if c is not None:
                        valid_candles.append(c)
                except Exception:
                    continue

            if not valid_candles:
                break

            # Convert to DataFrame and save into Parquet
            std_cols = ["timestamp", "open", "high", "low", "close", "volume", "quote_volume", "trades_count"]
            batch_df = pd.DataFrame([
                {k: getattr(c, k, None) for k in std_cols}
                for c in valid_candles
            ])
            saved_count = await self.repository.save_candles(sym_clean, timeframe, batch_df)
            total_saved += saved_count

            # Update earliest timestamp for next backward batch
            first_ts_iso = valid_candles[0].timestamp
            dt_first = datetime.fromisoformat(first_ts_iso.replace("Z", "+00:00"))
            next_end_ms = int(dt_first.timestamp() * 1000) - 1

            if end_ms is not None and next_end_ms >= end_ms:
                # No progress
                break
            end_ms = next_end_ms

            await asyncio.sleep(self.delay_sec)

        # Reload final count and range
        final_df = await self.repository.load_candles(sym_clean, timeframe)
        final_earliest = await self.repository.get_earliest_candle_time(sym_clean, timeframe)
        final_latest = await self.repository.get_latest_candle_time(sym_clean, timeframe)

        return BackfillDatasetSummary(
            symbol=sym_clean,
            timeframe=timeframe,
            candles_fetched=total_fetched,
            candles_saved=total_saved,
            total_stored_candles=len(final_df),
            earliest_timestamp=final_earliest.isoformat() if final_earliest else "",
            latest_timestamp=final_latest.isoformat() if final_latest else "",
            elapsed_seconds=round(time.time() - t0, 2),
            status="SUCCESS" if total_saved > 0 or len(final_df) >= target_candles else "PARTIAL",
            message=f"Added {total_saved} candles. Total stored: {len(final_df)}.",
        )
