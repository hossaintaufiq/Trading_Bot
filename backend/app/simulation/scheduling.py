"""
NEPTUNE Point-in-Time Execution Scheduling (`scheduling.py`)

Deterministic execution scheduler for historical simulations under the
NEXT_ELIGIBLE_PRICE execution policy (Milestone 4.6.2.4, ADR-026).

Enforces the non-negotiable temporal invariants:
1. Finalized candle close is the decision cutoff.
2. Orders approved at candle T close execute strictly at Bar T+1 Open.
3. Retroactive execution (at candle T close, T open, or intrabar) raises fatal look-ahead errors.
4. Risk Manager remains the sole authorization authority (retains tokens and provenance).
5. Missing candles and data gaps beyond max_execution_gap_bars trigger deterministic order expiry.
6. Market opening gaps breaching stop-loss thresholds invalidate entries safely.
7. Cryptographic HMAC risk authorization token verification prior to execution fill.
"""
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from app.data.market.validator import ValidatedCandle
from app.data.news.temporal import (
    PointInTimeExecutionSynchronizer,
    parse_iso_utc,
    to_iso_utc,
)
from app.simulation.execution import PaperExecutionSimulator
from app.simulation.models import (
    ActivePosition,
    ExecutionPolicy,
    OrderStatus,
    ScheduledOrder,
)


def get_timeframe_delta(timeframe: str) -> timedelta:
    """Resolve timeframe string to timedelta."""
    tf = timeframe.lower()
    if tf.endswith("m"):
        return timedelta(minutes=int(tf[:-1]))
    elif tf.endswith("h"):
        return timedelta(hours=int(tf[:-1]))
    elif tf.endswith("d"):
        return timedelta(days=int(tf[:-1]))
    elif tf.endswith("w"):
        return timedelta(weeks=int(tf[:-1]))
    return timedelta(minutes=15)


