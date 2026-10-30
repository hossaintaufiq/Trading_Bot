"""
Master Trading Bot Engine for Neptune Bot.
Orchestrates market data ingestion, Day Trader quantitative skills (Scanner, Exit Planner,
Time Machine Monte Carlo, Risk Gate), automated execution, and live 1s / 15s telemetry broadcasts.
"""

import asyncio
import datetime
import json
import logging
import math
import os
import time
from typing import Dict, Any, List, Optional
import pandas as pd

from indicators import enrich_dataframe
from strategies import get_strategy, Signal
from day_trader_skills import DayTraderSuite, TradePlan, TimeMachineResult, RiskVerdict
from paper_exchange import PaperExchange
from binance_service import BinanceService
from money_manager import MoneyManager
from risk_manager import CentralizedRiskManager

logger = logging.getLogger("bot_engine")


def sanitize_json_val(val: Any) -> Any:
    """Recursively ensure all numeric values are standard JSON compliant (no NaN/Inf)."""
    if isinstance(val, float):
        if math.isnan(val) or math.isinf(val):
            return 0.0
        return val
    elif isinstance(val, dict):
        return {k: sanitize_json_val(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [sanitize_json_val(v) for v in val]
    elif hasattr(val, "item"):
        try:
            return sanitize_json_val(val.item())
        except Exception:
            return str(val)
    return val


class BotEngine:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.config = self.load_config()

        # Bot runtime status - auto-running on launch
        self.is_running = True
        self.status = "RUNNING"  # "RUNNING", "PAUSED", "PANIC"
        self.bot_name = self.config.get("bot_name", "NEPTUNE BOT")
        self.mode = self.config.get("mode", "PAPER")
        self.symbol = self.config.get("symbol", "BTC/USDT")
        self.watchlist = self.config.get("watchlist", [
            "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT",
            "SUI/USDT", "DOGE/USDT", "XRP/USDT", "PEPE/USDT"
        ])
        if self.symbol not in self.watchlist:
            self.watchlist.insert(0, self.symbol)

        self.timeframe = self.config.get("timeframe", "1m")
        self.active_strategy_name = self.config.get("active_strategy", "neptune_fleet")
        self.max_open_positions = int(self.config.get("max_open_positions", 5))

        # Multi-Market state tracking: dictionary of {symbol: market_state}
        self.markets: Dict[str, Dict[str, Any]] = {}
        for s in self.watchlist:
            self.markets[s] = {
                "current_price": 0.0,
                "klines_df": pd.DataFrame(),
                "latest_signal": None,
                "detected_setups": [],
                "latest_plan": None,
                "latest_timemachine": None,
                "latest_market_trends": {}
            }

        # Active primary market & Indicator state (for primary chart display)
        self.current_price = 0.0
        self.klines_df = pd.DataFrame()
        self.latest_signal: Optional[Signal] = None
        self.last_candle_time = 0

        # Day Trader Skill Suite
        self.day_trader = DayTraderSuite(self.config)
        self.detected_setups: List[Dict[str, Any]] = []
        self.latest_plan: Optional[TradePlan] = None
        self.latest_timemachine: Optional[TimeMachineResult] = None
        self.last_scan_time = 0
        self.pulse_interval_sec = 15  # 15s scan pulse
        self.daily_loss_so_far = 0.0
        self.last_closed_candle_time: Dict[str, int] = {}
        self.max_correlated_positions = int(self.config.get("max_correlated_positions", 2))

        # Money Management & Centralized Risk Subsystems
        self.money_manager = MoneyManager(self.config)
        self.risk_manager = CentralizedRiskManager(self.config)
        self.max_open_positions = self.money_manager.max_open_positions

        # Subsystems
        self.paper_exchange = PaperExchange(
            state_file=self.config.get("paper_state_path", "paper_state.json"),
            initial_balance=self.config.get("paper_initial_balance", 10000.0),
            fee_pct=self.config.get("taker_fee_pct", 0.1),
            slippage_pct=self.config.get("slippage_pct", 0.05)
        )
        self.paper_exchange.current_symbol = self.symbol
        self.binance_service = BinanceService(self.config)
        self.strategy = get_strategy(self.active_strategy_name, self.config, learning_engine=self.paper_exchange.learning_engine)

        # Logging & Telemetry broadcast
        self.logs: List[Dict[str, Any]] = []
        self.ws_subscribers: List[asyncio.Queue] = []
        self.chart_markers: List[Dict[str, Any]] = []
        self.latest_market_trends: Dict[str, Any] = {}

        # Background 15s pulse task
        self.pulse_task: Optional[asyncio.Task] = None

        self.log("INFO", f"🌐 Neptune Multi-Coin Fleet initialized. Watching [{len(self.watchlist)}] high-volume coins. Max concurrent positions: {self.max_open_positions}.")

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config.json: {e}")
        return {
            "mode": "PAPER",
            "bot_name": "NEPTUNE BOT",
            "symbol": "BTC/USDT",
            "watchlist": [
                "BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT",
                "SUI/USDT", "DOGE/USDT", "XRP/USDT", "PEPE/USDT"
            ],
            "timeframe": "1m",
            "active_strategy": "neptune_fleet",
            "trade_amount_usdt": 100.0,
            "max_open_positions": 5,
            "max_loss_per_trade_usd": 50.0,
            "max_daily_loss_usd": 200.0,
            "min_reward_risk": 1.5,
            "stop_loss_pct": 1.5,
            "take_profit_pct": 3.0,
            "trailing_stop_enabled": True,
            "trailing_stop_pct": 1.0,
            "paper_initial_balance": 10000.0
        }

    def save_config(self):
        """Save active config to JSON file."""
        try:
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            self.log("ERROR", f"Failed to save config: {e}")

    def log(self, level: str, message: str):
        """Record system log and broadcast to WebSockets."""
        entry = {
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
            "timestamp": int(time.time() * 1000),
            "level": level.upper(),
            "message": message
        }
        self.logs.insert(0, entry)
        if len(self.logs) > 150:
            self.logs = self.logs[:150]

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast({"type": "LOG_ENTRY", "data": entry}))
        except RuntimeError:
            pass

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected frontend WebSockets."""
        for queue in list(self.ws_subscribers):
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                pass

    async def initialize(self):
        """Seed historical data for all watchlist coins, launch multiplex stream, and start 15s pulse."""
        self.log("INFO", f"Seeding historical candle data for {len(self.watchlist)} watchlist coins ({self.timeframe})...")

        for sym in self.watchlist:
            try:
                df = await self.binance_service.fetch_historical_klines(sym, self.timeframe, limit=100)
                if not df.empty:
                    strat_params = self.config.get("strategies", {}).get(self.active_strategy_name, {})
                    enriched = enrich_dataframe(df, strat_params)
                    if sym not in self.markets:
                        self.markets[sym] = {"latest_signal": None, "detected_setups": []}
                    self.markets[sym]["klines_df"] = enriched
                    px = float(enriched.iloc[-1]["close"])
                    self.markets[sym]["current_price"] = px

                    if sym == self.symbol:
                        self.klines_df = enriched
                        self.current_price = px
                        self.last_candle_time = int(enriched.iloc[-1]["time"])
                await asyncio.sleep(0.08)
            except Exception as e:
                logger.warning(f"Error seeding historical klines for {sym}: {e}")

        self.log("INFO", f"Watchlist seeded. Primary market: {self.symbol} (${self.current_price:,.2f}).")
        self._run_skills_scan()

        # Start live combined multiplex WebSocket stream (all coins concurrent)
        await self.binance_service.start_websocket(
            on_candle=self.handle_candle_update,
            on_ticker=self.handle_ticker_tick
        )

        # Start background 15-second radar pulse task
        if self.pulse_task is None or self.pulse_task.done():
            self.pulse_task = asyncio.create_task(self._periodic_15s_pulse())

    async def _periodic_15s_pulse(self):
        """Every 15 seconds: scan setups, run Monte Carlo simulation, broadcast radar update."""
        while True:
            try:
                await asyncio.sleep(self.pulse_interval_sec)
                if not self.klines_df.empty and len(self.klines_df) >= 20:
                    self._run_skills_scan()
                    fleet_status = self.get_fleet_diagnostics()

                    prices_map = {s: m.get("current_price", 0.0) for s, m in self.markets.items() if m.get("current_price", 0.0) > 0}

                    await self.broadcast({
                        "type": "RADAR_SCAN_PULSE",
                        "data": {
                            "setups": self.detected_setups,
                            "fleet_status": fleet_status,
                            "plan": self.latest_plan.__dict__ if self.latest_plan else None,
                            "timemachine": self.latest_timemachine.__dict__ if self.latest_timemachine else None,
                            "market_trends": self.latest_market_trends,
                            "prices": prices_map,
                            "timestamp": int(time.time() * 1000)
                        }
                    })
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error in 15s pulse: {e}")

    def _run_skills_scan(self):
        """Execute Day Trader Skills: Scanner, Exit Bracket Planner, and Time Machine for active symbol."""
        if self.klines_df.empty or len(self.klines_df) < 20:
            return

        # 1. Scanner: Find active setups
        self.detected_setups = self.day_trader.scan_setups(self.klines_df, self.symbol)

        # 2. Exit Planner: Build Bracket Plan for current price
        setup_name = self.detected_setups[0]["name"] if self.detected_setups else "Trend Momentum"
        self.latest_plan = self.day_trader.plan_bracket_exit(
            symbol=self.symbol,
            setup_name=setup_name,
            entry_price=self.current_price,
            df=self.klines_df,
            stop_mode="or-mid",
            target_mode="2R"
        )

        # 3. Time Machine: Run 1,000 Monte Carlo replays
        self.latest_timemachine = self.day_trader.run_time_machine(
            plan=self.latest_plan,
            df=self.klines_df,
            num_replays=1000
        )
        # 4. Live Market Trends
        self.latest_market_trends = self.day_trader.compute_market_trends(self.klines_df, self.current_price)
        self.last_scan_time = int(time.time() * 1000)

    async def handle_ticker_tick(self, symbol: str, price: float, candle: Dict[str, Any]):
        """Triggered on every micro-price tick across all watchlist coins."""
        if price <= 0:
            return

        # Ensure market entry exists
        if symbol not in self.markets:
            self.markets[symbol] = {
                "current_price": price,
                "klines_df": pd.DataFrame(),
                "latest_signal": None,
                "detected_setups": []
            }

        mkt = self.markets[symbol]
        mkt["current_price"] = price

        # Update kline dataframe for this symbol
        kdf = mkt.get("klines_df", pd.DataFrame())
        if not kdf.empty:
            last_idx = kdf.index[-1]
            if int(candle["time"]) == int(kdf.loc[last_idx, "time"]):
                kdf.loc[last_idx, "close"] = candle["close"]
                kdf.loc[last_idx, "high"] = max(kdf.loc[last_idx, "high"], candle["high"])
                kdf.loc[last_idx, "low"] = min(kdf.loc[last_idx, "low"], candle["low"])
                kdf.loc[last_idx, "volume"] = candle["volume"]
            elif int(candle["time"]) > int(kdf.loc[last_idx, "time"]):
                new_row = pd.DataFrame([candle])
                kdf = pd.concat([kdf, new_row], ignore_index=True)
                if len(kdf) > 150:
                    kdf = kdf.iloc[-150:].reset_index(drop=True)
                mkt["klines_df"] = kdf

        # If this tick is for the currently selected display symbol
        if symbol == self.symbol:
            self.current_price = price
            self.klines_df = mkt.get("klines_df", pd.DataFrame())

        # Evaluate real-time Risk Management for this symbol if an open position is held in the basket
        if self.is_running and self.status == "RUNNING" and symbol in self.paper_exchange.positions:
            await self._check_risk_management_for_symbol(symbol, price)

        # Broadcast live multi-coin ticker update to frontend
        prices_map = {s: m.get("current_price", 0.0) for s, m in self.markets.items() if m.get("current_price", 0.0) > 0}
        portfolio = self.paper_exchange.get_portfolio_summary(prices_map)

        if symbol == self.symbol and not self.klines_df.empty:
            self.latest_market_trends = self.day_trader.compute_market_trends(self.klines_df, self.current_price)

        await self.broadcast({
            "type": "TICKER_UPDATE",
            "data": {
                "symbol": symbol,
                "active_symbol": self.symbol,
                "price": price,
                "prices": prices_map,
                "candle": candle if symbol == self.symbol else None,
                "portfolio": portfolio,
                "market_trends": self.latest_market_trends
            }
        })

    async def handle_candle_update(self, symbol: str, candle: Dict[str, Any]):
        """Triggered on candle tick / closure. Evaluates closed candles for entries, manages open positions intrabar."""
        if symbol not in self.markets:
            return

        mkt = self.markets[symbol]
        kdf = mkt.get("klines_df", pd.DataFrame())
        if kdf.empty or len(kdf) < 15:
            return

        is_closed = candle.get("is_closed", False)
        candle_time = int(candle.get("time", 0))
        current_price = float(candle.get("close", mkt.get("current_price", self.current_price)))

        # Evaluate real-time Risk Management on open position during intrabar ticks
        pos = self.paper_exchange.positions.get(symbol)
        if self.is_running and self.status == "RUNNING" and pos is not None:
            curr_atr = float(kdf.iloc[-1].get("atr", current_price * 0.01)) if not kdf.empty else current_price * 0.01
            exit_reason = self.evaluate_position_exit(symbol, pos, current_price, curr_atr, kdf)
            if exit_reason:
                self.log("RISK", f"🚨 [{symbol}] EXIT TRIGGERED: {exit_reason}")
                await self._execute_sell(symbol, current_price, exit_reason)
                return

        # Bug 5 Fix: Entry signals must use CLOSED candles only, deduplicated by candle timestamp
        if not is_closed:
            return

        last_closed = self.last_closed_candle_time.get(symbol, 0)
        if candle_time <= last_closed:
            return

        self.last_closed_candle_time[symbol] = candle_time

        # Update or append closed candle to klines dataframe
        last_idx = kdf.index[-1]
        if candle_time == int(kdf.loc[last_idx, "time"]):
            for col in ["open", "high", "low", "close", "volume"]:
                if col in candle:
                    kdf.loc[last_idx, col] = candle[col]
        elif candle_time > int(kdf.loc[last_idx, "time"]):
            new_row = pd.DataFrame([candle])
            kdf = pd.concat([kdf, new_row], ignore_index=True)
            if len(kdf) > 150:
                kdf = kdf.iloc[-150:].reset_index(drop=True)

        strat_params = self.config.get("strategies", {}).get(self.active_strategy_name, {})
        kdf = enrich_dataframe(kdf, strat_params)
        mkt["klines_df"] = kdf

        # Evaluate Strategy for this coin on confirmed closed candle
        pos = self.paper_exchange.positions.get(symbol)
        signal = self.strategy.evaluate(kdf, pos)
        mkt["latest_signal"] = signal

        # If this is the currently displayed chart symbol, broadcast indicators
        if symbol == self.symbol:
            self.klines_df = kdf
            self.latest_signal = signal
            curr_row = kdf.iloc[-1]
            telemetry = {
                "symbol": symbol,
                "price": self.current_price,
                "rsi": float(curr_row.get("rsi", 50.0)),
                "ema_fast": float(curr_row.get("ema_fast", self.current_price)),
                "ema_slow": float(curr_row.get("ema_slow", self.current_price)),
                "bb_upper": float(curr_row.get("bb_upper", self.current_price)),
                "bb_lower": float(curr_row.get("bb_lower", self.current_price)),
                "bb_middle": float(curr_row.get("bb_middle", self.current_price)),
                "signal": {
                    "action": signal.action,
                    "reason": signal.reason,
                    "confidence": signal.confidence,
                    "setup_name": signal.setup_name,
                    "metrics": signal.metrics
                }
            }

            await self.broadcast({
                "type": "INDICATORS_UPDATE",
                "data": telemetry
            })

        # Process automated execution if running
        if self.is_running and self.status == "RUNNING":
            await self._process_strategy_signal_for_symbol(symbol, signal, kdf)

    def evaluate_position_exit(
        self,
        symbol: str,
        pos: Dict[str, Any],
        current_price: float,
        current_atr: float = 0.0,
        df: Optional[pd.DataFrame] = None
    ) -> Optional[str]:
        """
        Centralized Risk & Position Exit Evaluator (Bugs 6 & 7).
        Strict Priority Order:
        1. Hard Stop-Loss Hit / Setup Invalidation Hit
        2. Take-Profit Target Hit
        3. ATR-based Trailing Stop & Break-Even Ratchet (+1R activation, non-decreasing)
        4. Max Holding Duration Exceeded
        5. Strategy Custom Exit Signal (if df provided and strategy emits SELL)
        """
        entry_price = float(pos.get("entry_price", current_price))
        pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0.0

        # 1. Hard Stop-Loss Hit / Setup Invalidation Hit
        stop_loss_price = pos.get("stop_loss_price")
        if stop_loss_price is not None and current_price <= stop_loss_price:
            if pos.get("trailing_active") or (pos.get("initial_stop_price") and stop_loss_price > pos.get("initial_stop_price")):
                return f"🛡️ ATR Trailing Stop Hit at ${current_price:,.2f} (Locked Stop: ${stop_loss_price:,.2f}, PnL: {pnl_pct:+.2f}%)"
            return f"🚨 Stop-Loss Hit at ${current_price:,.2f} (Stop: ${stop_loss_price:,.2f}, PnL: {pnl_pct:+.2f}%)"

        invalidation_price = pos.get("invalidation_price")
        if invalidation_price is not None and current_price <= invalidation_price:
            return f"🚨 Setup Invalidation Hit at ${current_price:,.2f} (Inv: ${invalidation_price:,.2f}, PnL: {pnl_pct:+.2f}%)"

        # 2. Take-Profit Target Hit
        take_profit_price = pos.get("take_profit_price")
        if take_profit_price is not None and current_price >= take_profit_price:
            return f"🎯 Take-Profit Target Hit at ${current_price:,.2f} (+{pnl_pct:.2f}%)"

        # 3. ATR-based Trailing Stop & Break-Even Ratchet (Bug 6)
        highest_seen = max(float(pos.get("highest_price", entry_price)), current_price)
        pos["highest_price"] = round(highest_seen, 4)

        initial_stop = pos.get("initial_stop_price") or pos.get("stop_loss_price") or (entry_price - (1.5 * current_atr if current_atr > 0 else entry_price * 0.015))
        r_dist = max(0.0001, entry_price - initial_stop)

        trailing_enabled = self.config.get("trailing_stop_enabled", True)
        if trailing_enabled and (highest_seen - entry_price) >= r_dist:
            pos["trailing_active"] = True

            # Step A: Ratchet stop to break-even net of round-trip costs (taker 0.1%*2 + slip 0.05%*2 = 0.30%)
            fee_slip_buffer_pct = float(self.config.get("fee_slippage_buffer_pct", 0.30)) / 100.0
            be_price = round(entry_price * (1.0 + fee_slip_buffer_pct), 4)

            current_stop = pos.get("stop_loss_price") or 0.0
            if current_stop < be_price:
                pos["stop_loss_price"] = be_price
                self.log("TRADE", f"🔒 [{symbol}] Stop ratcheted to Break-Even + fees (${be_price:,.2f}) after +1R gain")

            # Step B: Trail by ATR below highest price seen
            if current_atr > 0:
                trail_mult = float(self.config.get("atr_trail_multiplier", 1.5))
                trail_stop = round(highest_seen - (trail_mult * current_atr), 4)
                # Monotonically non-decreasing stop
                if trail_stop > pos["stop_loss_price"]:
                    pos["stop_loss_price"] = trail_stop

            # Check if ratcheted stop is hit
            if current_price <= pos["stop_loss_price"]:
                return f"🛡️ ATR Trailing Stop Hit at ${current_price:,.2f} (Locked Stop: ${pos['stop_loss_price']:,.2f}, PnL: {pnl_pct:+.2f}%)"

        # 4. Max Holding Duration Exceeded
        max_bars = pos.get("max_holding_bars")
        entry_time = pos.get("entry_time", 0)
        if max_bars and entry_time > 0:
            timeframe_sec = 60
            if "15m" in self.timeframe:
                timeframe_sec = 900
            elif "5m" in self.timeframe:
                timeframe_sec = 300
            elif "1h" in self.timeframe:
                timeframe_sec = 3600
            bars_held = int((time.time() * 1000 - entry_time) / (timeframe_sec * 1000))
            if bars_held >= max_bars:
                return f"⏰ Max Holding Bars Exceeded ({bars_held}/{max_bars} bars, PnL: {pnl_pct:+.2f}%)"

        # 5. Strategy Custom Exit Signal
        if df is not None and not df.empty and len(df) >= 15:
            strat_signal = self.strategy.evaluate(df, pos)
            if strat_signal.action == "SELL":
                return f"Strategy Exit: {strat_signal.reason}"

        return None

    async def _check_risk_management_for_symbol(self, symbol: str, current_price: float):
        """Evaluate centralized risk management for an open position."""
        pos = self.paper_exchange.positions.get(symbol)
        if not pos:
            return

        mkt = self.markets.get(symbol, {})
        kdf = mkt.get("klines_df", pd.DataFrame())
        curr_atr = float(kdf.iloc[-1].get("atr", current_price * 0.01)) if not kdf.empty else current_price * 0.01

        exit_reason = self.evaluate_position_exit(symbol, pos, current_price, curr_atr, kdf)
        if exit_reason:
            self.log("RISK", f"🚨 [{symbol}] EXIT TRIGGERED: {exit_reason}")
            await self._execute_sell(symbol, current_price, exit_reason)

    async def _process_strategy_signal_for_symbol(self, symbol: str, signal: Signal, df: pd.DataFrame):
        """Execute buy/sell on a specific symbol when strategy condition triggers."""
        has_pos = symbol in self.paper_exchange.positions
        current_px = self.markets.get(symbol, {}).get("current_price", self.current_price)

        if signal.action == "BUY" and not has_pos:
            # Bug 3 Gate: Every strategy must define its own valid stop, target, invalidation, and max holding time.
            if (
                signal.stop_price is None or signal.stop_price <= 0 or
                signal.target_price is None or signal.target_price <= 0 or
                signal.stop_price >= current_px or
                signal.target_price <= current_px
            ):
                self.log("RISK", f"🛑 [{symbol}] BUY SIGNAL REJECTED: Strategy must define valid stop_price (< px) and target_price (> px). Given stop={signal.stop_price}, target={signal.target_price}")
                return

            # Bug 8 Fix: Correlation / exposure cap on correlated altcoin positions
            if symbol != "BTC/USDT":
                alt_positions = [s for s in self.paper_exchange.positions if s != "BTC/USDT"]
                if len(alt_positions) >= self.max_correlated_positions:
                    self.log("RISK", f"🛑 [{symbol}] ENTRY REJECTED: Correlated altcoin exposure cap reached ({len(alt_positions)}/{self.max_correlated_positions} active alt positions)")
                    return

            # 1. Money Manager Capital Allocation & Total Budget Check
            coin_atr = float(df.iloc[-1].get("atr_pct", 1.0)) if not df.empty else 1.0
            setup_w = 1.0
            if self.paper_exchange.learning_engine:
                setup_w = self.paper_exchange.learning_engine.get_setup_weight(signal.setup_id or signal.setup_name)

            alloc = self.money_manager.calculate_trade_allocation(
                symbol=symbol,
                current_price=current_px,
                active_positions=self.paper_exchange.positions,
                wallet_usdt_balance=self.paper_exchange.usdt_balance,
                setup_weight=setup_w,
                coin_atr_pct=coin_atr
            )

            if not alloc.approved:
                self.log("RISK", f"🛑 [{symbol}] ENTRY SUPPRESSED BY MONEY MANAGER: {alloc.reason}")
                return

            trade_amount = alloc.trade_amount_usdt

            # 2. Plan bracket exit & run Risk Gate before buying
            plan = self.day_trader.plan_bracket_exit(
                symbol=symbol,
                setup_name=signal.setup_name,
                entry_price=current_px,
                df=df
            )
            # Override plan with signal specific stops
            plan.stop_loss = signal.stop_price
            plan.risk_per_unit = max(0.01, current_px - signal.stop_price)
            plan.take_profit = signal.target_price
            plan.reward_per_unit = max(0.01, signal.target_price - current_px)
            plan.reward_risk_ratio = round(plan.reward_per_unit / plan.risk_per_unit, 2)

            risk_check = self.day_trader.check_risk_gate(plan, trade_amount, self.daily_loss_so_far)

            if not risk_check.passed:
                self.log("RISK", f"🛑 [{symbol}] TRADE BLOCKED BY RISK GATE: {risk_check.reason}")
                return

            self.log("SIGNAL", f"🟢 [{symbol}] BUY SIGNAL: {signal.reason} | Stop ${plan.stop_loss:,.2f}, Target ${plan.take_profit:,.2f} [Allocated: ${trade_amount:,.2f}]")
            await self._execute_buy(
                symbol=symbol,
                market_price=current_px,
                amount_usdt=trade_amount,
                reason=signal.reason,
                stop_price=plan.stop_loss,
                tp_price=plan.take_profit,
                setup_id=signal.setup_id or "generic",
                invalidation_price=signal.invalidation_price,
                max_holding_bars=signal.max_holding_bars
            )

        elif signal.action == "SELL" and has_pos:
            self.log("SIGNAL", f"🔴 [{symbol}] SELL SIGNAL: {signal.reason}")
            await self._execute_sell(symbol, current_px, signal.reason)

    async def _execute_buy(
        self,
        symbol: str,
        market_price: float,
        amount_usdt: float,
        reason: str,
        stop_price: Optional[float] = None,
        tp_price: Optional[float] = None,
        setup_id: str = "generic",
        invalidation_price: Optional[float] = None,
        max_holding_bars: Optional[int] = None
    ):
        """Execute buy order in Live Real Money, Testnet, or Paper Exchange."""
        if self.mode == "BINANCE_LIVE" and self.binance_service.ccxt_live:
            self.log("TRADE", f"Executing LIVE REAL MONEY BUY: ${amount_usdt:,.2f} of {symbol}...")
            res = await self.binance_service.live_create_order(symbol, "BUY", amount_usdt, market_price)
            if not res.get("success"):
                self.log("ERROR", f"Live Order Failed: {res.get('error')}. Trade aborted for safety.")
                return
            else:
                self.log("TRADE", f"Live Order Filled: {res.get('order', {}).get('id')}")
                result = self.paper_exchange.execute_buy(
                    symbol, market_price, amount_usdt, f"[LIVE] {reason}", stop_price, tp_price,
                    self.max_open_positions, setup_id, invalidation_price, max_holding_bars
                )
        elif self.mode == "BINANCE_TESTNET" and self.binance_service.ccxt_testnet:
            self.log("TRADE", f"Executing Testnet BUY: ${amount_usdt:,.2f} of {symbol}...")
            res = await self.binance_service.testnet_create_order(symbol, "BUY", amount_usdt, market_price)
            if not res.get("success"):
                self.log("ERROR", f"Testnet Order Failed: {res.get('error')}. Falling back to paper simulation.")
                result = self.paper_exchange.execute_buy(
                    symbol, market_price, amount_usdt, reason, stop_price, tp_price,
                    self.max_open_positions, setup_id, invalidation_price, max_holding_bars
                )
            else:
                self.log("TRADE", f"Testnet Order Filled: {res.get('order', {}).get('id')}")
                result = self.paper_exchange.execute_buy(
                    symbol, market_price, amount_usdt, f"[TESTNET] {reason}", stop_price, tp_price,
                    self.max_open_positions, setup_id, invalidation_price, max_holding_bars
                )
        else:
            result = self.paper_exchange.execute_buy(
                symbol, market_price, amount_usdt, reason, stop_price, tp_price,
                self.max_open_positions, setup_id, invalidation_price, max_holding_bars
            )

        if result.get("success"):
            trade = result["trade"]
            base_sym = symbol.split('/')[0]
            self.log("TRADE", f"✅ BOUGHT {trade['quantity']} {base_sym} @ ${trade['price']:,.2f} (${trade['cost_usdt']}) [{len(self.paper_exchange.positions)}/{self.max_open_positions} in Basket]")

            marker = None
            if symbol == self.symbol:
                marker = {
                    "time": int(trade["timestamp"] / 1000),
                    "position": "belowBar",
                    "color": "#00f5d4",
                    "shape": "arrowUp",
                    "text": f"BUY @ {trade['price']:,.1f}"
                }
                self.chart_markers.append(marker)

            prices_map = {s: m.get("current_price", 0.0) for s, m in self.markets.items() if m.get("current_price", 0.0) > 0}
            portfolio = self.paper_exchange.get_portfolio_summary(prices_map)
            await self.broadcast({"type": "TRADE_EXECUTED", "data": {"trade": trade, "marker": marker, "portfolio": portfolio}})
        else:
            self.log("WARNING", f"[{symbol}] Buy could not execute: {result.get('error')}")

    async def _execute_sell(self, symbol: str, market_price: float, reason: str):
        """Execute sell order in Live Real Money, Testnet, or Paper Exchange."""
        if self.mode == "BINANCE_LIVE" and self.binance_service.ccxt_live:
            pos = self.paper_exchange.positions.get(symbol)
            if pos:
                self.log("TRADE", f"Executing LIVE REAL MONEY SELL: {pos['quantity']} {symbol}...")
                res = await self.binance_service.live_create_order(symbol, "SELL", pos["cost_usdt"], market_price)
                if not res.get("success"):
                    self.log("ERROR", f"Live Sell Order Failed: {res.get('error')}")
            result = self.paper_exchange.execute_sell(symbol, market_price, f"[LIVE] {reason}")
        elif self.mode == "BINANCE_TESTNET" and self.binance_service.ccxt_testnet:
            pos = self.paper_exchange.positions.get(symbol)
            if pos:
                await self.binance_service.testnet_create_order(symbol, "SELL", pos["cost_usdt"], market_price)
            result = self.paper_exchange.execute_sell(symbol, market_price, f"[TESTNET] {reason}")
        else:
            result = self.paper_exchange.execute_sell(symbol, market_price, reason)

        if result.get("success"):
            trade = result["trade"]
            pnl_val = float(trade.get("realized_pnl", 0.0))
            if pnl_val < 0:
                self.daily_loss_so_far += abs(pnl_val)

            # Inform Money Manager and Centralized Risk Manager of closed trade result
            self.money_manager.record_closed_trade_pnl(pnl_val)
            self.risk_manager.record_trade_outcome(pnl_val)
            if self.money_manager.circuit_breaker_tripped or self.risk_manager.circuit_breaker_tripped:
                self.is_running = False
                self.status = "CIRCUIT_BREAKER_HALTED"
                self.log("RISK", f"🚨 MAX SESSION LOSS LIMIT REACHED (${self.money_manager.session_realized_loss:,.2f}). CIRCUIT BREAKER ENGAGED. Halting entries to protect capital!")

            pnl_str = f"+${trade['realized_pnl']:,.2f} (+{trade['realized_pnl_pct']}%)" if trade['realized_pnl'] >= 0 else f"-${abs(trade['realized_pnl']):,.2f} ({trade['realized_pnl_pct']}%)"
            base_sym = symbol.split('/')[0]
            self.log("TRADE", f"🏁 SOLD {trade['quantity']} {base_sym} @ ${trade['price']:,.2f} | PnL: {pnl_str} [{len(self.paper_exchange.positions)}/{self.max_open_positions} in Basket]")

            marker = None
            if symbol == self.symbol:
                marker = {
                    "time": int(trade["timestamp"] / 1000),
                    "position": "aboveBar",
                    "color": "#ff0054",
                    "shape": "arrowDown",
                    "text": f"SELL @ {trade['price']:,.1f} ({trade['realized_pnl_pct']:+.1f}%)"
                }
                self.chart_markers.append(marker)

            prices_map = {s: m.get("current_price", 0.0) for s, m in self.markets.items() if m.get("current_price", 0.0) > 0}
            portfolio = self.paper_exchange.get_portfolio_summary(prices_map)
            await self.broadcast({"type": "TRADE_EXECUTED", "data": {"trade": trade, "marker": marker, "portfolio": portfolio}})
        else:
            self.log("WARNING", f"[{symbol}] Sell could not execute: {result.get('error')}")

    # --- Controls ---

    def start_bot(self):
        """Activate algorithmic execution."""
        if self.money_manager.circuit_breaker_tripped:
            self.log("WARNING", "⚠️ Cannot start bot: Circuit Breaker is active. Reset session loss first.")
            return
        self.is_running = True
        self.status = "RUNNING"
        self.log("INFO", f"▶️ Neptune Bot active in [{self.mode}] mode. Strategy: [{self.active_strategy_name}]. Monitoring {len(self.watchlist)} coins...")

    def stop_bot(self):
        """Pause algorithmic execution."""
        self.is_running = False
        self.status = "PAUSED"
        self.log("INFO", "⏸️ Neptune Bot paused. Active positions remain protected by Stop/Target.")

    async def panic_exit(self):
        """Emergency Kill Switch: Liquidate all active positions in basket immediately."""
        self.is_running = False
        self.status = "PANIC"
        self.log("RISK", "🚨 EMERGENCY PANIC ACTIVATED: Liquidating ALL basket positions immediately!")
        active_syms = list(self.paper_exchange.positions.keys())
        for sym in active_syms:
            px = self.markets.get(sym, {}).get("current_price", self.paper_exchange.positions[sym]["entry_price"])
            await self._execute_sell(sym, px, "EMERGENCY PANIC MANUAL EXIT")
        self.status = "PAUSED"
        self.log("INFO", "Neptune Bot paused after emergency liquidation.")

    def reset_paper_wallet(self):
        """Reset virtual wallet to clean starting state."""
        initial = float(self.config.get("paper_initial_balance", 10000.0))
        self.paper_exchange.reset_wallet(initial)
        self.money_manager.reset_session_loss()
        self.risk_manager.reset_daily_metrics()
        self.chart_markers = []
        self.daily_loss_so_far = 0.0
        self.status = "RUNNING"
        self.is_running = True
        self.log("INFO", f"🔄 Paper wallet reset to ${initial:,.2f} USDT. Centralized Risk Manager and Money Manager circuit breakers reset.")

    async def manual_buy(self, symbol: Optional[str] = None, amount_usdt: Optional[float] = None) -> Dict[str, Any]:
        """Manually trigger an immediate trade for testing and verification."""
        target_sym = symbol or self.symbol
        trade_amount = amount_usdt or float(self.config.get("trade_amount_usdt", 100.0))
        px = self.markets.get(target_sym, {}).get("current_price", self.current_price)
        if px <= 0:
            px = self.current_price

        self.log("TRADE", f"⚡ MANUAL TEST TRADE: Buying ${trade_amount:,.2f} of {target_sym}...")
        stop_p = px * 0.985
        tp_p = px * 1.03
        await self._execute_buy(target_sym, px, trade_amount, "MANUAL INSTANT TEST TRADE", stop_p, tp_p)
        return {"success": True, "message": f"Manual test buy executed for ${trade_amount} on {target_sym}"}

    async def switch_market(self, new_symbol: str):
        """Switch active display chart and primary analysis to any watchlist coin."""
        new_symbol = new_symbol.upper().strip()
        if not new_symbol:
            return

        self.symbol = new_symbol
        self.config["symbol"] = new_symbol
        self.paper_exchange.current_symbol = new_symbol
        self.chart_markers = []

        if new_symbol not in self.watchlist:
            self.watchlist.append(new_symbol)
            self.config["watchlist"] = self.watchlist
            self.binance_service.watchlist = self.watchlist
            self.binance_service._build_symbol_map()

        self.save_config()

        if new_symbol in self.markets and not self.markets[new_symbol]["klines_df"].empty:
            self.klines_df = self.markets[new_symbol]["klines_df"]
            self.current_price = self.markets[new_symbol]["current_price"]
        else:
            self.log("INFO", f"Fetching candle history for switched market {new_symbol}...")
            df = await self.binance_service.fetch_historical_klines(new_symbol, self.timeframe, limit=100)
            if not df.empty:
                strat_params = self.config.get("strategies", {}).get(self.active_strategy_name, {})
                enriched = enrich_dataframe(df, strat_params)
                if new_symbol not in self.markets:
                    self.markets[new_symbol] = {"latest_signal": None, "detected_setups": []}
                self.markets[new_symbol]["klines_df"] = enriched
                px = float(enriched.iloc[-1]["close"])
                self.markets[new_symbol]["current_price"] = px
                self.klines_df = enriched
                self.current_price = px

        self._run_skills_scan()
        self.log("INFO", f"Active chart switched to {new_symbol} (${self.current_price:,.2f}).")

        # Broadcast state snapshot to update chart immediately
        snapshot = self.get_telemetry_snapshot()
        await self.broadcast({"type": "INITIAL_STATE", "data": snapshot})

    async def update_config(self, new_config: Dict[str, Any]):
        """Update runtime configuration and reconfigure dependencies."""
        old_symbol = self.symbol
        old_timeframe = self.timeframe
        old_strategy = self.active_strategy_name

        self.config.update(new_config)
        self.mode = self.config.get("mode", "PAPER")
        self.symbol = self.config.get("symbol", "BTC/USDT")
        self.timeframe = self.config.get("timeframe", "1m")
        self.active_strategy_name = self.config.get("active_strategy", "neptune_fleet")

        self.money_manager.update_config(self.config)
        self.max_open_positions = self.money_manager.max_open_positions

        self.strategy = get_strategy(self.active_strategy_name, self.config, learning_engine=self.paper_exchange.learning_engine)
        self.day_trader.config = self.config
        self.binance_service.config = self.config
        self.binance_service._init_ccxt_client()

        if self.symbol != old_symbol or self.timeframe != old_timeframe:
            self.log("INFO", f"Switching market to {self.symbol} [{self.timeframe}]...")
            self.binance_service.symbol = self.symbol
            self.binance_service.timeframe = self.timeframe
            await self.binance_service.stop_websocket()
            await self.initialize()

        self.save_config()
        self.log("INFO", f"🌐 Neptune configuration updated. Active Strategy: [{self.active_strategy_name}].")

    def get_fleet_diagnostics(self) -> List[Dict[str, Any]]:
        """Return real-time diagnostic status and feedback from all 5 sub-bots."""
        if hasattr(self.strategy, "get_fleet_status"):
            return self.strategy.get_fleet_status(self.klines_df, self.paper_exchange.active_position)
        else:
            if not hasattr(self, "_diagnostic_fleet") or self._diagnostic_fleet is None:
                from strategies import NeptuneFleetStrategy
                self._diagnostic_fleet = NeptuneFleetStrategy(self.config, learning_engine=self.paper_exchange.learning_engine)
            return self._diagnostic_fleet.get_fleet_status(self.klines_df, self.paper_exchange.active_position)

    def get_telemetry_snapshot(self) -> Dict[str, Any]:
        """Generate comprehensive telemetry payload for the UI."""
        prices_map = {s: m.get("current_price", 0.0) for s, m in self.markets.items() if m.get("current_price", 0.0) > 0}
        if self.current_price > 0:
            prices_map[self.symbol] = self.current_price

        portfolio = self.paper_exchange.get_portfolio_summary(prices_map)

        candles = []
        if not self.klines_df.empty:
            for _, r in self.klines_df.tail(100).iterrows():
                candles.append({
                    "time": int(r["time"]),
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": float(r["volume"])
                })

        curr_rsi = 50.0
        curr_ema_fast = self.current_price
        curr_ema_slow = self.current_price
        if not self.klines_df.empty:
            row = self.klines_df.iloc[-1]
            curr_rsi = float(row.get("rsi", 50.0))
            curr_ema_fast = float(row.get("ema_fast", self.current_price))
            curr_ema_slow = float(row.get("ema_slow", self.current_price))

        fleet_status = self.get_fleet_diagnostics()

        snapshot = {
            "bot_name": self.bot_name,
            "status": self.status,
            "is_running": self.is_running,
            "mode": self.mode,
            "symbol": self.symbol,
            "active_symbol": self.symbol,
            "watchlist": self.watchlist,
            "prices": prices_map,
            "timeframe": self.timeframe,
            "active_strategy": self.active_strategy_name,
            "current_price": self.current_price,
            "portfolio": portfolio,
            "money_management": self.money_manager.get_summary(self.paper_exchange.positions, self.paper_exchange.usdt_balance),
            "config": self.config,
            "indicators": {
                "rsi": round(curr_rsi, 2),
                "ema_fast": round(curr_ema_fast, 2),
                "ema_slow": round(curr_ema_slow, 2)
            },
            "signal": {
                "action": self.latest_signal.action if self.latest_signal else "HOLD",
                "reason": self.latest_signal.reason if self.latest_signal else "Neptune Fleet scanning setups...",
                "confidence": self.latest_signal.confidence if self.latest_signal else 0.0,
                "setup_name": self.latest_signal.setup_name if self.latest_signal else "Fleet Radar"
            },
            "day_trader_suite": {
                "setups": self.detected_setups,
                "fleet_status": fleet_status,
                "plan": self.latest_plan.__dict__ if self.latest_plan else None,
                "timemachine": self.latest_timemachine.__dict__ if self.latest_timemachine else None,
                "market_trends": self.latest_market_trends,
                "learning_insights": self.paper_exchange.learning_engine.get_learning_insights(),
                "last_scan_time": self.last_scan_time
            },
            "candles": candles,
            "markers": self.chart_markers[-30:],
            "logs": self.logs[:50]
        }
        return sanitize_json_val(snapshot)

    def run_custom_time_machine(
        self,
        symbol: Optional[str] = None,
        replays: int = 1000,
        horizon: int = 30,
        target_mode: str = "2R"
    ) -> Dict[str, Any]:
        """Execute on-demand dynamic Monte Carlo simulation with user-chosen coin, horizon, replays, and target mode."""
        sym = symbol or self.symbol
        mkt = self.markets.get(sym, {})
        kdf = mkt.get("klines_df", pd.DataFrame())
        px = mkt.get("current_price", self.current_price)

        if kdf.empty or len(kdf) < 25:
            kdf = self.klines_df
            px = self.current_price

        plan = self.day_trader.plan_bracket_exit(
            symbol=sym,
            setup_name="Dynamic Simulation",
            entry_price=px,
            df=kdf,
            target_mode=target_mode
        )
        tm_result = self.day_trader.run_time_machine(
            plan=plan,
            df=kdf,
            num_replays=replays,
            horizon=horizon,
            symbol=sym
        )
        if sym == self.symbol:
            self.latest_timemachine = tm_result
            self.latest_plan = plan

        return sanitize_json_val({
            "success": True,
            "symbol": sym,
            "plan": plan.__dict__,
            "timemachine": tm_result.__dict__
        })
