"""
Realistic Event-Driven Portfolio Backtesting Engine.
Reuses identical strategy evaluation and risk exit logic from live/paper bot.
Simulates closed-candle entries, next-bar-open fills, taker fees, slippage,
and conservative intrabar stop/target execution.
"""

import os
import json
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional, Tuple

from strategies import Signal, BaseStrategy, get_strategy, NeptuneFleetStrategy
from indicators import enrich_dataframe

logger = logging.getLogger("backtest_simulator")


class BacktestEngine:
    def __init__(
        self,
        strategy_name: str = "neptune_fleet",
        config: Optional[Dict[str, Any]] = None,
        initial_capital: float = 10000.0,
        trade_amount: float = 100.0,
        fee_pct: float = 0.10,
        slippage_pct: float = 0.05,
        max_open_positions: int = 5,
        max_correlated_positions: int = 2,
        use_original_logic: bool = False
    ):
        self.strategy_name = strategy_name
        self.config = config or {}
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.trade_amount = trade_amount
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct
        self.max_open_positions = max_open_positions
        self.max_correlated_positions = max_correlated_positions
        self.use_original_logic = use_original_logic

        # Strategy instance
        self.strategy = get_strategy(strategy_name, self.config)

        # State tracking
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.closed_trades: List[Dict[str, Any]] = []
        self.equity_curve: List[Dict[str, Any]] = []

    def run_multi_asset(self, data_by_symbol: Dict[str, pd.DataFrame]) -> List[Dict[str, Any]]:
        """
        Run multi-asset backtest chronologically across multiple symbols.
        Synchronizes all symbols bar-by-bar by timestamp.
        """
        # 1. Enrich dataframes with technical indicators
        enriched_data = {}
        all_timestamps = set()
        for sym, df in data_by_symbol.items():
            if df.empty or len(df) < 25:
                continue
            strat_params = self.config.get("strategies", {}).get(self.strategy_name, {})
            edf = enrich_dataframe(df.copy(), strat_params)
            enriched_data[sym] = edf
            all_timestamps.update(edf["time"].tolist())

        sorted_times = sorted(list(all_timestamps))
        time_to_idx = {sym: {t: i for i, t in enumerate(df["time"])} for sym, df in enriched_data.items()}

        pending_orders = []  # List of dicts: {"symbol": ..., "signal": ..., "eval_time": ...}

        # 2. Step through time chronologically
        for current_time in sorted_times:
            # Step A: Fill pending buy orders at open of current candle (Next Bar Open fill)
            remaining_orders = []
            for order in pending_orders:
                sym = order["symbol"]
                df = enriched_data.get(sym)
                if df is not None and current_time in time_to_idx[sym]:
                    idx = time_to_idx[sym][current_time]
                    open_price = float(df.iloc[idx]["open"])
                    self._execute_buy(sym, open_price, order["signal"], current_time)
                else:
                    remaining_orders.append(order)
            pending_orders = remaining_orders

            # Step B: Evaluate open positions on current candle's price action (Intrabar Risk Checks)
            symbols_to_close = []
            for sym, pos in list(self.positions.items()):
                df = enriched_data.get(sym)
                if df is None or current_time not in time_to_idx[sym]:
                    continue
                idx = time_to_idx[sym][current_time]
                bar = df.iloc[idx]
                exit_signal, exit_px = self._evaluate_position_intrabar(pos, bar, df.iloc[:idx+1])
                if exit_signal:
                    symbols_to_close.append((sym, exit_px, exit_signal, current_time))

            for sym, exit_px, reason, t_exit in symbols_to_close:
                if sym in self.positions:
                    self._execute_sell(sym, exit_px, reason, t_exit)

            # Step C: Evaluate strategy signals on CLOSED bar at current_time
            # Generated signal will be filled at NEXT bar's open
            for sym, df in enriched_data.items():
                if current_time not in time_to_idx[sym]:
                    continue
                idx = time_to_idx[sym][current_time]
                if idx < 20:
                    continue

                historical_slice = df.iloc[:idx+1]
                has_pos = sym in self.positions
                pos = self.positions.get(sym)

                # Skip if already holding or already placed pending order for this symbol
                if has_pos or any(o["symbol"] == sym for o in pending_orders):
                    continue

                # Check portfolio capacity limits
                if len(self.positions) + len(pending_orders) >= self.max_open_positions:
                    continue

                # Bug 8 Correlation Cap: Max 2 correlated altcoins
                if not self.use_original_logic and sym != "BTC/USDT":
                    alt_count = len([s for s in self.positions if s != "BTC/USDT"]) + len([o for o in pending_orders if o["symbol"] != "BTC/USDT"])
                    if alt_count >= self.max_correlated_positions:
                        continue

                signal = self.strategy.evaluate(historical_slice, pos)
                if signal.action == "BUY":
                    # Bug 3 Gate: Reject signals without explicit stops/targets
                    if not self.use_original_logic:
                        curr_close = float(historical_slice.iloc[-1]["close"])
                        if (
                            signal.stop_price is None or signal.stop_price <= 0 or
                            signal.target_price is None or signal.target_price <= 0 or
                            signal.stop_price >= curr_close or
                            signal.target_price <= curr_close
                        ):
                            continue

                    pending_orders.append({
                        "symbol": sym,
                        "signal": signal,
                        "eval_time": current_time
                    })

            # Record portfolio equity
            unrealized_pnl = 0.0
            for sym, pos in self.positions.items():
                df = enriched_data.get(sym)
                if df is not None and current_time in time_to_idx[sym]:
                    idx = time_to_idx[sym][current_time]
                    px = float(df.iloc[idx]["close"])
                    unrealized_pnl += (pos["quantity"] * px * (1.0 - self.slippage_pct / 100.0) * (1.0 - self.fee_pct / 100.0)) - pos["cost_usdt"]

            total_equity = self.capital + sum(p["cost_usdt"] for p in self.positions.values()) + unrealized_pnl
            self.equity_curve.append({
                "time": current_time,
                "cash": round(self.capital, 2),
                "equity": round(total_equity, 2),
                "open_positions": len(self.positions)
            })

        return self.closed_trades

    def _execute_buy(self, symbol: str, open_price: float, signal: Signal, timestamp: int):
        """Execute buy order with realistic slippage and fee deduction."""
        if len(self.positions) >= self.max_open_positions:
            return
        if self.capital < self.trade_amount:
            return

        exec_price = open_price * (1.0 + self.slippage_pct / 100.0)
        fee = self.trade_amount * (self.fee_pct / 100.0)
        net_usdt = self.trade_amount - fee
        qty = net_usdt / exec_price

        self.capital -= self.trade_amount

        # Calculate initial stop / target
        stop_price = signal.stop_price
        target_price = signal.target_price
        if self.use_original_logic or stop_price is None:
            # Original fallback: 1.5% stop, 2.5% target
            stop_price = exec_price * 0.985
            target_price = exec_price * 1.025

        self.positions[symbol] = {
            "symbol": symbol,
            "setup_id": signal.setup_id or "generic",
            "setup_name": signal.setup_name or "Generic",
            "entry_time": timestamp,
            "entry_price": exec_price,
            "quantity": qty,
            "cost_usdt": self.trade_amount,
            "buy_fee": fee,
            "highest_price": exec_price,
            "initial_stop_price": stop_price,
            "stop_loss_price": stop_price,
            "take_profit_price": target_price,
            "invalidation_price": signal.invalidation_price or stop_price,
            "max_holding_bars": signal.max_holding_bars or 60,
            "bars_held": 0,
            "trailing_active": False,
            "reason": signal.reason
        }

    def _evaluate_position_intrabar(self, pos: Dict[str, Any], bar: pd.Series, slice_df: pd.DataFrame) -> Tuple[Optional[str], float]:
        """
        Evaluate position exit against current bar's Open, High, Low, Close.
        Strict priority:
        1. Conservative tie-breaker: If both SL and TP touched on same bar -> SL hits first!
        2. Hard Stop Loss / Invalidation
        3. Take-Profit Target
        4. ATR Trailing Stop & Break-Even Ratchet
        5. Max holding duration
        6. Strategy custom SELL on bar close
        """
        pos["bars_held"] += 1
        high_p = float(bar["high"])
        low_p = float(bar["low"])
        close_p = float(bar["close"])
        open_p = float(bar["open"])
        curr_atr = float(bar.get("atr", open_p * 0.01))

        entry_px = pos["entry_price"]
        sl = pos["stop_loss_price"]
        tp = pos["take_profit_price"]

        # Track peak price
        if high_p > pos["highest_price"]:
            pos["highest_price"] = high_p

        # 1. Conservative tie-breaker: Stop loss and Take profit both touched inside this candle
        hit_sl = sl is not None and low_p <= sl
        hit_tp = tp is not None and high_p >= tp

        if hit_sl and hit_tp:
            # Conservative rule: Assume stop-loss hits first
            exit_px = min(open_p, sl) if open_p < sl else sl
            return "Conservative: Stop Loss Hit (Intrabar Tie-Break)", exit_px

        # 2. Hard Stop Loss / Invalidation
        if hit_sl:
            exit_px = min(open_p, sl) if open_p < sl else sl
            return f"Hard Stop-Loss Hit (${sl:,.2f})", exit_px

        # 3. Take Profit
        if hit_tp:
            exit_px = max(open_p, tp) if open_p > tp else tp
            return f"Take-Profit Target Hit (${tp:,.2f})", exit_px

        # 4. Trailing Stop & Break-Even Ratchet
        if not self.use_original_logic:
            # Stage 1 Fix: ATR Trail activating at +1R
            init_sl = pos.get("initial_stop_price") or (entry_px * 0.985)
            r_dist = max(0.0001, entry_px - init_sl)
            highest_seen = pos["highest_price"]

            if (highest_seen - entry_px) >= r_dist:
                pos["trailing_active"] = True
                # Break-even lock covering fees + slippage (0.30%)
                be_price = round(entry_px * 1.003, 4)
                if pos["stop_loss_price"] < be_price:
                    pos["stop_loss_price"] = be_price

                # ATR trail: highest - 1.5 * ATR
                trail_stop = round(highest_seen - (1.5 * curr_atr), 4)
                if trail_stop > pos["stop_loss_price"]:
                    pos["stop_loss_price"] = trail_stop

                # Check if current bar low hits trailing stop
                if low_p <= pos["stop_loss_price"]:
                    return f"ATR Trailing Stop Hit (${pos['stop_loss_price']:,.2f})", pos["stop_loss_price"]
        else:
            # Original Flawed Logic: fixed 1% trail above +1% gain
            pnl_pct = ((high_p - entry_px) / entry_px) * 100.0
            if pnl_pct > 1.0:
                highest_seen = pos["highest_price"]
                pullback_pct = ((highest_seen - low_p) / highest_seen) * 100.0
                if pullback_pct >= 1.0:
                    exit_px = highest_seen * 0.99
                    return f"Original Trailing Stop Hit (-1.0%)", exit_px

        # 5. Max Holding Duration Exceeded
        if not self.use_original_logic and pos["bars_held"] >= pos["max_holding_bars"]:
            return f"Max Holding Bars Exceeded ({pos['bars_held']} bars)", close_p

        # 6. Strategy Custom Exit on bar close
        strat_sig = self.strategy.evaluate(slice_df, pos)
        if strat_sig.action == "SELL":
            return f"Strategy Exit: {strat_sig.reason}", close_p

        return None, 0.0

    def _execute_sell(self, symbol: str, exit_price: float, reason: str, timestamp: int):
        """Execute sell order with realistic slippage and fee deduction."""
        pos = self.positions.pop(symbol, None)
        if not pos:
            return

        exec_price = exit_price * (1.0 - self.slippage_pct / 100.0)
        gross_proceeds = pos["quantity"] * exec_price
        sell_fee = gross_proceeds * (self.fee_pct / 100.0)
        net_proceeds = gross_proceeds - sell_fee

        realized_pnl = net_proceeds - pos["cost_usdt"]
        realized_pnl_pct = (realized_pnl / pos["cost_usdt"]) * 100.0
        total_fees = pos["buy_fee"] + sell_fee

        self.capital += net_proceeds

        record = {
            "id": f"BT-TRD-{len(self.closed_trades)+1}",
            "symbol": symbol,
            "setup_id": pos["setup_id"],
            "setup_name": pos["setup_name"],
            "entry_time": pos["entry_time"],
            "exit_time": timestamp,
            "hold_bars": pos["bars_held"],
            "hold_duration_sec": timestamp - pos["entry_time"],
            "entry_price": round(pos["entry_price"], 4),
            "exit_price": round(exec_price, 4),
            "cost_usdt": round(pos["cost_usdt"], 2),
            "proceeds_usdt": round(net_proceeds, 2),
            "realized_pnl": round(realized_pnl, 4),
            "realized_pnl_pct": round(realized_pnl_pct, 2),
            "buy_fee": round(pos["buy_fee"], 4),
            "sell_fee": round(sell_fee, 4),
            "total_fees": round(total_fees, 4),
            "reason": reason
        }
        self.closed_trades.append(record)