class PointInTimeExecutionScheduler:
    """
    Schedules, validates, and fills simulated orders strictly at eligible market execution points.
    """

    def __init__(
        self,
        execution_policy: str = ExecutionPolicy.NEXT_ELIGIBLE_PRICE,
        max_execution_gap_bars: int = 3,
        risk_manager: Optional[Any] = None,
    ):
        self.execution_policy = execution_policy
        self.max_execution_gap_bars = max_execution_gap_bars
        self.risk_manager = risk_manager
        self.pending_orders: List[ScheduledOrder] = []
        self.order_history: List[ScheduledOrder] = []
        self.scheduled_order_ids: Set[str] = set()
        self.scheduled_tokens: Set[str] = set()

    def schedule_order(
        self,
        signal_id: str,
        symbol: str,
        timeframe: str,
        direction: str,
        signal_timestamp: str,
        candle_close_timestamp: str,
        position_size: Decimal,
        stop_loss: Decimal,
        take_profit: Optional[Decimal],
        risk_approval_token: str,
        market_regime: str,
        strategy_metadata: Dict[str, Any],
        exit_policy: str = "BALANCED",
        theoretical_take_profit: Optional[Decimal] = None,
        information_availability_cutoff: Optional[str] = None,
        earliest_eligible_execution_timestamp: Optional[str] = None,
        scheduled_bar_index: int = 0,
        order_id: Optional[str] = None,
    ) -> ScheduledOrder:
        """
        Create and queue a ScheduledOrder awaiting next-eligible-price fill.
        """
        if not risk_approval_token or not str(risk_approval_token).strip():
            raise ValueError("Risk authorization token is required to schedule an order.")

        cutoff = information_availability_cutoff or candle_close_timestamp

        # Invariant: earliest execution timestamp must be at or after decision candle close
        dt_close = parse_iso_utc(candle_close_timestamp)
        if dt_close is None:
            raise ValueError(f"Invalid candle_close_timestamp: {candle_close_timestamp}")

        if earliest_eligible_execution_timestamp:
            dt_earliest = parse_iso_utc(earliest_eligible_execution_timestamp)
            if dt_earliest and dt_earliest < dt_close:
                raise ValueError(
                    f"Look-ahead violation: earliest_eligible_execution_timestamp ({earliest_eligible_execution_timestamp}) "
                    f"< candle_close_timestamp ({candle_close_timestamp})"
                )
        else:
            earliest_eligible_execution_timestamp = candle_close_timestamp

        assigned_order_id = order_id or f"ord_{uuid.uuid4().hex[:12]}"
        if assigned_order_id in self.scheduled_order_ids:
            raise ValueError(f"Duplicate order ID detected: {assigned_order_id}")

        if risk_approval_token in self.scheduled_tokens:
            raise ValueError(f"Duplicate risk token submission: {risk_approval_token} is already scheduled")

        if self.risk_manager is not None and hasattr(self.risk_manager, "reserve_token"):
            run_ref = str(strategy_metadata.get("run_id", "default_run"))
            rec = getattr(self.risk_manager, "token_registry", {}).get(risk_approval_token)
            if rec is not None:
                if rec.state == "CONSUMED":
                    raise ValueError("Risk token reservation failed: TOKEN_ALREADY_CONSUMED")
                if rec.state == "RESERVED" and rec.order_id != assigned_order_id:
                    raise ValueError("Risk token reservation failed: TOKEN_ALREADY_RESERVED_BY_ANOTHER_ORDER")
                if rec.run_id == run_ref:
                    self.risk_manager.reserve_token(risk_approval_token, assigned_order_id, run_ref)

        self.scheduled_order_ids.add(assigned_order_id)
        self.scheduled_tokens.add(risk_approval_token)

        order = ScheduledOrder(
            order_id=assigned_order_id,
            signal_id=signal_id,
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            signal_timestamp=signal_timestamp,
            information_availability_cutoff=cutoff,
            candle_close_timestamp=candle_close_timestamp,
            order_creation_timestamp=candle_close_timestamp,
            risk_approval_timestamp=candle_close_timestamp,
            risk_approval_token=risk_approval_token,
            earliest_eligible_execution_timestamp=earliest_eligible_execution_timestamp,
            execution_policy=self.execution_policy,
            status=OrderStatus.SCHEDULED,
            position_size=position_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
            market_regime=market_regime,
            strategy_metadata=strategy_metadata,
            exit_policy=exit_policy,
            theoretical_take_profit=theoretical_take_profit or take_profit,
            scheduled_bar_index=scheduled_bar_index,
        )

        self.pending_orders.append(order)
        # Maintain deterministic ordering: candle_close_timestamp, signal_id, symbol
        self.pending_orders.sort(
            key=lambda o: (o.candle_close_timestamp, o.signal_id, o.symbol)
        )
        return order

    def process_candle_open(
        self,
        curr_candle: ValidatedCandle,
        current_open_positions: List[ActivePosition],
        current_equity: Decimal,
        peak_equity: Decimal,
        daily_starting_equity: Decimal,
        daily_realized_pnl: Decimal,
        execution_simulator: PaperExecutionSimulator,
        max_concurrent_positions: int,
        max_drawdown_pct: Decimal,
        daily_loss_limit_pct: Decimal,
    ) -> Tuple[List[Tuple[ScheduledOrder, ActivePosition]], List[ScheduledOrder]]:
        """
        Evaluate and fill pending scheduled orders matching curr_candle.symbol at curr_candle.open.

        Returns:
            (filled_pairs, terminal_orders)
            where filled_pairs is List[(ScheduledOrder, ActivePosition)]
            and terminal_orders is List[ScheduledOrder] (rejected or expired)
        """
        filled_pairs: List[Tuple[ScheduledOrder, ActivePosition]] = []
        terminal_orders: List[ScheduledOrder] = []
        surviving_pending: List[ScheduledOrder] = []

        dt_candle = parse_iso_utc(curr_candle.timestamp)
        if dt_candle is None:
            raise ValueError(f"Invalid candle timestamp: {curr_candle.timestamp}")

        tf_delta = get_timeframe_delta(curr_candle.timeframe)
        c_open = Decimal(str(curr_candle.open))

        # Check circuit breakers once per candle step
        drawdown_tripped = False
        if peak_equity > Decimal("0"):
            dd = (peak_equity - current_equity) / peak_equity
            if dd >= max_drawdown_pct:
                drawdown_tripped = True

        daily_loss_tripped = False
        if daily_starting_equity > Decimal("0"):
            # Approximate unrealized pnl across existing open positions
            unrealized = sum(getattr(p, "unrealized_pnl", Decimal("0")) for p in current_open_positions)
            daily_loss_ratio = (daily_realized_pnl + unrealized) / daily_starting_equity
            if daily_loss_ratio <= -daily_loss_limit_pct:
                daily_loss_tripped = True

        active_symbols = {p.symbol for p in current_open_positions}

        for order in self.pending_orders:
            if order.symbol != curr_candle.symbol:
                surviving_pending.append(order)
                continue

            dt_close = parse_iso_utc(order.candle_close_timestamp)
            dt_earliest = parse_iso_utc(order.earliest_eligible_execution_timestamp)

            # Check if order is eligible yet
            if dt_earliest and dt_candle < dt_earliest:
                surviving_pending.append(order)
                continue

            # Invariant: assert no look-ahead execution
            if dt_close and dt_candle < dt_close:
                raise ValueError(
                    f"Look-ahead violation: Attempted fill at {curr_candle.timestamp} "
                    f"before decision candle close {order.candle_close_timestamp}"
                )

            # Check market-data gap between decision candle close and execution
            if dt_close:
                time_elapsed = dt_candle - dt_close
                max_allowed_time = tf_delta * (self.max_execution_gap_bars + 1)
                if time_elapsed > max_allowed_time:
                    order.status = OrderStatus.EXPIRED
                    order.rejection_reason = (
                        f"Data gap exceeded max_execution_gap_bars ({self.max_execution_gap_bars}): "
                        f"elapsed {time_elapsed} > {max_allowed_time}"
                    )
                    if self.risk_manager is not None and hasattr(self.risk_manager, "expire_token"):
                        self.risk_manager.expire_token(order.risk_approval_token, order.order_id)
                    terminal_orders.append(order)
                    self.order_history.append(order)
                    continue

            # Check circuit breakers at execution time
            if drawdown_tripped:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = "Drawdown circuit breaker active at execution time"
                terminal_orders.append(order)
                self.order_history.append(order)
                continue

            if daily_loss_tripped:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = "Daily loss limit active at execution time"
                terminal_orders.append(order)
                self.order_history.append(order)
                continue

            # Check portfolio position limits
            total_active_count = len(current_open_positions) + len(filled_pairs)
            if total_active_count >= max_concurrent_positions:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = (
                    f"Max concurrent positions reached before execution ({total_active_count} >= {max_concurrent_positions})"
                )
                terminal_orders.append(order)
                self.order_history.append(order)
                continue

            # Check asset correlation exposure (1 per asset)
            if order.symbol in active_symbols or any(p.symbol == order.symbol for _, p in filled_pairs):
                order.status = OrderStatus.REJECTED
                order.rejection_reason = f"Active position already open for {order.symbol}"
                terminal_orders.append(order)
                self.order_history.append(order)
                continue

            # Check stop loss opening gap
            if order.direction == "LONG" and c_open <= order.stop_loss:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = f"Market opening gap below stop loss ({c_open} <= {order.stop_loss})"
                terminal_orders.append(order)
                self.order_history.append(order)
                continue

            if order.direction == "SHORT" and c_open >= order.stop_loss:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = f"Market opening gap above stop loss ({c_open} >= {order.stop_loss})"
                terminal_orders.append(order)
                self.order_history.append(order)
                continue

            # Cryptographic Risk Manager Token Verification
            if not order.risk_approval_token:
                order.status = OrderStatus.REJECTED
                order.rejection_reason = "Missing risk authorization token"
                terminal_orders.append(order)
                self.order_history.append(order)
                continue

            if self.risk_manager is not None:
                entry_ref = Decimal(str(order.strategy_metadata.get("entry_price", c_open)))
                run_ref = str(order.strategy_metadata.get("run_id", "default_run"))
                is_valid_tok, tok_err = self.risk_manager.verify_risk_token(
                    token=order.risk_approval_token,
                    signal_id=order.signal_id,
                    symbol=order.symbol,
                    direction=order.direction,
                    position_size=order.position_size,
                    entry_price=entry_ref,
                    stop_loss=order.stop_loss,
                    timestamp=order.risk_approval_timestamp,
                    run_id=run_ref,
                )
                if not is_valid_tok:
                    order.status = OrderStatus.REJECTED
                    order.rejection_reason = f"Risk token verification failed: {tok_err}"
                    if hasattr(self.risk_manager, "release_token"):
                        self.risk_manager.release_token(order.risk_approval_token, order.order_id)
                    terminal_orders.append(order)
                    self.order_history.append(order)
                    continue

                if hasattr(self.risk_manager, "consume_token"):
                    is_consumed, con_err = self.risk_manager.consume_token(
                        token=order.risk_approval_token,
                        order_id=order.order_id,
                        run_id=run_ref,
                        fill_timestamp=curr_candle.timestamp,
                    )
                    if not is_consumed:
                        order.status = OrderStatus.REJECTED
                        order.rejection_reason = f"Risk token consumption failed: {con_err}"
                        terminal_orders.append(order)
                        self.order_history.append(order)
                        continue

            # All checks passed: execute at curr_candle.open
            PointInTimeExecutionSynchronizer.assert_no_lookahead(
                decision_bar_close_dt=dt_close or dt_candle,
                execution_dt=dt_candle,
                execution_price_type="NEXT_BAR_OPEN",
            )

            new_pos = execution_simulator.simulate_entry(
                symbol=order.symbol,
                timeframe=order.timeframe,
                direction=order.direction,
                raw_price=c_open,
                position_size=order.position_size,
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                signal_timestamp=order.signal_timestamp,
                entry_timestamp=curr_candle.timestamp,
                market_regime=order.market_regime,
                strategy_metadata=order.strategy_metadata,
                exit_policy=order.exit_policy,
                theoretical_take_profit=order.theoretical_take_profit,
                information_availability_cutoff=order.information_availability_cutoff,
                candle_close_timestamp=order.candle_close_timestamp,
                order_creation_timestamp=order.order_creation_timestamp,
                risk_approval_timestamp=order.risk_approval_timestamp,
                risk_approval_token=order.risk_approval_token,
                earliest_eligible_execution_timestamp=order.earliest_eligible_execution_timestamp,
                execution_policy=self.execution_policy,
            )

            order.status = OrderStatus.FILLED
            order.actual_fill_timestamp = curr_candle.timestamp
            order.actual_fill_price = new_pos.entry_price
            order.raw_fill_price = c_open

            filled_pairs.append((order, new_pos))
            self.order_history.append(order)

        self.pending_orders = surviving_pending
        return filled_pairs, terminal_orders
