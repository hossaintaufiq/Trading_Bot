"""
Binance Market Data Service & Testnet Client.
Provides:
1. REST Kline fetcher for historical charts & indicator warm-up.
2. Async WebSocket listener for real-time live price ticks & candle updates.
3. CCXT Sandbox client for Binance Spot Testnet execution.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Callable
import aiohttp
import ccxt.async_support as ccxt_async
import pandas as pd

logger = logging.getLogger("binance_service")


class BinanceService:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.symbol = config.get("symbol", "BTC/USDT")
        self.timeframe = config.get("timeframe", "1m")
        self.ws_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.on_candle_callback: Optional[Callable] = None
        self.on_ticker_callback: Optional[Callable] = None

        # CCXT Testnet client
        self.ccxt_testnet: Optional[ccxt_async.binance] = None
        self._init_ccxt_client()

    def _init_ccxt_client(self):
        """Initialize CCXT client configured for Binance Spot Testnet."""
        testnet_cfg = self.config.get("binance_testnet", {})
        api_key = testnet_cfg.get("api_key", "").strip()
        api_secret = testnet_cfg.get("api_secret", "").strip()

        if api_key and api_secret:
            try:
                self.ccxt_testnet = ccxt_async.binance({
                    "apiKey": api_key,
                    "secret": api_secret,
                    "enableRateLimit": True,
                    "options": {"defaultType": "spot"}
                })
                self.ccxt_testnet.set_sandbox_mode(True)
                logger.info("Binance Testnet CCXT client initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize CCXT Testnet client: {e}")
                self.ccxt_testnet = None
        else:
            self.ccxt_testnet = None

    def format_symbol_for_api(self, symbol: str) -> str:
        """Convert 'BTC/USDT' -> 'BTCUSDT'."""
        return symbol.replace("/", "").upper()

    def format_symbol_for_ws(self, symbol: str) -> str:
        """Convert 'BTC/USDT' -> 'btcusdt'."""
        return symbol.replace("/", "").lower()

    async def fetch_historical_klines(self, symbol: str, timeframe: str = "1m", limit: int = 150) -> pd.DataFrame:
        """Fetch historical klines via Binance public REST API."""
        binance_symbol = self.format_symbol_for_api(symbol)
        url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval={timeframe}&limit={limit}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to fetch klines: HTTP {resp.status}")
                        return pd.DataFrame()
                    data = await resp.json()
            except Exception as e:
                logger.error(f"Error fetching historical klines: {e}")
                return pd.DataFrame()

        rows = []
        for k in data:
            # kline format: [open_time, open, high, low, close, volume, close_time, ...]
            rows.append({
                "time": int(k[0] / 1000),  # Unix timestamp in seconds for Lightweight Charts
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5]),
                "is_closed": True
            })

        df = pd.DataFrame(rows)
        return df

    async def start_websocket(self, on_candle: Callable, on_ticker: Callable):
        """Start background WebSocket listener for live price action."""
        self.on_candle_callback = on_candle
        self.on_ticker_callback = on_ticker
        self.is_running = True
        self.ws_task = asyncio.create_task(self._ws_loop())

    async def stop_websocket(self):
        """Stop background WebSocket listener."""
        self.is_running = False
        if self.ws_task:
            self.ws_task.cancel()
            try:
                await self.ws_task
            except asyncio.CancelledError:
                pass
        if self.ccxt_testnet:
            await self.ccxt_testnet.close()

    async def _ws_loop(self):
        """Persistent WebSocket loop with automatic reconnection."""
        while self.is_running:
            symbol_ws = self.format_symbol_for_ws(self.symbol)
            stream_url = f"wss://stream.binance.com:9443/ws/{symbol_ws}@kline_{self.timeframe}"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(stream_url, heartbeat=20.0) as ws:
                        logger.info(f"Connected to Binance WebSocket stream: {symbol_ws}@kline_{self.timeframe}")
                        async for msg in ws:
                            if not self.is_running:
                                break
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                payload = json.loads(msg.data)
                                kline = payload.get("k", {})
                                candle = {
                                    "time": int(kline.get("t", 0) / 1000),
                                    "open": float(kline.get("o", 0)),
                                    "high": float(kline.get("h", 0)),
                                    "low": float(kline.get("l", 0)),
                                    "close": float(kline.get("c", 0)),
                                    "volume": float(kline.get("v", 0)),
                                    "is_closed": bool(kline.get("x", False))
                                }
                                current_price = float(kline.get("c", 0))

                                if self.on_ticker_callback:
                                    await self.on_ticker_callback(self.symbol, current_price, candle)
                                if self.on_candle_callback:
                                    await self.on_candle_callback(self.symbol, candle)

                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"WebSocket connection dropped: {e}. Reconnecting in 3 seconds...")
                await asyncio.sleep(3)

    # --- Binance Testnet Trading API Methods ---

    async def testnet_get_balance(self) -> Dict[str, float]:
        """Fetch real balance on Binance Spot Testnet."""
        if not self.ccxt_testnet:
            return {"USDT": 0.0, "asset": 0.0}
        try:
            balance = await self.ccxt_testnet.fetch_balance()
            usdt = float(balance.get("free", {}).get("USDT", 0.0))
            base_asset = self.symbol.split("/")[0]
            asset = float(balance.get("free", {}).get(base_asset, 0.0))
            return {"USDT": usdt, "asset": asset}
        except Exception as e:
            logger.error(f"Error fetching testnet balance: {e}")
            return {"USDT": 0.0, "asset": 0.0, "error": str(e)}

    async def testnet_create_order(self, symbol: str, side: str, amount_usdt: float, current_price: float) -> Dict[str, Any]:
        """Execute a market order on Binance Spot Testnet."""
        if not self.ccxt_testnet:
            return {"success": False, "error": "Binance Testnet API keys not configured"}
        try:
            qty = amount_usdt / current_price
            order = await self.ccxt_testnet.create_market_order(symbol, side.lower(), qty)
            return {"success": True, "order": order}
        except Exception as e:
            logger.error(f"Error placing testnet order: {e}")
            return {"success": False, "error": str(e)}
