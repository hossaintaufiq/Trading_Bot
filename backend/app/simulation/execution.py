"""
NEPTUNE Paper Execution Simulation (`execution.py`)

Simulates realistic exchange order fills without connecting to any real exchange.
Applies:
- Taker fees (0.1% default)
- Slippage penalty (0.05% per side default)
- Bid-ask spread penalty (e.g. 2 bps)
- Intrabar stop/target conflict resolution:
  CRITICAL: If both stop loss and take profit are touched in the same OHLC candle,
  the trade is conservatively resolved as a STOP LOSS hit (AMBIGUOUS_BAR_STOP).
  Favorable outcome is never assumed (Section 4 & Rule S-06).
"""
import uuid
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple

from app.data.market.validator import ValidatedCandle
from app.simulation.models import ActivePosition, SimulatedTrade


class PaperExecutionSimulator:
    """Simulates realistic execution dynamics for paper trades."""

    def __init__(
        self,
        taker_fee_pct: Decimal = Decimal("0.001"),    # 0.1%
        maker_fee_pct: Decimal = Decimal("0.001"),    # 0.1%
        slippage_pct: Decimal = Decimal("0.0005"),    # 0.05%
        spread_bps: Decimal = Decimal("2.0"),         # 2 bps = 0.02%
        conservative_ambiguity: bool = True,
    ):
        self.taker_fee_pct = taker_fee_pct
        self.maker_fee_pct = maker_fee_pct
        self.slippage_pct = slippage_pct
        self.spread_fraction = (spread_bps / Decimal("10000")) / Decimal("2")  # Half spread
        self.conservative_ambiguity = conservative_ambiguity

    def simulate_entry(
        self,
        symbol: str,
        timeframe: str,
        direction: str,
        raw_price: Decimal,
        position_size: Decimal,
        stop_loss: Decimal,
        take_profit: Optional[Decimal],
        signal_timestamp: str,
        entry_timestamp: str,
        market_regime: str,
        strategy_metadata: dict,
        exit_policy: str = "FIXED_BRACKET",
        theoretical_take_profit: Optional[Decimal] = None,
    ) -> ActivePosition:
        """
        Execute simulated market entry with slippage and spread friction.
        """
        if direction == "LONG":
            # Long pays ask price (above midpoint) + slippage
            friction_multiplier = Decimal("1") + self.slippage_pct + self.spread_fraction
            exec_entry_price = raw_price * friction_multiplier
        else:
            # Short sells at bid price (below midpoint) - slippage
            friction_multiplier = Decimal("1") - self.slippage_pct - self.spread_fraction
            exec_entry_price = raw_price * friction_multiplier

        notional = exec_entry_price * position_size
        entry_fee = notional * self.taker_fee_pct
        entry_slippage_cost = (raw_price * self.slippage_pct) * position_size
        entry_spread_cost = (raw_price * self.spread_fraction) * position_size

        position_id = f"pos_{uuid.uuid4().hex[:12]}"

        return ActivePosition(
            position_id=position_id,
            signal_id=strategy_metadata.get("signal_id", f"sig_{uuid.uuid4().hex[:8]}"),
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            entry_timestamp=entry_timestamp,
            entry_price=exec_entry_price,
            raw_entry_price=raw_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            entry_fee=entry_fee,
            entry_slippage_cost=entry_slippage_cost,
            entry_spread_cost=entry_spread_cost,
            market_regime=market_regime,
            strategy_metadata=strategy_metadata,
            exit_policy=exit_policy,
            theoretical_take_profit=theoretical_take_profit or take_profit,
        )

    def evaluate_candle_bracket(
        self,
        position: ActivePosition,
        candle: ValidatedCandle,
    ) -> Optional[SimulatedTrade]:
        """
        Evaluate candle against position's protective brackets.
        Under BALANCED exit policy:
        - Fixed take profit is NOT enforced; position is allowed to continue running.
        - Only protective stop loss (or ratcheted trailing stop) is evaluated.
        Under FIXED_BRACKET exit policy:
        - Hard brackets apply with conservative resolution on ambiguous bars.
        """
        c_open = Decimal(str(candle.open))
        c_high = Decimal(str(candle.high))
        c_low = Decimal(str(candle.low))
        c_close = Decimal(str(candle.close))

        # Update unrealized mark-to-market
        position.current_price = c_close
        if position.direction == "LONG":
            position.unrealized_pnl = (c_close - position.entry_price) * position.position_size
        else:
            position.unrealized_pnl = (position.entry_price - c_close) * position.position_size

        if position.exit_policy == "BALANCED":
            # In BALANCED protection mode, fixed take-profit is NOT automatically enforced.
            # Only protective stop-loss (initial or ratcheted trailing stop) is evaluated.
            if position.direction == "LONG":
                if c_low <= position.stop_loss:
                    exit_price_raw = min(position.stop_loss, c_open)
                    exit_reason = "TRAILING_STOP" if position.stop_loss > position.initial_stop_loss else "STOP_LOSS"
                    return self._finalize_trade(position, exit_price_raw, candle.timestamp, exit_reason)
            else:  # SHORT
                if c_high >= position.stop_loss:
                    exit_price_raw = max(position.stop_loss, c_open)
                    exit_reason = "TRAILING_STOP" if position.stop_loss < position.initial_stop_loss else "STOP_LOSS"
                    return self._finalize_trade(position, exit_price_raw, candle.timestamp, exit_reason)
            return None

        # Standard hard-bracket evaluation (for FIXED_BRACKET mode)
        if position.direction == "LONG":
            stop_touched = bool(c_low <= position.stop_loss)
            target_touched = bool(position.take_profit is not None and c_high >= position.take_profit)

            if stop_touched and target_touched:
                # Ambiguous bar: both stop and target touched in the same candle
                # Conservative mandate: treat as stop loss hit
                exit_price_raw = position.stop_loss
                exit_reason = "AMBIGUOUS_BAR_STOP" if self.conservative_ambiguity else "STOP_LOSS"
                return self._finalize_trade(position, exit_price_raw, candle.timestamp, exit_reason)

            if stop_touched:
                # If market gapped down below stop on open, fill at open (worse execution)
                exit_price_raw = min(position.stop_loss, c_open)
                return self._finalize_trade(position, exit_price_raw, candle.timestamp, "STOP_LOSS")

            if target_touched:
                # Resting limit order fills at take profit level (no unearned favorable windfall)
                exit_price_raw = position.take_profit
                return self._finalize_trade(position, exit_price_raw, candle.timestamp, "TAKE_PROFIT")

        else:  # SHORT
            stop_touched = bool(c_high >= position.stop_loss)
            target_touched = bool(position.take_profit is not None and c_low <= position.take_profit)

            if stop_touched and target_touched:
                exit_price_raw = position.stop_loss
                exit_reason = "AMBIGUOUS_BAR_STOP" if self.conservative_ambiguity else "STOP_LOSS"
                return self._finalize_trade(position, exit_price_raw, candle.timestamp, exit_reason)

            if stop_touched:
                exit_price_raw = max(position.stop_loss, c_open)
                return self._finalize_trade(position, exit_price_raw, candle.timestamp, "STOP_LOSS")

            if target_touched:
                # Resting limit order fills at take profit level
                exit_price_raw = position.take_profit
                return self._finalize_trade(position, exit_price_raw, candle.timestamp, "TAKE_PROFIT")

        return None

    def update_trailing_stop(
        self,
        position: ActivePosition,
        candle: ValidatedCandle,
        atr_value: Optional[Decimal] = None,
        atr_multiplier: Decimal = Decimal("2.0"),
        activation_threshold_r: Decimal = Decimal("1.0"),
    ) -> bool:
        """
        Update position high/low watermarks, MFE/MAE, and ratchet trailing stop if activated.
        CRITICAL INVARIANT: Stops only ratchet in the direction of profit.
        Never widens or retreats into higher risk.
        Returns True if trailing stop was ratcheted, False otherwise.
        """
        c_high = Decimal(str(candle.high))
        c_low = Decimal(str(candle.low))

        # 1. Update peak and trough observations
        if c_high > position.peak_price_since_entry:
            position.peak_price_since_entry = c_high
        if c_low < position.trough_price_since_entry:
            position.trough_price_since_entry = c_low

        # 2. Update MFE and MAE
        if position.direction == "LONG":
            fav_dist = position.peak_price_since_entry - position.raw_entry_price
            adv_dist = position.raw_entry_price - position.trough_price_since_entry
        else:
            fav_dist = position.raw_entry_price - position.trough_price_since_entry
            adv_dist = position.peak_price_since_entry - position.raw_entry_price

        if fav_dist > position.mfe:
            position.mfe = fav_dist
        if adv_dist > position.mae:
            position.mae = adv_dist

        if position.exit_policy != "BALANCED":
            return False

        initial_risk = position.initial_risk_per_unit
        if initial_risk <= Decimal("0"):
            return False

        # 3. Check activation threshold in R terms
        favorable_r = fav_dist / initial_risk
        if favorable_r < activation_threshold_r:
            return False

        # 4. Calculate candidate stop
        if position.direction == "LONG":
            if atr_value is not None and atr_value > Decimal("0"):
                candidate = position.peak_price_since_entry - (atr_multiplier * atr_value)
            else:
                candidate = position.peak_price_since_entry - (Decimal("2.0") * initial_risk)

            # Ratchet check: stop can only move UP
            if candidate > position.stop_loss:
                position.stop_loss = candidate
                position.trailing_stop = candidate
                position.trailing_updates_count += 1
                return True

        else:  # SHORT
            if atr_value is not None and atr_value > Decimal("0"):
                candidate = position.trough_price_since_entry + (atr_multiplier * atr_value)
            else:
                candidate = position.trough_price_since_entry + (Decimal("2.0") * initial_risk)

            # Ratchet check: stop can only move DOWN
            if candidate < position.stop_loss:
                position.stop_loss = candidate
                position.trailing_stop = candidate
                position.trailing_updates_count += 1
                return True

        return False

    def execute_pending_reversal(
        self,
        position: ActivePosition,
        candle: ValidatedCandle,
    ) -> SimulatedTrade:
        """
        Execute confirmed reversal exit at current candle open.
        Applies taker fee, spread, and adverse slippage.
        """
        c_open = Decimal(str(candle.open))
        return self._finalize_trade(
            position=position,
            exit_price_raw=c_open,
            exit_timestamp=candle.timestamp,
            exit_reason="REVERSAL_CONFIRMED",
        )

    def force_close(
        self,
        position: ActivePosition,
        candle: ValidatedCandle,
        reason: str = "FORCE_CLOSE",
    ) -> SimulatedTrade:
        """Force close an active position at candle close price (e.g. end of simulation or kill switch)."""
        close_price = Decimal(str(candle.close))
        return self._finalize_trade(position, close_price, candle.timestamp, reason)

    def _finalize_trade(
        self,
        position: ActivePosition,
        exit_price_raw: Decimal,
        exit_timestamp: str,
        exit_reason: str,
    ) -> SimulatedTrade:
        """
        Calculate final trade metrics applying exit slippage, fees, and spread.
        """
        # Ensure final exit price is incorporated into MFE / MAE
        if position.direction == "LONG":
            favorable = exit_price_raw - position.raw_entry_price
            adverse = position.raw_entry_price - exit_price_raw
        else:
            favorable = position.raw_entry_price - exit_price_raw
            adverse = exit_price_raw - position.raw_entry_price

        if favorable > position.mfe:
            position.mfe = favorable
        if adverse > position.mae:
            position.mae = adverse

        if position.direction == "LONG":
            # Long selling at bid - slippage
            friction_multiplier = Decimal("1") - self.slippage_pct - self.spread_fraction
            exec_exit_price = exit_price_raw * friction_multiplier
            gross_pnl = (exit_price_raw - position.raw_entry_price) * position.position_size
        else:
            # Short buying at ask + slippage
            friction_multiplier = Decimal("1") + self.slippage_pct + self.spread_fraction
            exec_exit_price = exit_price_raw * friction_multiplier
            gross_pnl = (position.raw_entry_price - exit_price_raw) * position.position_size

        exit_notional = exec_exit_price * position.position_size
        exit_fee = exit_notional * self.taker_fee_pct
        total_fees = position.entry_fee + exit_fee

        exit_slippage_cost = (exit_price_raw * self.slippage_pct) * position.position_size
        total_slippage_cost = position.entry_slippage_cost + exit_slippage_cost

        exit_spread_cost = (exit_price_raw * self.spread_fraction) * position.position_size
        total_spread_cost = position.entry_spread_cost + exit_spread_cost

        # Net P&L is gross PnL minus all round-trip frictions
        net_pnl = gross_pnl - total_fees - total_slippage_cost - total_spread_cost

        # Calculate holding duration in seconds
        try:
            t_entry = datetime.fromisoformat(position.entry_timestamp.replace("Z", "+00:00"))
            t_exit = datetime.fromisoformat(exit_timestamp.replace("Z", "+00:00"))
            holding_duration = max(0.0, (t_exit - t_entry).total_seconds())
        except Exception:
            holding_duration = 0.0

        return SimulatedTrade(
            trade_id=f"trd_{uuid.uuid4().hex[:12]}",
            symbol=position.symbol,
            timeframe=position.timeframe,
            direction=position.direction,
            signal_timestamp=position.strategy_metadata.get("timestamp", position.entry_timestamp),
            entry_timestamp=position.entry_timestamp,
            entry_price=position.entry_price.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP),
            exit_timestamp=exit_timestamp,
            exit_price=exec_exit_price.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP),
            stop_loss=position.stop_loss,
            take_profit=position.take_profit,
            position_size=position.position_size,
            gross_pnl=gross_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            fees=total_fees.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            spread_cost=total_spread_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            slippage_cost=total_slippage_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            net_pnl=net_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            exit_reason=exit_reason,
            market_regime=position.market_regime,
            strategy_metadata=position.strategy_metadata,
            initial_stop_loss=position.initial_stop_loss,
            final_stop_loss=position.stop_loss,
            trailing_stop_updates=position.trailing_updates_count,
            peak_favorable_price=position.peak_price_since_entry if position.direction == "LONG" else position.trough_price_since_entry,
            original_theoretical_target=position.theoretical_take_profit,
            reversal_detection_timestamp=position.reversal_detection_timestamp,
            mfe=position.mfe.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            mae=position.mae.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            holding_duration_seconds=holding_duration,
            reversal_reasons=list(position.reversal_reason_codes),
            reversal_superseded=getattr(position, "reversal_superseded", False),
        )

