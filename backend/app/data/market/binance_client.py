"""
NEPTUNE Market Data — Binance Public Client

Connects to Binance Public REST API and WebSocket streams:
- Zero authentication: NO API key or secret required (Rule S-02, ADR-011).
- Fetches historical klines via REST with rate-limit tracking (429/418 backoff).
- Subscribes to live public kline WebSocket streams with automatic exponential reconnection.
- Emits normalized candle payloads into registered listeners.
"""
import asyncio
import json
import random
import time
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine, Dict, List, Optional

import httpx
import structlog
import websockets

from app.config.settings import get_settings

logger = structlog.get_logger(__name__)


class BinanceRateLimitError(Exception):
    """Raised when Binance returns HTTP 429 or 418."""
    def __init__(self, status_code: int, retry_after: int = 30):
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(f"Binance rate limit triggered (HTTP {status_code}). Backing off for {retry_after}s.")


class BinancePublicClient:
    """
    Public unauthenticated client for Binance market data.
    """

    def __init__(
        self,
        rest_base_url: Optional[str] = None,
        ws_base_url: Optional[str] = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 3,
    ):
        settings = get_settings()
        self.rest_base_url = (rest_base_url or settings.binance_rest_base_url).rstrip("/")
        self.ws_base_url = (ws_base_url or settings.binance_ws_base_url).rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries

        # Rate-limiting state
        self.used_weight_1m = 0
        self.is_rate_limited = False
        self.rate_limit_reset_time = 0.0

        # WebSocket lifecycle
        self._ws_running = False
        self._ws_task: Optional[asyncio.Task] = None
        self._candle_listeners: List[Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]] = []

    def add_candle_listener(
        self, listener: Callable[[Dict[str, Any]], Coroutine[Any, Any, None]]
    ) -> None:
        """Register a callback for live candle updates."""
        self._candle_listeners.append(listener)

    async def fetch_klines(
        self,
        symbol: str,
        interval: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical closed klines via Binance public REST API.
        
        Args:
            symbol: e.g. 'BTCUSDT'
            interval: e.g. '15m', '1h', '4h'
            start_time: Epoch milliseconds (inclusive)
            end_time: Epoch milliseconds (inclusive)
            limit: Number of candles (max 1000)
        
        Returns:
            List of raw candle dicts with timestamps in ISO 8601 UTC.
        """
        # Guard against active rate-limit bans
        now = time.time()
        if self.is_rate_limited and now < self.rate_limit_reset_time:
            wait_sec = self.rate_limit_reset_time - now
            raise BinanceRateLimitError(429, retry_after=int(wait_sec))

        endpoint = f"{self.rest_base_url}/api/v3/klines"
        params: Dict[str, Any] = {
            "symbol": symbol.upper().replace("/", ""),
            "interval": interval,
            "limit": min(limit, 1000),
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time

        attempt = 0
        backoff_sec = 1.0

        while attempt < self.max_retries:
            attempt += 1
            try:
                async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                    resp = await client.get(endpoint, params=params)

                    # Update weight tracking from headers
                    weight_header = resp.headers.get("x-mbx-used-weight-1m")
                    if weight_header and weight_header.isdigit():
                        self.used_weight_1m = int(weight_header)

                    if resp.status_code in (429, 418):
                        self.is_rate_limited = True
                        retry_after_hdr = resp.headers.get("Retry-After", "30")
                        retry_after = int(retry_after_hdr) if retry_after_hdr.isdigit() else 30
                        self.rate_limit_reset_time = time.time() + retry_after
                        logger.warning(
                            "binance_rate_limit_hit",
                            status=resp.status_code,
                            retry_after=retry_after,
                            attempt=attempt,
                        )
                        raise BinanceRateLimitError(resp.status_code, retry_after=retry_after)

                    resp.raise_for_status()
                    raw_data = resp.json()
                    return self._parse_rest_klines(symbol, interval, raw_data)

            except BinanceRateLimitError:
                raise
            except (httpx.RequestError, httpx.HTTPStatusError) as exc:
                logger.warning(
                    "binance_rest_request_failed",
                    attempt=attempt,
                    symbol=symbol,
                    interval=interval,
                    error=str(exc),
                )
                if attempt >= self.max_retries:
                    raise
                # Exponential backoff with jitter
                sleep_time = backoff_sec * (2 ** (attempt - 1)) + random.uniform(0.1, 0.5)
                await asyncio.sleep(sleep_time)

        return []

    async def fetch_klines_paginated(
        self,
        symbol: str,
        interval: str,
        start_time: int,
        end_time: Optional[int] = None,
        total_limit: Optional[int] = None,
        page_size: int = 1000,
    ) -> List[Dict[str, Any]]:
        """
        Fetch historical candles spanning multiple pages via Binance public REST API.

        Args:
            symbol: e.g. 'BTCUSDT'
            interval: e.g. '15m'
            start_time: Epoch milliseconds (inclusive)
            end_time: Epoch milliseconds (inclusive, optional)
            total_limit: Maximum total candles to retrieve across all pages (optional)
            page_size: Batch size per page (max 1000)

        Returns:
            Concatenated, chronologically sorted list of unique candle dicts.
        """
        all_candles: List[Dict[str, Any]] = []
        current_start = start_time
        batch_limit = min(page_size, 1000)

        while True:
            fetch_limit = batch_limit
            if total_limit is not None:
                remaining = total_limit - len(all_candles)
                if remaining <= 0:
                    break
                fetch_limit = min(batch_limit, remaining)

            batch = await self.fetch_klines(
                symbol=symbol,
                interval=interval,
                start_time=current_start,
                end_time=end_time,
                limit=fetch_limit,
            )

            if not batch:
                break

            all_candles.extend(batch)

            if len(batch) < fetch_limit:
                # Exchange returned fewer candles than requested; end of data
                break

            # Next page start_time = last candle open time + 1 millisecond
            last_candle_iso = batch[-1]["timestamp"]
            dt = datetime.fromisoformat(last_candle_iso.replace("Z", "+00:00"))
            next_start = int(dt.timestamp() * 1000) + 1
            if next_start <= current_start:
                break
            current_start = next_start

            if end_time is not None and current_start >= end_time:
                break

            await asyncio.sleep(0.05)

        return all_candles

    def _parse_rest_klines(
        self, symbol: str, interval: str, raw_klines: List[List[Any]]
    ) -> List[Dict[str, Any]]:
        """Parse Binance kline arrays into normalized dictionaries."""
        parsed: List[Dict[str, Any]] = []
        for k in raw_klines:
            open_time_ms = int(k[0])
            open_dt = datetime.fromtimestamp(open_time_ms / 1000.0, tz=timezone.utc)
            parsed.append({
                "symbol": symbol.upper().replace("/", ""),
                "timeframe": interval,
                "timestamp": open_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "quote_volume": float(k[7]),
                "trades_count": int(k[8]),
                "is_closed": True,  # Historical klines fetched are closed
            })
        return parsed

    async def start_kline_stream(
        self, symbols: List[str], intervals: List[str]
    ) -> None:
        """
        Start public multi-stream WebSocket connection for real-time klines.
        Re-establishes connection automatically on disconnect.
        """
        self._ws_running = True
        streams = [
            f"{s.lower().replace('/', '')}@kline_{i}"
            for s in symbols
            for i in intervals
        ]
        stream_path = "/stream?streams=" + "/".join(streams)
        url = self.ws_base_url.replace("/ws", "") + stream_path

        backoff = 1.0
        while self._ws_running:
            try:
                logger.info("binance_ws_connecting", url=url)
                async with websockets.connect(url, ping_interval=20, ping_timeout=15) as ws:
                    logger.info("binance_ws_connected", stream_count=len(streams))
                    backoff = 1.0  # Reset backoff on successful connect

                    while self._ws_running:
                        try:
                            msg_str = await asyncio.wait_for(ws.recv(), timeout=30.0)
                            msg = json.loads(msg_str)
                            if "data" in msg and "k" in msg["data"]:
                                kline_data = msg["data"]["k"]
                                candle = self._parse_ws_kline(kline_data)
                                for listener in self._candle_listeners:
                                    try:
                                        await listener(candle)
                                    except Exception as exc:
                                        logger.error("candle_listener_error", error=str(exc))
                        except asyncio.TimeoutError:
                            # Send ping to keep connection alive
                            pong_waiter = await ws.ping()
                            await asyncio.wait_for(pong_waiter, timeout=5.0)

            except (websockets.ConnectionClosed, Exception) as exc:
                if not self._ws_running:
                    break
                logger.warning("binance_ws_disconnected", error=str(exc), retry_in=backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2.0 + random.uniform(0.1, 0.5), 60.0)

    def _parse_ws_kline(self, k: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a WebSocket kline object to normalized dictionary."""
        open_time_ms = int(k["t"])
        open_dt = datetime.fromtimestamp(open_time_ms / 1000.0, tz=timezone.utc)
        return {
            "symbol": k["s"].upper(),
            "timeframe": k["i"],
            "timestamp": open_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            "open": float(k["o"]),
            "high": float(k["h"]),
            "low": float(k["l"]),
            "close": float(k["c"]),
            "volume": float(k["v"]),
            "quote_volume": float(k["q"]),
            "trades_count": int(k["n"]),
            "is_closed": bool(k["x"]),
        }

    async def stop(self) -> None:
        """Stop WebSocket loops and background tasks."""
        self._ws_running = False
        if self._ws_task and not self._ws_task.done():
            self._ws_task.cancel()
            try:
                await self._ws_task
            except asyncio.CancelledError:
                pass
        logger.info("binance_public_client_stopped")

