"""
Local Learning & Adaptive Memory Engine for Neptune Bot.
Permanently logs trade executions, evaluates setup efficacy, and computes
adaptive Bayesian confidence multipliers to organically favor winning strategies
in current market conditions while dampening underperforming setups.
"""

import json
import logging
import os
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger("learning_engine")


class LocalLearningEngine:
    """
    Autonomous local learning system that analyzes trade outcomes
    and optimizes fleet strategy weights based on real market results.
    """

    def __init__(self, storage_path: str = "local_learning_memory.json"):
        self.storage_path = storage_path
        self.memory: Dict[str, Any] = self._load_memory()

    def _default_memory(self) -> Dict[str, Any]:
        """Initialize clean local learning structure."""
        return {
            "version": "1.0",
            "last_updated": int(time.time() * 1000),
            "total_trades_analyzed": 0,
            "overall_win_rate_pct": 0.0,
            "overall_profit_factor": 1.0,
            "setups": {
                "orb": {
                    "name": "ORB Breakout",
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate_pct": 50.0,
                    "total_pnl": 0.0,
                    "gross_profit": 0.0,
                    "gross_loss": 0.0,
                    "profit_factor": 1.0,
                    "avg_win_usd": 0.0,
                    "avg_loss_usd": 0.0,
                    "consecutive_wins": 0,
                    "consecutive_losses": 0,
                    "learned_weight": 1.0,
                    "status": "NORMAL"
                },
                "bull_flag": {
                    "name": "Bull Flag Momentum",
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate_pct": 50.0,
                    "total_pnl": 0.0,
                    "gross_profit": 0.0,
                    "gross_loss": 0.0,
                    "profit_factor": 1.0,
                    "avg_win_usd": 0.0,
                    "avg_loss_usd": 0.0,
                    "consecutive_wins": 0,
                    "consecutive_losses": 0,
                    "learned_weight": 1.0,
                    "status": "NORMAL"
                },
                "oversold_bounce": {
                    "name": "Oversold Bounce",
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate_pct": 50.0,
                    "total_pnl": 0.0,
                    "gross_profit": 0.0,
                    "gross_loss": 0.0,
                    "profit_factor": 1.0,
                    "avg_win_usd": 0.0,
                    "avg_loss_usd": 0.0,
                    "consecutive_wins": 0,
                    "consecutive_losses": 0,
                    "learned_weight": 1.0,
                    "status": "NORMAL"
                },
                "reclaim_ma20": {
                    "name": "20-MA Reclaim",
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate_pct": 50.0,
                    "total_pnl": 0.0,
                    "gross_profit": 0.0,
                    "gross_loss": 0.0,
                    "profit_factor": 1.0,
                    "avg_win_usd": 0.0,
                    "avg_loss_usd": 0.0,
                    "consecutive_wins": 0,
                    "consecutive_losses": 0,
                    "learned_weight": 1.0,
                    "status": "NORMAL"
                },
                "ema_rsi": {
                    "name": "EMA 9/21 Trend",
                    "trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate_pct": 50.0,
                    "total_pnl": 0.0,
                    "gross_profit": 0.0,
                    "gross_loss": 0.0,
                    "profit_factor": 1.0,
                    "avg_win_usd": 0.0,
                    "avg_loss_usd": 0.0,
                    "consecutive_wins": 0,
                    "consecutive_losses": 0,
                    "learned_weight": 1.0,
                    "status": "NORMAL"
                }
            },
            "recent_trade_memories": []
        }

    def _load_memory(self) -> Dict[str, Any]:
        """Load persistent memory file or create default."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                    # Validate setups key presence
                    if "setups" in data:
                        return data
            except Exception as e:
                logger.error(f"Error reading local learning memory: {e}")
        default_mem = self._default_memory()
        self._save_memory(default_mem)
        return default_mem

    def _save_memory(self, memory: Optional[Dict[str, Any]] = None):
        """Save updated memory to local JSON storage."""
        target = memory or self.memory
        target["last_updated"] = int(time.time() * 1000)
        try:
            with open(self.storage_path, "w") as f:
                json.dump(target, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save local learning memory: {e}")

    def identify_setup_key(self, reason: str, setup_name: str = "") -> str:
        """Map trade text or signal name to standard setup key."""
        text = f"{reason} {setup_name}".lower()
        if "orb" in text:
            return "orb"
        elif "flag" in text:
            return "bull_flag"
        elif "oversold" in text or "bounce" in text:
            return "oversold_bounce"
        elif "20-ma" in text or "reclaim" in text:
            return "reclaim_ma20"
        return "ema_rsi"

    def record_closed_trade(self, trade: Dict[str, Any], market_context: Optional[Dict[str, Any]] = None):
        """
        Ingest a closed trade into local learning memory, update Bayesian statistics,
        and adaptively re-weight strategy priorities.
        """
        pnl = float(trade.get("realized_pnl", 0.0))
        pnl_pct = float(trade.get("realized_pnl_pct", 0.0))
        reason = str(trade.get("reason", ""))
        setup_key = self.identify_setup_key(reason)

        if setup_key not in self.memory["setups"]:
            setup_key = "ema_rsi"

        s = self.memory["setups"][setup_key]
        is_win = pnl > 0

        # Update setup counters
        s["trades"] += 1
        s["total_pnl"] = round(s["total_pnl"] + pnl, 2)

        if is_win:
            s["wins"] += 1
            s["gross_profit"] = round(s["gross_profit"] + pnl, 2)
            s["consecutive_wins"] += 1
            s["consecutive_losses"] = 0
        else:
            s["losses"] += 1
            s["gross_loss"] = round(s["gross_loss"] + abs(pnl), 2)
            s["consecutive_losses"] += 1
            s["consecutive_wins"] = 0

        # Recompute Win Rate and Profit Factor
        s["win_rate_pct"] = round((s["wins"] / s["trades"]) * 100, 1) if s["trades"] > 0 else 50.0
        s["avg_win_usd"] = round(s["gross_profit"] / s["wins"], 2) if s["wins"] > 0 else 0.0
        s["avg_loss_usd"] = round(s["gross_loss"] / s["losses"], 2) if s["losses"] > 0 else 0.0

        if s["gross_loss"] > 0:
            s["profit_factor"] = round(s["gross_profit"] / s["gross_loss"], 2)
        else:
            s["profit_factor"] = round(s["gross_profit"], 2) if s["gross_profit"] > 0 else 1.0

        # Compute Adaptive Learned Weight (0.65 to 1.35)
        # Bayesian prior: blend with initial prior of 1.0 over first 4 trades
        n = s["trades"]
        prior_weight = 1.0
        prior_strength = 4.0

        raw_factor = 1.0 + ((s["win_rate_pct"] - 50.0) / 100.0) * 0.5 + (min(2.5, s["profit_factor"]) - 1.0) * 0.15

        # Penalty for consecutive losing streaks in current regime
        if s["consecutive_losses"] >= 2:
            raw_factor -= 0.12 * min(3, s["consecutive_losses"])
        elif s["consecutive_wins"] >= 2:
            raw_factor += 0.08 * min(3, s["consecutive_wins"])

        # Bayesian shrinkage
        blended_weight = ((n * raw_factor) + (prior_strength * prior_weight)) / (n + prior_strength)
        blended_weight = max(0.65, min(1.35, blended_weight))
        s["learned_weight"] = round(blended_weight, 2)

        # Status badge
        if s["learned_weight"] >= 1.15:
            s["status"] = "BOOSTED"
        elif s["learned_weight"] <= 0.85:
            s["status"] = "DEFENSIVE"
        else:
            s["status"] = "NORMAL"

        # Update overall metrics
        self.memory["total_trades_analyzed"] += 1
        all_wins = sum(setup["wins"] for setup in self.memory["setups"].values())
        all_trades = sum(setup["trades"] for setup in self.memory["setups"].values())
        total_gp = sum(setup["gross_profit"] for setup in self.memory["setups"].values())
        total_gl = sum(setup["gross_loss"] for setup in self.memory["setups"].values())

        self.memory["overall_win_rate_pct"] = round((all_wins / all_trades) * 100, 1) if all_trades > 0 else 0.0
        self.memory["overall_profit_factor"] = round(total_gp / total_gl, 2) if total_gl > 0 else (round(total_gp, 2) if total_gp > 0 else 1.0)

        # Record trade memory with context
        trade_mem = {
            "timestamp": trade.get("timestamp", int(time.time() * 1000)),
            "setup_key": setup_key,
            "setup_name": s["name"],
            "pnl": pnl,
            "pnl_pct": pnl_pct,
            "is_win": is_win,
            "hold_duration_sec": trade.get("hold_duration_sec", 0),
            "new_weight": s["learned_weight"],
            "market_context": market_context or {}
        }
        self.memory["recent_trade_memories"].insert(0, trade_mem)
        if len(self.memory["recent_trade_memories"]) > 50:
            self.memory["recent_trade_memories"] = self.memory["recent_trade_memories"][:50]

        self._save_memory()
        logger.info(f"Learned from {s['name']}: PnL=${pnl:+.2f} | New Weight: {s['learned_weight']}x ({s['status']})")

    def get_setup_weight(self, setup_key: str) -> float:
        """Retrieve dynamic learned confidence multiplier for given setup."""
        if setup_key in self.memory["setups"]:
            return float(self.memory["setups"][setup_key].get("learned_weight", 1.0))
        return 1.0

    def get_all_weights(self) -> Dict[str, float]:
        """Return dict of setup_key -> learned_weight."""
        return {k: float(v.get("learned_weight", 1.0)) for k, v in self.memory["setups"].items()}

    def get_learning_insights(self) -> Dict[str, Any]:
        """Return full structured learning insights for UI and diagnostics."""
        weights = self.get_all_weights()
        best_setup = max(self.memory["setups"].items(), key=lambda x: x[1].get("total_pnl", 0.0))

        return {
            "total_trades_analyzed": self.memory.get("total_trades_analyzed", 0),
            "overall_win_rate_pct": self.memory.get("overall_win_rate_pct", 0.0),
            "overall_profit_factor": self.memory.get("overall_profit_factor", 1.0),
            "setups": self.memory.get("setups", {}),
            "weights": weights,
            "top_performing_setup": {
                "key": best_setup[0],
                "name": best_setup[1]["name"],
                "pnl": best_setup[1]["total_pnl"],
                "win_rate": best_setup[1]["win_rate_pct"],
                "weight": best_setup[1]["learned_weight"]
            },
            "recent_memories": self.memory.get("recent_trade_memories", [])[:10],
            "is_learning_active": True
        }

    def reset_learning_memory(self):
        """Reset local learning memory to default state."""
        self.memory = self._default_memory()
        self._save_memory()
        logger.info("Local learning memory reset to defaults.")
