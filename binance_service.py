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
        self.watchlist = config.get("watchlist", [
            "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT",
            "SUI/USDT", "DOGE/USDT", "XRP/USDT", "PEPE/USDT"
        ])
        if self.symbol not in self.watchlist:
            self.watchlist.insert(0, self.symbol)

        self.timeframe = config.get("timeframe", "1m")
        self.ws_task: Optional[asyncio.Task] = None
        self.is_running = False
        self.on_candle_callback: Optional[Callable] = None
        self.on_ticker_callback: Optional[Callable] = None

        # Build symbol mapping (e.g., 'BTCUSDT' -> 'BTC/USDT')
        self._build_symbol_map()

        # CCXT Clients for Testnet & Live (Real Money)
        self.ccxt_testnet: Optional[ccxt_async.binance] = None
        self.ccxt_live: Optional[ccxt_async.binance] = None
        self._init_ccxt_client()

    def _build_symbol_map(self):
        self.symbol_map: Dict[str, str] = {}
        for s in self.watchlist:
            clean = self.format_symbol_for_api(s)
            self.symbol_map[clean] = s

    def _init_ccxt_client(self):
        """Initialize CCXT clients for both Binance Spot Testnet and Live Real Money."""
        # 1. Testnet client
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

        # 2. Live Real Money client
        live_cfg = self.config.get("binance_live", {})
        live_key = live_cfg.get("api_key", "").strip()
        live_secret = live_cfg.get("api_secret", "").strip()

        if live_key and live_secret:
            try:
                self.ccxt_live = ccxt_async.binance({
                    "apiKey": live_key,
                    "secret": live_secret,
                    "enableRateLimit": True,
                    "options": {"defaultType": "spot"}
                })
                logger.info("Binance Live (Real Money) CCXT client initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize CCXT Live client: {e}")
                self.ccxt_live = None
        else:
            self.ccxt_live = None

    def format_symbol_for_api(self, symbol: str) -> str:
        """Convert 'BTC/USDT' -> 'BTCUSDT'."""
        return symbol.replace("/", "").upper()

    def format_symbol_for_ws(self, symbol: str) -> str:
        """Convert 'BTC/USDT' -> 'btcusdt'."""
        return symbol.replace("/", "").lower()

    def map_api_symbol_to_pair(self, api_sym: str) -> str:
        """Map 'BTCUSDT' to 'BTC/USDT'."""
        api_upper = api_sym.upper()
        if api_upper in self.symbol_map:
            return self.symbol_map[api_upper]
        if api_upper.endswith("USDT"):
            base = api_upper[:-4]
            pair = f"{base}/USDT"
            self.symbol_map[api_upper] = pair
            return pair
        return api_upper

    async def fetch_historical_klines(self, symbol: str, timeframe: str = "1m", limit: int = 150) -> pd.DataFrame:
        """Fetch historical klines via Binance public REST API."""
        binance_symbol = self.format_symbol_for_api(symbol)
        url = f"https://api.binance.com/api/v3/klines?symbol={binance_symbol}&interval={timeframe}&limit={limit}"

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        logger.error(f"Failed to fetch klines for {symbol}: HTTP {resp.status}")
                        return pd.DataFrame()
                    data = await resp.json()
            except Exception as e:
                logger.error(f"Error fetching historical klines for {symbol}: {e}")
                return pd.DataFrame()

        rows = []
        for k in data:
            rows.append({
                "time": int(k[0] / 1000),
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
        """Start background WebSocket listener for live price action across all watchlist coins."""
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
        if self.ccxt_live:
            await self.ccxt_live.close()

    async def _ws_loop(self):
        """Combined multiplex WebSocket loop streaming real-time klines for the entire watchlist."""
        while self.is_running:
            # Ensure current symbol is in watchlist
            if self.symbol not in self.watchlist:
                self.watchlist.insert(0, self.symbol)
            self._build_symbol_map()

            # Form combined stream URL: wss://stream.binance.com:9443/stream?streams=btcusdt@kline_1m/ethusdt@kline_1m/...
            stream_names = [f"{self.format_symbol_for_ws(s)}@kline_{self.timeframe}" for s in self.watchlist]
            streams_param = "/".join(stream_names)
            combined_url = f"wss://stream.binance.com:9443/stream?streams={streams_param}"

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(combined_url, heartbeat=20.0) as ws:
                        logger.info(f"Connected to Binance Multi-Coin WebSocket: {len(self.watchlist)} streams active.")
                        async for msg in ws:
                            if not self.is_running:
                                break
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                payload = json.loads(msg.data)
                                # Combined stream wraps in {"stream": "...", "data": {...}}
                                event_data = payload.get("data", payload)
                                kline = event_data.get("k", {})
                                raw_sym = kline.get("s", "") or event_data.get("s", "")
                                pair_symbol = self.map_api_symbol_to_pair(raw_sym)

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
                                    await self.on_ticker_callback(pair_symbol, current_price, candle)
                                if self.on_candle_callback:
                                    await self.on_candle_callback(pair_symbol, candle)

                            elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"WebSocket connection dropped: {e}. Reconnecting in 3 seconds...")
                await asyncio.sleep(3)

    # --- Binance Live Real Money Trading API Methods ---

    async def live_get_balance(self) -> Dict[str, Any]:
        """Fetch real money balance from Binance Live Spot wallet."""
        if not self.ccxt_live:
            return {"USDT": 0.0, "asset": 0.0, "error": "Binance Live API keys not configured"}
        try:
            balance = await self.ccxt_live.fetch_balance()
            usdt = float(balance.get("free", {}).get("USDT", 0.0))
            base_asset = self.symbol.split("/")[0]
            asset = float(balance.get("free", {}).get(base_asset, 0.0))
            return {"USDT": round(usdt, 2), "asset": round(asset, 6), "success": True}
        except Exception as e:
            logger.error(f"Error fetching live balance: {e}")
            return {"USDT": 0.0, "asset": 0.0, "error": str(e), "success": False}

    async def live_create_order(self, symbol: str, side: str, amount_usdt: float, current_price: float) -> Dict[str, Any]:
        """Execute a REAL MONEY market order on Binance Spot."""
        if not self.ccxt_live:
            return {"success": False, "error": "Binance Live API keys not configured"}
        try:
            qty = amount_usdt / current_price
            order = await self.ccxt_live.create_market_order(symbol, side.lower(), qty)
            return {"success": True, "order": order}
        except Exception as e:
            logger.error(f"Error placing live order: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    async def validate_credentials(api_key: str, api_secret: str, is_testnet: bool = True) -> Dict[str, Any]:
        """Validate Binance API credentials and check account permissions."""
        if not api_key or not api_secret:
            return {"valid": False, "error": "API Key and Secret must not be empty"}
        client = None
        try:
            client = ccxt_async.binance({
                "apiKey": api_key.strip(),
                "secret": api_secret.strip(),
                "enableRateLimit": True,
                "options": {"defaultType": "spot"}
            })
            if is_testnet:
                client.set_sandbox_mode(True)
            balance = await client.fetch_balance()
            usdt = float(balance.get("free", {}).get("USDT", 0.0))
            return {"valid": True, "usdt_balance": round(usdt, 2), "message": "API keys successfully verified!"}
        except Exception as e:
            return {"valid": False, "error": str(e)}
        finally:
            if client:
                await client.close()
