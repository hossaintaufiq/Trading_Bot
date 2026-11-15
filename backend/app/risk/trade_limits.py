"""
Trade limits and risk-based sizing for day-trade setups (ADR-038). Decimal only (A-01).

Pure functions adapted from day-trader-skill's budget/risk steps. They are ADDITIONAL gates: they do not
replace the Risk Manager (S-04), which still must authorize every paper order.
"""
from dataclasses import dataclass, field
from decimal import ROUND_DOWN, Decimal
from typing import List

from pydantic import BaseModel


class TradeLimits(BaseModel):
    risk_pct: Decimal = Decimal("0.005")       # AGENTS.md: max risk per trade 0.5% of equity
    min_rr: Decimal = Decimal("1.5")           # AGENTS.md: minimum reward:risk
    max_trades_per_day: int = 2                # AGENTS.md: max concurrent positions 2 (reused as daily cap)
    entry_start_hour_utc: int = 0
    entry_end_hour_utc: int = 12               # entries allowed while hour < end


@dataclass
class LimitDecision:
    passed: bool
    failed: List[str] = field(default_factory=list)


def size_position(equity: Decimal, risk_pct: Decimal, entry: Decimal, stop: Decimal,
                  fee_rate: Decimal = Decimal("0")) -> Decimal:
    """Quantity risking `risk_pct` of equity at the stop, capped so cost incl. entry fee <= equity (no leverage)."""
    per_unit = entry - stop
    if per_unit <= 0 or equity <= 0:
        return Decimal("0")
    by_risk = equity * risk_pct / per_unit
    by_cash = equity / (entry * (Decimal(1) + fee_rate))
    return min(by_risk, by_cash).quantize(Decimal("0.00000001"), rounding=ROUND_DOWN)


def check_limits(*, limits: TradeLimits, equity: Decimal, entry: Decimal, stop: Decimal, target: Decimal,
                 trades_today: int, hour_utc: int, fee_rate: Decimal = Decimal("0")) -> LimitDecision:
    failed: List[str] = []
    risk = entry - stop
    if risk <= 0:
        failed.append("stop_side")
    elif (target - entry) / risk < limits.min_rr:
        failed.append("reward_risk")
    if trades_today >= limits.max_trades_per_day:
        failed.append("trades_per_day")
    if not (limits.entry_start_hour_utc <= hour_utc < limits.entry_end_hour_utc):
        failed.append("entry_window")
    qty = size_position(equity, limits.risk_pct, entry, stop, fee_rate)
    if qty <= 0:
        failed.append("size_zero")
    elif qty * risk > equity * limits.risk_pct:
        failed.append("max_loss")
    return LimitDecision(passed=not failed, failed=failed)
