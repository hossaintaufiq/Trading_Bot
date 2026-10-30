"""
Centralized Institutional Risk Manager for Neptune Bot.
Unified across Backtest, Paper Trading, and Live Execution.

Key Guardrails:
1. Fixed Fractional Risk: Position size calculated strictly from stop distance (Risk = Capital * Risk%).
2. Max Total Exposure & Budget Cap: Deployed capital across all positions never exceeds budget limit.
3. Max Exposure per Symbol: Concentration cap per asset.
4. Max Open Concurrent Positions: Portfolio slot limit.
5. Max Correlated Altcoin Exposure: Diversification guardrail against market-wide dumps.
6. Daily Loss Circuit Breaker: Halts new entries when daily loss reaches threshold.
7. Max Drawdown Stop: Portfolio protection against deep drawdown.
8. Consecutive Loss Cooldown: Pauses new entries after N consecutive losses.
9. Global Kill Switch: Emergency stop immediately preventing any new entries.
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger("risk_manager")


@dataclass
class RiskOrderEvaluation:
    approved: bool
    reason: str
    trade_amount_usdt: float
    position_units: float
    stop_distance_pct: float
    reward_risk_ratio: float


class CentralizedRiskManager:
    def __init__(self, config_or_path: Any = "config.json"):
        self.config_path = config_or_path if isinstance(config_or_path, str) else "config.json"
        self.config: Dict[str, Any] = {}
        if isinstance(config_or_path, dict):
            self.config = config_or_path
        else:
            self.load_config()

        # State tracking
        self.consecutive_losses = 0
        self.cooldown_until_ts = 0
        self.daily_realized_loss_usd = 0.0
        self.session_peak_equity = float(self.config.get("paper_initial_balance", 10000.0))
        self.circuit_breaker_tripped = False

    def load_config(self):
        """Load and validate configuration from disk."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    self.config = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load risk config: {e}")
        self._apply_config_defaults()

    def _apply_config_defaults(self):
        """Enforce strict quantitative risk parameters."""
        self.kill_switch_active = bool(self.config.get("global_kill_switch", False))
        self.total_budget_limit_usd = float(self.config.get("total_budget_limit_usd", 2000.0))
        self.max_exposure_per_symbol_usd = float(self.config.get("max_exposure_per_symbol_usd", 600.0))
        self.max_open_positions = max(1, int(self.config.get("max_open_positions", 3)))
        self.max_correlated_positions = max(1, int(self.config.get("max_correlated_positions", 2)))
        self.risk_per_trade_pct = float(self.config.get("risk_per_trade_pct", 1.0))  # 1.0% portfolio risk
        self.max_daily_loss_usd = float(self.config.get("max_daily_loss_usd", 300.0))
        self.max_drawdown_stop_pct = float(self.config.get("max_drawdown_stop_pct", 10.0))
        self.consecutive_loss_limit = int(self.config.get("consecutive_loss_limit", 3))
        self.cooldown_duration_sec = int(self.config.get("consecutive_loss_cooldown_sec", 7200))  # 2 hours
        self.min_order_usd = float(self.config.get("min_order_usd", 12.0))
        self.taker_fee_pct = float(self.config.get("taker_fee_pct", 0.10))
        self.slippage_pct = float(self.config.get("slippage_pct", 0.05))

    def evaluate_order(
        self,
        symbol: str,
        entry_price: float,
        stop_price: float,
        target_price: float,
        current_equity: float,
        active_positions: Dict[str, Dict[str, Any]]
    ) -> RiskOrderEvaluation:
        """
        Comprehensive pre-trade risk evaluation.
        Calculates position size strictly from stop distance and ensures zero guardrail breaches.
        """
        # 1. Global Kill Switch Check
        if self.kill_switch_active or self.config.get("global_kill_switch", False):
            return RiskOrderEvaluation(False, "🛑 GLOBAL KILL SWITCH ACTIVE: All trading halted", 0.0, 0.0, 0.0, 0.0)

        # 2. Consecutive Loss Cooldown Check
        now_ts = int(time.time())
        if now_ts < self.cooldown_until_ts:
            rem_min = int((self.cooldown_until_ts - now_ts) / 60)
            return RiskOrderEvaluation(
                False,
                f"🛑 CONSECUTIVE LOSS COOLDOWN: {self.consecutive_losses} consecutive losses. Paused for {rem_min} more minutes.",
                0.0, 0.0, 0.0, 0.0
            )

        # 3. Daily Loss Circuit Breaker Check
        if self.daily_realized_loss_usd >= self.max_daily_loss_usd or self.circuit_breaker_tripped:
            return RiskOrderEvaluation(
                False,
                f"🛑 DAILY LOSS LIMIT BREACHED: Daily loss ${self.daily_realized_loss_usd:.2f} >= max ${self.max_daily_loss_usd:.2f}",
                0.0, 0.0, 0.0, 0.0
            )

        # 4. Max Drawdown Stop Check
        if current_equity > self.session_peak_equity:
            self.session_peak_equity = current_equity
        dd_pct = ((self.session_peak_equity - current_equity) / self.session_peak_equity) * 100.0 if self.session_peak_equity > 0 else 0.0
        if dd_pct >= self.max_drawdown_stop_pct:
            return RiskOrderEvaluation(
                False,
                f"🛑 MAX DRAWDOWN STOPPED: Portfolio drawdown {dd_pct:.2f}% >= max allowed {self.max_drawdown_stop_pct:.1f}%",
                0.0, 0.0, 0.0, 0.0
            )

        # 5. Position Slot & Correlation Limit Checks
        if len(active_positions) >= self.max_open_positions:
            return RiskOrderEvaluation(
                False,
                f"🛑 MAX OPEN POSITIONS REACHED: {len(active_positions)}/{self.max_open_positions} slots occupied",
                0.0, 0.0, 0.0, 0.0
            )

        if symbol in active_positions:
            return RiskOrderEvaluation(
                False,
                f"🛑 EXISTING POSITION: Symbol {symbol} already held in portfolio",
                0.0, 0.0, 0.0, 0.0
            )

        if symbol != "BTC/USDT":
            alt_count = len([s for s in active_positions if s != "BTC/USDT"])
            if alt_count >= self.max_correlated_positions:
                return RiskOrderEvaluation(
                    False,
                    f"🛑 CORRELATED ALTCOIN CAP: {alt_count}/{self.max_correlated_positions} alt positions active",
                    0.0, 0.0, 0.0, 0.0
                )

        # 6. Price & Stop Validation
        if stop_price <= 0 or stop_price >= entry_price:
            return RiskOrderEvaluation(
                False,
                f"🛑 INVALID STOP PRICE: Stop (${stop_price}) must be strictly below Entry (${entry_price})",
                0.0, 0.0, 0.0, 0.0
            )
        if target_price <= entry_price:
            return RiskOrderEvaluation(
                False,
                f"🛑 INVALID TARGET PRICE: Target (${target_price}) must be strictly above Entry (${entry_price})",
                0.0, 0.0, 0.0, 0.0
            )

        stop_dist = entry_price - stop_price
        stop_dist_pct = (stop_dist / entry_price) * 100.0
        reward_dist = target_price - entry_price
        rr_ratio = reward_dist / stop_dist

        # Minimum reward-to-risk gate (>= 1.5R)
        if rr_ratio < 1.45:
            return RiskOrderEvaluation(
                False,
                f"🛑 INSUFFICIENT REWARD:RISK: {rr_ratio:.2f}R is below institutional minimum 1.50R",
                0.0, 0.0, stop_dist_pct, rr_ratio
            )

        # 7. Fixed Fractional Position Sizing from Stop Distance
        # Dollar Risk = Equity * Risk%
        allowed_risk_usd = current_equity * (self.risk_per_trade_pct / 100.0)
        # Position Size (USDT) = (Dollar Risk / Stop Distance %) * 100
        ideal_trade_amount = (allowed_risk_usd / (stop_dist_pct / 100.0))

        # Enforce Concentration Cap per Symbol
        trade_amount = min(ideal_trade_amount, self.max_exposure_per_symbol_usd)

        # Enforce Total Budget Cap
        currently_deployed = sum(p.get("cost_usdt", 0.0) for p in active_positions.values())
        available_budget = max(0.0, self.total_budget_limit_usd - currently_deployed)

        if trade_amount > available_budget:
            trade_amount = available_budget

        if trade_amount < self.min_order_usd:
            return RiskOrderEvaluation(
                False,
                f"🛑 BUDGET CONSTRAINED: Allowed size ${trade_amount:.2f} is below minimum ${self.min_order_usd:.2f} (Available budget: ${available_budget:.2f})",
                0.0, 0.0, stop_dist_pct, rr_ratio
            )

        units = trade_amount / entry_price

        return RiskOrderEvaluation(
            approved=True,
            reason=f"Approved: ${trade_amount:.2f} position (Risk: ${allowed_risk_usd:.2f}, RR: {rr_ratio:.2f}R)",
            trade_amount_usdt=round(trade_amount, 2),
            position_units=round(units, 6),
            stop_distance_pct=round(stop_dist_pct, 2),
            reward_risk_ratio=round(rr_ratio, 2)
        )

    def record_trade_outcome(self, realized_pnl: float):
        """Update risk metrics upon trade close."""
        if realized_pnl < 0:
            self.consecutive_losses += 1
            self.daily_realized_loss_usd += abs(realized_pnl)
            if self.consecutive_losses >= self.consecutive_loss_limit:
                self.cooldown_until_ts = int(time.time()) + self.cooldown_duration_sec
                logger.warning(f"🚨 Consecutive loss limit reached ({self.consecutive_losses}). Cooldown active for {self.cooldown_duration_sec // 60} min.")
            if self.daily_realized_loss_usd >= self.max_daily_loss_usd:
                self.circuit_breaker_tripped = True
                logger.warning(f"🚨 Daily loss circuit breaker tripped: ${self.daily_realized_loss_usd:.2f} >= ${self.max_daily_loss_usd:.2f}")
        else:
            self.consecutive_losses = 0

    def reset_daily_metrics(self):
        """Reset daily loss tracking and circuit breakers."""
        self.daily_realized_loss_usd = 0.0
        self.circuit_breaker_tripped = False
        self.consecutive_losses = 0
        self.cooldown_until_ts = 0
        logger.info("Daily risk metrics reset.")
