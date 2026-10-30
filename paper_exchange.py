"""
Realistic Paper Trading Exchange Simulator.
Simulates order execution, slippage, Binance-style fees, PnL tracking,
portfolio equity, win rate, and drawdown statistics.
"""

import json
import os
import time
from typing import Dict, Any, List, Optional
from learning_engine import LocalLearningEngine


class PaperExchange:
    def __init__(self, initial_balance: float = 10000.0, fee_pct: float = 0.1, slippage_pct: float = 0.05, state_file: str = "paper_state.json"):
        self.state_file = state_file
        self.initial_balance = initial_balance
        self.fee_pct = fee_pct
        self.slippage_pct = slippage_pct
        self.learning_engine = LocalLearningEngine()

        self.usdt_balance = initial_balance
        self.current_symbol = "BTC/USDT"
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.trades_history: List[Dict[str, Any]] = []

        self.peak_equity = initial_balance
        self.max_drawdown_pct = 0.0
        self.equity_history: List[Dict[str, Any]] = []

        self.load_state()

    @property
    def active_position(self) -> Optional[Dict[str, Any]]:
        """Return position for current symbol or first open position for backwards compatibility."""
        if self.current_symbol in self.positions:
            return self.positions[self.current_symbol]
        if self.positions:
            return next(iter(self.positions.values()))
        return None

    @property
    def asset_balance(self) -> float:
        """Return asset quantity of current active position or 0.0."""
        pos = self.active_position
        return pos.get("quantity", 0.0) if pos else 0.0

    def load_state(self):
        """Load persisted paper trading state if exists."""
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    self.usdt_balance = float(data.get("usdt_balance", self.initial_balance))
                    if "positions" in data and isinstance(data["positions"], dict):
                        self.positions = data["positions"]
                    elif "active_position" in data and data["active_position"]:
                        sym = data["active_position"].get("symbol", "BTC/USDT")
                        self.positions = {sym: data["active_position"]}
                    else:
                        self.positions = {}
                    self.trades_history = data.get("trades_history", [])
                    self.peak_equity = float(data.get("peak_equity", self.initial_balance))
                    self.max_drawdown_pct = float(data.get("max_drawdown_pct", 0.0))
                    self.equity_history = data.get("equity_history", [])
            except Exception:
                pass

    def save_state(self):
        """Persist state to disk."""
        data = {
            "usdt_balance": self.usdt_balance,
            "positions": self.positions,
            "active_position": self.active_position,
            "asset_balance": self.asset_balance,
            "trades_history": self.trades_history,
            "peak_equity": self.peak_equity,
            "max_drawdown_pct": self.max_drawdown_pct,
            "equity_history": self.equity_history
        }
        try:
            with open(self.state_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def reset_wallet(self, initial_balance: float = 10000.0):
        """Reset paper wallet to clean initial state of $10,000.00."""
        self.initial_balance = initial_balance
        self.usdt_balance = initial_balance
        self.positions = {}
        self.trades_history = []
        self.peak_equity = initial_balance
        self.max_drawdown_pct = 0.0
        self.equity_history = []
        self.learning_engine.reset_learning_memory()
        self.save_state()

    def execute_buy(
        self,
        symbol: str,
        market_price: float,
        usdt_amount: float,
        reason: str = "",
        stop_loss_price: Optional[float] = None,
        take_profit_price: Optional[float] = None,
        max_positions: int = 5,
        setup_id: str = "generic",
        invalidation_price: Optional[float] = None,
        max_holding_bars: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute simulated market BUY order for a specific symbol in the portfolio basket."""
        if symbol in self.positions:
            return {"success": False, "error": f"Position already active for {symbol}"}

        if len(self.positions) >= max_positions:
            return {"success": False, "error": f"Fleet at max open capacity ({max_positions} positions active)"}

        if usdt_amount > self.usdt_balance:
            usdt_amount = self.usdt_balance

        if usdt_amount < 10.0:
            return {"success": False, "error": f"Insufficient USDT balance: ${self.usdt_balance:.2f}"}

        # Apply slippage (buy slightly higher than market tick)
        execution_price = market_price * (1 + self.slippage_pct / 100)
        fee = usdt_amount * (self.fee_pct / 100)
        net_usdt = usdt_amount - fee
        qty = net_usdt / execution_price

        self.usdt_balance -= usdt_amount

        pos = {
            "symbol": symbol,
            "setup_id": setup_id,
            "entry_price": round(execution_price, 4),
            "quantity": round(qty, 6),
            "cost_usdt": round(usdt_amount, 2),
            "entry_time": int(time.time() * 1000),
            "highest_price": round(execution_price, 4),
            "initial_stop_price": round(stop_loss_price, 4) if stop_loss_price else None,
            "stop_loss_price": round(stop_loss_price, 4) if stop_loss_price else None,
            "take_profit_price": round(take_profit_price, 4) if take_profit_price else None,
            "invalidation_price": round(invalidation_price, 4) if invalidation_price else (round(stop_loss_price, 4) if stop_loss_price else None),
            "max_holding_bars": max_holding_bars or 60,
            "trailing_active": False,
            "reason": reason
        }
        self.positions[symbol] = pos

        trade_record = {
            "id": f"TRD-{int(time.time() * 1000)}",
            "timestamp": int(time.time() * 1000),
            "symbol": symbol,
            "setup_id": setup_id,
            "side": "BUY",
            "price": round(execution_price, 4),
            "quantity": round(qty, 6),
            "cost_usdt": round(usdt_amount, 2),
            "fee_usdt": round(fee, 4),
            "reason": reason
        }

        self.trades_history.insert(0, trade_record)
        if len(self.trades_history) > 150:
            self.trades_history = self.trades_history[:150]

        self.save_state()
        return {"success": True, "trade": trade_record, "position": pos}

    def execute_sell(self, symbol: str, market_price: float, reason: str = "") -> Dict[str, Any]:
        """Execute simulated market SELL order closing the specified coin position."""
        target_sym = symbol
        if target_sym not in self.positions:
            if self.positions:
                target_sym = next(iter(self.positions.keys()))
            else:
                return {"success": False, "error": f"No active position for {symbol} to close"}

        pos = self.positions[target_sym]
        qty = pos["quantity"]
        entry_price = pos["entry_price"]
        cost_usdt = pos["cost_usdt"]

        # Apply slippage (sell slightly lower than market tick)
        execution_price = market_price * (1 - self.slippage_pct / 100)
        gross_proceeds = qty * execution_price
        fee = gross_proceeds * (self.fee_pct / 100)
        net_proceeds = gross_proceeds - fee

        realized_pnl = net_proceeds - cost_usdt
        realized_pnl_pct = (realized_pnl / cost_usdt) * 100 if cost_usdt > 0 else 0.0

        self.usdt_balance += net_proceeds
        del self.positions[target_sym]

        trade_record = {
            "id": f"TRD-{int(time.time() * 1000)}",
            "timestamp": int(time.time() * 1000),
            "symbol": target_sym,
            "setup_id": pos.get("setup_id", "ema_rsi"),
            "side": "SELL",
            "price": round(execution_price, 4),
            "quantity": round(qty, 6),
            "cost_usdt": round(cost_usdt, 2),
            "proceeds_usdt": round(net_proceeds, 2),
            "fee_usdt": round(fee, 4),
            "realized_pnl": round(realized_pnl, 2),
            "realized_pnl_pct": round(realized_pnl_pct, 2),
            "hold_duration_sec": int((time.time() * 1000 - pos["entry_time"]) / 1000),
            "reason": reason
        }

        self.trades_history.insert(0, trade_record)
        if len(self.trades_history) > 150:
            self.trades_history = self.trades_history[:150]

        # Ingest trade into Local Learning Engine to adaptively update setup weights
        self.learning_engine.record_closed_trade(trade_record)

        self.save_state()
        return {"success": True, "trade": trade_record}

    def get_portfolio_summary(self, current_prices: Any) -> Dict[str, Any]:
        """Compute live equity across all open basket positions, unrealized PnL, and performance statistics."""
        # Handle current_prices as dict or single float
        prices_map: Dict[str, float] = {}
        if isinstance(current_prices, dict):
            prices_map = current_prices
        elif isinstance(current_prices, (int, float)):
            prices_map = {self.current_symbol: float(current_prices)}

        total_positions_value = 0.0
        active_positions_list: List[Dict[str, Any]] = []

        for sym, pos in list(self.positions.items()):
            px = prices_map.get(sym, pos["entry_price"])
            if px <= 0:
                px = pos["entry_price"]

            pos_val = pos["quantity"] * px
            cost = pos["cost_usdt"]
            unrealized_pnl = pos_val - cost
            unrealized_pnl_pct = (unrealized_pnl / cost) * 100 if cost > 0 else 0.0

            # Update highest price for trailing stop tracking
            if px > pos.get("highest_price", pos["entry_price"]):
                pos["highest_price"] = px

            active_positions_list.append({
                **pos,
                "current_price": round(px, 4),
                "market_value": round(pos_val, 2),
                "unrealized_pnl": round(unrealized_pnl, 2),
                "unrealized_pnl_pct": round(unrealized_pnl_pct, 2)
            })
            total_positions_value += pos_val

        total_equity = self.usdt_balance + total_positions_value

        # Update Peak and Drawdown
        if total_equity > self.peak_equity:
            self.peak_equity = total_equity
        drawdown_pct = 0.0
        if self.peak_equity > 0:
            drawdown_pct = ((self.peak_equity - total_equity) / self.peak_equity) * 100
            if drawdown_pct > self.max_drawdown_pct:
                self.max_drawdown_pct = drawdown_pct

        # Primary active position for single-card display
        primary_pos = active_positions_list[0] if active_positions_list else None

        # Calculate Closed Trades Metrics
        closed_trades = [t for t in self.trades_history if t.get("side") == "SELL" and "realized_pnl" in t]
        total_closed = len(closed_trades)
        winning_trades = [t for t in closed_trades if t["realized_pnl"] > 0]
        losing_trades = [t for t in closed_trades if t["realized_pnl"] <= 0]

        win_rate = (len(winning_trades) / total_closed * 100) if total_closed > 0 else 0.0
        gross_profit = sum(t["realized_pnl"] for t in winning_trades)
        gross_loss = abs(sum(t["realized_pnl"] for t in losing_trades))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        total_realized_pnl = sum(t["realized_pnl"] for t in closed_trades)
        total_pnl_pct = ((total_equity - self.initial_balance) / self.initial_balance) * 100

        # Record equity snapshot for dynamic equity curve visualization
        now_ts = int(time.time() * 1000)
        if not self.equity_history or (now_ts - self.equity_history[-1]["time"] >= 10000) or (abs(total_equity - self.equity_history[-1]["equity"]) > 0.5):
            self.equity_history.append({
                "time": now_ts,
                "equity": round(total_equity, 2),
                "drawdown": round(drawdown_pct, 2),
                "pnl": round(total_realized_pnl, 2)
            })
            if len(self.equity_history) > 200:
                self.equity_history = self.equity_history[-200:]

        return {
            "initial_balance": round(self.initial_balance, 2),
            "usdt_balance": round(self.usdt_balance, 2),
            "total_positions_value": round(total_positions_value, 2),
            "total_equity": round(total_equity, 2),
            "total_realized_pnl": round(total_realized_pnl, 2),
            "total_pnl_pct": round(total_pnl_pct, 2),
            "win_rate_pct": round(win_rate, 1),
            "profit_factor": round(profit_factor, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "total_trades": len(self.trades_history),
            "winning_trades_count": len(winning_trades),
            "losing_trades_count": len(losing_trades),
            "active_position": primary_pos,
            "active_positions": active_positions_list,
            "open_positions_count": len(active_positions_list),
            "asset_balance": round(self.asset_balance, 6),
            "equity_history": self.equity_history[-60:],
            "recent_trades": self.trades_history[:15]
        }

    def get_daily_report(self) -> Dict[str, Any]:
        """Generate comprehensive 24-hour test session analytics for review before real money."""
        summary = self.get_portfolio_summary(self.active_position["entry_price"] if self.active_position else self.initial_balance)
        closed_trades = [t for t in self.trades_history if t.get("side") == "SELL" and "realized_pnl" in t]

        bot_breakdown = {
            "orb": {"name": "ORB Breakout", "trades": 0, "wins": 0, "pnl": 0.0},
            "bull_flag": {"name": "Bull Flag Momentum", "trades": 0, "wins": 0, "pnl": 0.0},
            "oversold_bounce": {"name": "Oversold Bounce", "trades": 0, "wins": 0, "pnl": 0.0},
            "reclaim_ma20": {"name": "20-MA Reclaim", "trades": 0, "wins": 0, "pnl": 0.0},
            "bollinger_reversion": {"name": "Range Hunter", "trades": 0, "wins": 0, "pnl": 0.0},
            "ema_rsi": {"name": "EMA 9/21 Trend", "trades": 0, "wins": 0, "pnl": 0.0}
        }

        best_trade = None
        worst_trade = None

        for t in closed_trades:
            pnl = float(t.get("realized_pnl", 0.0))
            if best_trade is None or pnl > float(best_trade.get("realized_pnl", -999999)):
                best_trade = t
            if worst_trade is None or pnl < float(worst_trade.get("realized_pnl", 999999)):
                worst_trade = t

            r = str(t.get("reason", "")).lower()
            if "orb" in r:
                bot_breakdown["orb"]["trades"] += 1
                bot_breakdown["orb"]["pnl"] += pnl
                if pnl > 0: bot_breakdown["orb"]["wins"] += 1
            elif "flag" in r:
                bot_breakdown["bull_flag"]["trades"] += 1
                bot_breakdown["bull_flag"]["pnl"] += pnl
                if pnl > 0: bot_breakdown["bull_flag"]["wins"] += 1
            elif "oversold" in r or "bounce" in r:
                bot_breakdown["oversold_bounce"]["trades"] += 1
                bot_breakdown["oversold_bounce"]["pnl"] += pnl
                if pnl > 0: bot_breakdown["oversold_bounce"]["wins"] += 1
            elif "20-ma" in r or "reclaim" in r:
                bot_breakdown["reclaim_ma20"]["trades"] += 1
                bot_breakdown["reclaim_ma20"]["pnl"] += pnl
                if pnl > 0: bot_breakdown["reclaim_ma20"]["wins"] += 1
            elif "range" in r or "hunter" in r or "bb mid" in r:
                bot_breakdown["bollinger_reversion"]["trades"] += 1
                bot_breakdown["bollinger_reversion"]["pnl"] += pnl
                if pnl > 0: bot_breakdown["bollinger_reversion"]["wins"] += 1
            else:
                bot_breakdown["ema_rsi"]["trades"] += 1
                bot_breakdown["ema_rsi"]["pnl"] += pnl
                if pnl > 0: bot_breakdown["ema_rsi"]["wins"] += 1

        first_trade_time = self.trades_history[-1]["timestamp"] if self.trades_history else int(time.time() * 1000)
        session_elapsed_sec = max(1, int((time.time() * 1000 - first_trade_time) / 1000))
        hours = session_elapsed_sec // 3600
        mins = (session_elapsed_sec % 3600) // 60

        # Ready for real money assessment
        is_ready = summary["total_realized_pnl"] >= 0 and summary["win_rate_pct"] >= 50.0 and len(closed_trades) >= 2

        return {
            "session_duration_str": f"{hours}h {mins}m",
            "session_hours": round(session_elapsed_sec / 3600, 2),
            "initial_balance": summary["initial_balance"],
            "current_equity": summary["total_equity"],
            "total_realized_pnl": summary["total_realized_pnl"],
            "total_pnl_pct": summary["total_pnl_pct"],
            "win_rate_pct": summary["win_rate_pct"],
            "profit_factor": summary["profit_factor"],
            "max_drawdown_pct": summary["max_drawdown_pct"],
            "total_trades": len(self.trades_history),
            "closed_trades_count": len(closed_trades),
            "winning_trades_count": summary["winning_trades_count"],
            "losing_trades_count": summary["losing_trades_count"],
            "best_trade": best_trade,
            "worst_trade": worst_trade,
            "bot_breakdown": bot_breakdown,
            "ready_for_real_money": is_ready,
            "learning_insights": self.learning_engine.get_learning_insights()
        }

    def generate_trades_csv(self) -> str:
        """Export all executed trades to CSV spreadsheet format."""
        header = "Trade_ID,Timestamp,DateTime,Symbol,Side,Price,Quantity,Cost_USDT,Proceeds_USDT,Fee_USDT,Realized_PnL,Realized_PnL_Pct,Hold_Sec,Reason"
        lines = [header]
        for t in reversed(self.trades_history):
            dt_str = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(t.get('timestamp', 0) / 1000))
            lines.append(
                f"{t.get('id')},{t.get('timestamp')},{dt_str},{t.get('symbol')},{t.get('side')},"
                f"{t.get('price')},{t.get('quantity')},{t.get('cost_usdt', '')},{t.get('proceeds_usdt', '')},"
                f"{t.get('fee_usdt', '')},{t.get('realized_pnl', '')},{t.get('realized_pnl_pct', '')},"
                f"{t.get('hold_duration_sec', '')},\"{t.get('reason', '')}\""
            )
        return "\n".join(lines)

