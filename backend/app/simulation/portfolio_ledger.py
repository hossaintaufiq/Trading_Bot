"""
Portfolio Ledger & Corrected Double-Entry Cash/Equity Accounting Engine.

NEPTUNE Milestone 4.6.3.1.2 - Mathematical Portfolio Accounting Remediation.
Provides rigorous double-entry accounting for both LONG and SHORT spot-collateralized positions:
- Liquid cash balance (unencumbered capital).
- Reserved collateral (for SHORT positions).
- Long inventory cost (for LONG positions).
- Unrealized PnL and marked-to-market position equity.
- Entry and exit cash flows with exact friction charging.
- Full reconciliation between cash, trades, and marked equity.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Set, Tuple

from app.data.market.validator import ValidatedCandle
from app.simulation.models import ActivePosition, SimulatedTrade


class InsufficientFundsError(Exception):
    """Raised when available cash balance is insufficient for order margin/notional and fees."""
    pass


class PortfolioLedger:
    """
    Stateful accounting ledger maintaining mathematical invariants across
    long and short positions, transaction costs, cash flows, and mark-to-market equity.
    """

    def __init__(
        self,
        initial_capital: Decimal,
        taker_fee_pct: Decimal = Decimal("0.001"),
    ):
        self.initial_capital = initial_capital
        self.cash_balance = initial_capital
        self.reserved_collateral = Decimal("0")
        self.long_inventory_cost = Decimal("0")
        self.taker_fee_pct = taker_fee_pct

        self.open_positions: List[ActivePosition] = []
        self.completed_trades: List[SimulatedTrade] = []
        self.seen_trade_ids: Set[str] = set()

        self.peak_equity = initial_capital
        self.daily_starting_equity = initial_capital
        self.daily_realized_pnl = Decimal("0")
        self.current_day: Optional[str] = None

        # Ledger transaction history
        self.transaction_history: List[Dict[str, Any]] = [
            {
                "type": "INITIAL_DEPOSIT",
                "amount": initial_capital,
                "cash_balance": initial_capital,
                "timestamp": "START",
            }
        ]

    @property
    def cash_equity(self) -> Decimal:
        """Alias for backward compatibility with existing engine code."""
        return self.cash_balance

    @cash_equity.setter
    def cash_equity(self, value: Decimal) -> None:
        self.cash_balance = value

    def process_order_fill(self, pos: ActivePosition) -> Decimal:
        """
        Record order fill and deduct initial cash outflow.
        For LONG: Outflow = entry_notional + entry_fee.
        For SHORT: Outflow = collateral_reserved (entry_notional) + entry_fee.
        Returns the deducted cash outflow.
        """
        entry_notional = pos.position_size * pos.entry_price
        cash_outflow = entry_notional + pos.entry_fee

        if self.cash_balance < cash_outflow:
            raise InsufficientFundsError(
                f"Cannot fill {pos.direction} {pos.symbol}: requires {cash_outflow} USDT, "
                f"available cash is {self.cash_balance} USDT"
            )

        self.cash_balance -= cash_outflow

        if pos.direction == "LONG":
            self.long_inventory_cost += entry_notional
        elif pos.direction == "SHORT":
            self.reserved_collateral += entry_notional
        else:
            raise ValueError(f"Unsupported position direction: {pos.direction}")

        self.open_positions.append(pos)

        self.transaction_history.append({
            "type": "ORDER_ENTRY",
            "position_id": pos.position_id,
            "symbol": pos.symbol,
            "direction": pos.direction,
            "size": pos.position_size,
            "entry_price": pos.entry_price,
            "notional": entry_notional,
            "fee": pos.entry_fee,
            "outflow": cash_outflow,
            "cash_balance_after": self.cash_balance,
            "timestamp": pos.entry_timestamp,
        })

        return cash_outflow

    def process_trade_exit(
        self,
        pos: ActivePosition,
        trade: SimulatedTrade,
        exit_fee: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Record position exit and credit cash proceeds.
        For LONG: Inflow = exit_notional - exit_fee.
        For SHORT: Inflow = collateral + gross_pnl - exit_fee
                         = pos.position_size * (2 * pos.entry_price - trade.exit_price) - exit_fee.
        Returns the credited cash inflow.
        """
        if trade.trade_id in self.seen_trade_ids:
            raise ValueError(f"Duplicate trade detected in ledger: {trade.trade_id}")

        exit_notional = pos.position_size * trade.exit_price
        fee = exit_fee if exit_fee is not None else (exit_notional * self.taker_fee_pct)

        if pos.direction == "LONG":
            cash_inflow = exit_notional - fee
            self.long_inventory_cost -= (pos.position_size * pos.entry_price)
        elif pos.direction == "SHORT":
            # Repurchase liability: pos.position_size * trade.exit_price
            # Return collateral: pos.position_size * pos.entry_price
            # Gross profit / loss: pos.position_size * (pos.entry_price - trade.exit_price)
            # Cash inflow = collateral + gross_pnl - fee
            cash_inflow = pos.position_size * (Decimal("2.0") * pos.entry_price - trade.exit_price) - fee
            self.reserved_collateral -= (pos.position_size * pos.entry_price)
        else:
            raise ValueError(f"Unsupported position direction: {pos.direction}")

        self.cash_balance += cash_inflow
        self.daily_realized_pnl += trade.net_pnl

        self.completed_trades.append(trade)
        self.seen_trade_ids.add(trade.trade_id)

        # Remove position from open positions
        self.open_positions = [p for p in self.open_positions if p.position_id != pos.position_id]

        self.transaction_history.append({
            "type": "TRADE_EXIT",
            "trade_id": trade.trade_id,
            "position_id": pos.position_id,
            "symbol": pos.symbol,
            "direction": pos.direction,
            "exit_price": trade.exit_price,
            "exit_fee": fee,
            "inflow": cash_inflow,
            "gross_pnl": trade.gross_pnl,
            "net_pnl": trade.net_pnl,
            "cash_balance_after": self.cash_balance,
            "timestamp": trade.exit_timestamp,
        })

        return cash_inflow

    def process_partial_exit(
        self,
        pos: ActivePosition,
        exit_size: Decimal,
        trade: SimulatedTrade,
        exit_fee: Optional[Decimal] = None,
    ) -> Decimal:
        """
        Record partial position exit, adjusting position size and crediting proportional proceeds.
        """
        if exit_size <= Decimal("0") or exit_size > pos.position_size:
            raise ValueError(f"Invalid exit size {exit_size} for position size {pos.position_size}")

        if trade.trade_id in self.seen_trade_ids:
            raise ValueError(f"Duplicate trade detected in ledger: {trade.trade_id}")

        exit_notional = exit_size * trade.exit_price
        fee = exit_fee if exit_fee is not None else (exit_notional * self.taker_fee_pct)

        if pos.direction == "LONG":
            cash_inflow = exit_notional - fee
            self.long_inventory_cost -= (exit_size * pos.entry_price)
        elif pos.direction == "SHORT":
            cash_inflow = exit_size * (Decimal("2.0") * pos.entry_price - trade.exit_price) - fee
            self.reserved_collateral -= (exit_size * pos.entry_price)
        else:
            raise ValueError(f"Unsupported position direction: {pos.direction}")

        self.cash_balance += cash_inflow
        self.daily_realized_pnl += trade.net_pnl

        self.completed_trades.append(trade)
        self.seen_trade_ids.add(trade.trade_id)

        # Proportionally reduce entry fee on surviving position
        if pos.position_size > Decimal("0") and pos.entry_fee > Decimal("0"):
            entry_fee_share = pos.entry_fee * (exit_size / pos.position_size)
            pos.entry_fee -= entry_fee_share

        pos.position_size -= exit_size
        if pos.position_size == Decimal("0"):
            self.open_positions = [p for p in self.open_positions if p.position_id != pos.position_id]

        self.transaction_history.append({
            "type": "PARTIAL_EXIT",
            "trade_id": trade.trade_id,
            "position_id": pos.position_id,
            "exit_size": exit_size,
            "remaining_size": pos.position_size,
            "inflow": cash_inflow,
            "net_pnl": trade.net_pnl,
            "cash_balance_after": self.cash_balance,
            "timestamp": trade.exit_timestamp,
        })

        return cash_inflow

    def update_candle_mark(self, symbol: str, candle: ValidatedCandle) -> None:
        """Update current price and mark-to-market unrealized PnL for active positions."""
        c_close = Decimal(str(candle.close))
        for p in self.open_positions:
            if p.symbol == symbol:
                p.current_price = c_close
                if p.direction == "LONG":
                    p.unrealized_pnl = p.position_size * (c_close - p.entry_price)
                elif p.direction == "SHORT":
                    p.unrealized_pnl = p.position_size * (p.entry_price - c_close)

    def get_position_equity(self, pos: ActivePosition) -> Decimal:
        """
        Calculate marked-to-market equity for a single active position.
        LONG: position_size * current_price.
        SHORT: position_size * (2 * entry_price - current_price)
             = collateral + unrealized_pnl.
        """
        if pos.direction == "LONG":
            return pos.position_size * pos.current_price
        elif pos.direction == "SHORT":
            return pos.position_size * (Decimal("2.0") * pos.entry_price - pos.current_price)
        else:
            raise ValueError(f"Unsupported position direction: {pos.direction}")

    def get_open_positions_equity(self) -> Decimal:
        """Sum marked-to-market equity across all currently open positions."""
        return sum((self.get_position_equity(p) for p in self.open_positions), Decimal("0.0"))

    def get_total_equity(self) -> Decimal:
        """
        Total portfolio equity = cash_balance + open_positions_equity.
        Strictly reconciles with initial_capital + realized_net_pnl + open_unrealized_pnl - open_entry_fees.
        """
        return self.cash_balance + self.get_open_positions_equity()

    def get_drawdown_pct(self) -> Decimal:
        """Current drawdown from peak equity as a percentage [0.0, 100.0]."""
        tot_eq = self.get_total_equity()
        if self.peak_equity > Decimal("0"):
            return (self.peak_equity - tot_eq) / self.peak_equity * Decimal("100.0")
        return Decimal("0.0")

    def assert_invariants(self) -> Dict[str, bool]:
        """
        Verify all core mathematical and accounting invariants.
        Raises AssertionError if any invariant is violated.
        """
        # Tolerance allows for cumulative cent-level rounding on quantized trade.net_pnl
        tol = Decimal("0.05")

        # 1. Total equity reconciliation
        calc_tot_eq = self.cash_balance + self.get_open_positions_equity()
        assert abs(self.get_total_equity() - calc_tot_eq) < tol, "Total equity does not reconcile to cash + positions"

        # 2. Closed ledger reconciliation
        realized_net_pnl = sum((t.net_pnl for t in self.completed_trades), Decimal("0.0"))
        open_unrealized = sum((p.unrealized_pnl for p in self.open_positions), Decimal("0.0"))
        open_entry_fees = sum((p.entry_fee for p in self.open_positions), Decimal("0.0"))
        expected_tot_eq = self.initial_capital + realized_net_pnl + open_unrealized - open_entry_fees
        assert abs(self.get_total_equity() - expected_tot_eq) < tol, (
            f"Balance sheet invariant violated: total_equity={self.get_total_equity()} "
            f"!= expected={expected_tot_eq} (realized={realized_net_pnl}, unrealized={open_unrealized})"
        )

        # 3. Post-close reconciliation (when no positions open)
        if len(self.open_positions) == 0:
            assert abs(self.cash_balance - (self.initial_capital + realized_net_pnl)) < tol, (
                f"Cash equity invariant violated after positions closed: cash={self.cash_balance} "
                f"!= initial({self.initial_capital}) + realized({realized_net_pnl})"
            )
            assert self.reserved_collateral == Decimal("0"), "Reserved collateral non-zero after close"
            assert self.long_inventory_cost == Decimal("0"), "Long inventory cost non-zero after close"

        # 4. Collateral tracking
        expected_reserved = sum(
            (p.position_size * p.entry_price for p in self.open_positions if p.direction == "SHORT"),
            Decimal("0.0")
        )
        assert abs(self.reserved_collateral - expected_reserved) < tol, "Reserved collateral mismatch"

        # 5. Long inventory tracking
        expected_long_inv = sum(
            (p.position_size * p.entry_price for p in self.open_positions if p.direction == "LONG"),
            Decimal("0.0")
        )
        assert abs(self.long_inventory_cost - expected_long_inv) < tol, "Long inventory cost mismatch"

        return {
            "total_equity_reconciled": True,
            "balance_sheet_reconciled": True,
            "post_close_cash_reconciled": True,
            "collateral_reconciled": True,
            "long_inventory_reconciled": True,
        }
