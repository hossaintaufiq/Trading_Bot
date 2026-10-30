"""
Institutional Money Management & Capital Allocation Engine for Neptune Bot.
Enforces strict portfolio-level budget constraints, dynamic slot division,
risk-based position sizing, break-even profit locking, and daily loss circuit breakers.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger("money_manager")


@dataclass
class AllocationResult:
    approved: bool
    reason: str
    trade_amount_usdt: float
    total_budget_limit: float
    total_deployed_usdt: float
    available_budget_usdt: float
    slot_budget_usdt: float


class MoneyManager:
    """
    Coordinates portfolio capital allocation and risk guardrails.
    Ensures total deployed capital never breaches user-defined limits and
    intelligently divides capital among active sub-bots and open positions.
    """

    def __init__(self, config: Dict[str, Any]):
        self.update_config(config)
        self.session_realized_loss = 0.0
        self.circuit_breaker_tripped = False

    def update_config(self, config: Dict[str, Any]):
        """Update money management parameters from active config."""
        self.config = config
        # Total Capital Budget Limit (user limit for total active spend across all bots)
        self.total_budget_limit = float(config.get("total_budget_limit_usd", 200.0))
        # Allocation Division Mode: "EQUAL_SPLIT", "CONFIDENCE_WEIGHTED", "VOLATILITY_PARITY"
        self.allocation_mode = config.get("budget_allocation_mode", "EQUAL_SPLIT")
        # Max open concurrent positions
        self.max_open_positions = max(1, int(config.get("max_open_positions", 4)))
        # Circuit Breaker: Max session loss in USD before halting entries
        self.max_session_loss_usd = float(config.get("max_session_loss_usd", 25.0))
        # Break-Even Lock: Auto-moves stop loss to Entry + Fee once target distance is gained
        self.breakeven_lock_enabled = bool(config.get("breakeven_lock_enabled", True))
        self.breakeven_trigger_pct = float(config.get("breakeven_trigger_pct", 1.0))
        # Minimum single order size ($10 standard Binance minimum)
        self.min_order_usd = float(config.get("min_order_usd", 12.0))
        # Slippage and taker fee
        self.fee_pct = float(config.get("taker_fee_pct", 0.1))
        self.slippage_pct = float(config.get("slippage_pct", 0.05))

    def reset_session_loss(self):
        """Reset session loss tracker and untrip circuit breaker."""
        self.session_realized_loss = 0.0
        self.circuit_breaker_tripped = False
        logger.info("MoneyManager session loss reset. Circuit breaker disengaged.")

    def record_closed_trade_pnl(self, realized_pnl: float):
        """Update session loss tracker when a trade closes."""
        if realized_pnl < 0:
            self.session_realized_loss += abs(realized_pnl)
            if self.session_realized_loss >= self.max_session_loss_usd:
                self.circuit_breaker_tripped = True
                logger.warning(
                    f"🚨 CIRCUIT BREAKER TRIPPED! Session loss ${self.session_realized_loss:.2f} "
                    f"exceeded maximum limit of ${self.max_session_loss_usd:.2f}."
                )

    def calculate_trade_allocation(
        self,
        symbol: str,
        current_price: float,
        active_positions: Dict[str, Dict[str, Any]],
        wallet_usdt_balance: float,
        setup_weight: float = 1.0,
        coin_atr_pct: float = 1.0
    ) -> AllocationResult:
        """
        Calculates exact allowed USDT trade amount for an incoming setup signal.
        Ensures:
        1. Circuit breaker is not tripped
        2. Total deployed capital across basket + new trade <= total_budget_limit
        3. Budget is intelligently divided among slots
        """
        # 1. Circuit Breaker Check
        if self.circuit_breaker_tripped:
            return AllocationResult(
                approved=False,
                reason=f"Circuit Breaker Tripped: Session loss (${self.session_realized_loss:.2f}) reached limit (${self.max_session_loss_usd:.2f})",
                trade_amount_usdt=0.0,
                total_budget_limit=self.total_budget_limit,
                total_deployed_usdt=0.0,
                available_budget_usdt=0.0,
                slot_budget_usdt=0.0
            )

        # 2. Portfolio Capacity Check
        current_open_count = len(active_positions)
        if current_open_count >= self.max_open_positions:
            return AllocationResult(
                approved=False,
                reason=f"Fleet Basket Full ({current_open_count}/{self.max_open_positions} positions active)",
                trade_amount_usdt=0.0,
                total_budget_limit=self.total_budget_limit,
                total_deployed_usdt=0.0,
                available_budget_usdt=0.0,
                slot_budget_usdt=0.0
            )

        # 3. Calculate Deployed Capital & Remaining Budget
        total_deployed = sum(float(pos.get("cost_usdt", 0.0)) for pos in active_positions.values())
        available_budget = max(0.0, self.total_budget_limit - total_deployed)

        # Also cannot exceed actual wallet cash
        available_cash = max(0.0, wallet_usdt_balance * 0.98)  # keep 2% cash buffer
        effective_pool = min(available_budget, available_cash)

        if effective_pool < self.min_order_usd:
            return AllocationResult(
                approved=False,
                reason=f"Total Budget Depleted: Deployed ${total_deployed:,.2f} of ${self.total_budget_limit:,.2f} limit (Remaining: ${available_budget:,.2f})",
                trade_amount_usdt=0.0,
                total_budget_limit=self.total_budget_limit,
                total_deployed_usdt=total_deployed,
                available_budget_usdt=available_budget,
                slot_budget_usdt=0.0
            )

        # 4. Divide Budget Based on Allocation Mode
        base_slot_budget = self.total_budget_limit / self.max_open_positions

        if self.allocation_mode == "CONFIDENCE_WEIGHTED":
            # Scale by Bayesian setup performance weight (0.65x to 1.35x)
            clamped_weight = max(0.65, min(1.35, setup_weight))
            allocated_amount = base_slot_budget * clamped_weight
        elif self.allocation_mode == "VOLATILITY_PARITY":
            # Scale inversely with coin ATR% (lower dollar amount for meme/hyper-volatile coins)
            norm_atr = max(0.4, min(3.0, coin_atr_pct))
            vol_factor = 1.0 / (norm_atr / 1.0)
            allocated_amount = base_slot_budget * max(0.6, min(1.4, vol_factor))
        else:
            # Default EQUAL_SPLIT: Each slot receives an equal portion of total budget
            allocated_amount = base_slot_budget

        # 5. Strict Bound Checks:
        # Cannot exceed available budget pool
        allocated_amount = min(allocated_amount, effective_pool)
        # Cannot be less than minimum order size
        if allocated_amount < self.min_order_usd:
            if effective_pool >= self.min_order_usd:
                allocated_amount = self.min_order_usd
            else:
                return AllocationResult(
                    approved=False,
                    reason=f"Allocated amount (${allocated_amount:.2f}) below minimum order (${self.min_order_usd:.2f})",
                    trade_amount_usdt=0.0,
                    total_budget_limit=self.total_budget_limit,
                    total_deployed_usdt=total_deployed,
                    available_budget_usdt=available_budget,
                    slot_budget_usdt=base_slot_budget
                )

        return AllocationResult(
            approved=True,
            reason="Budget allocation approved",
            trade_amount_usdt=round(allocated_amount, 2),
            total_budget_limit=round(self.total_budget_limit, 2),
            total_deployed_usdt=round(total_deployed, 2),
            available_budget_usdt=round(available_budget, 2),
            slot_budget_usdt=round(base_slot_budget, 2)
        )

    def check_breakeven_adjustment(self, pos: Dict[str, Any], current_price: float) -> Optional[float]:
        """
        Evaluates whether an open position qualifies for a Break-Even Stop Loss lock.
        Once price rises >= breakeven_trigger_pct (default +1.0%), moves stop loss
        to Entry Price + 0.25% (covering fees and locking in green trade).
        """
        if not self.breakeven_lock_enabled:
            return None

        # If already locked to break-even or higher, return None
        entry_price = float(pos["entry_price"])
        current_stop = pos.get("stop_loss_price")
        breakeven_target_stop = round(entry_price * 1.0025, 4)

        if current_stop and current_stop >= breakeven_target_stop:
            return None  # Already locked

        # Check if current profit reaches trigger threshold
        gain_pct = ((current_price - entry_price) / entry_price) * 100
        if gain_pct >= self.breakeven_trigger_pct:
            return breakeven_target_stop

        return None

    def get_summary(self, active_positions: Dict[str, Dict[str, Any]], wallet_balance: float) -> Dict[str, Any]:
        """Generate comprehensive money management metrics for telemetry and UI."""
        total_deployed = sum(float(pos.get("cost_usdt", 0.0)) for pos in active_positions.values())
        available_budget = max(0.0, self.total_budget_limit - total_deployed)
        utilization_pct = (total_deployed / self.total_budget_limit * 100) if self.total_budget_limit > 0 else 0.0
        base_slot = self.total_budget_limit / self.max_open_positions if self.max_open_positions > 0 else 0.0

        return {
            "total_budget_limit_usd": round(self.total_budget_limit, 2),
            "total_deployed_usd": round(total_deployed, 2),
            "available_budget_usd": round(available_budget, 2),
            "budget_utilization_pct": round(min(100.0, utilization_pct), 1),
            "allocation_mode": self.allocation_mode,
            "max_open_positions": self.max_open_positions,
            "open_positions_count": len(active_positions),
            "per_slot_budget_usd": round(base_slot, 2),
            "max_session_loss_usd": round(self.max_session_loss_usd, 2),
            "session_realized_loss_usd": round(self.session_realized_loss, 2),
            "circuit_breaker_tripped": self.circuit_breaker_tripped,
            "breakeven_lock_enabled": self.breakeven_lock_enabled,
            "breakeven_trigger_pct": self.breakeven_trigger_pct,
            "wallet_usdt_balance": round(wallet_balance, 2)
        }

