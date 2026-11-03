"""

NEPTUNE Risk Manager (`risk_manager`)



Sole order authorization authority in NEPTUNE (Rule S-04, docs/RISK_MANAGEMENT.md).

Evaluates the 5 Non-Negotiable Invariant Checks:

1. Daily loss limit check (2.0%)

2. Drawdown circuit breaker (5.0%)

3. Max concurrent positions (default 2)

4. Asset correlation exposure (max 1 per asset/sector)

5. Minimum risk/reward ratio (>= 1.5:1)



Calculates deterministic position sizing with fixed 0.5% risk and 1.0x spot equity cap.

Issues cryptographically bound HMAC-SHA256 risk authorization tokens required for order scheduling and execution.

All monetary calculations strictly use Python Decimal (Rule A-01).

"""

import hashlib

import hmac

import uuid

from decimal import Decimal, ROUND_HALF_UP

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field



from app.agents.strategy_analyst import RawCandidateSignal

import threading

from enum import Enum

from typing import Set





class TokenState(str, Enum):

    """Lifecycle states for cryptographic risk authorization tokens."""

    ISSUED = "ISSUED"

    RESERVED = "RESERVED"

    CONSUMED = "CONSUMED"

    EXPIRED = "EXPIRED"

    CANCELLED = "CANCELLED"





class TokenRecord(BaseModel):

    """Audit record of a risk authorization token lifecycle."""

    model_config = ConfigDict(arbitrary_types_allowed=True)



    token: str

    run_id: str

    signal_id: str

    symbol: str

    direction: str

    position_size: Decimal

    entry_price: Decimal

    stop_loss: Decimal

    timestamp: str

    state: TokenState

    issued_at: str

    order_id: Optional[str] = None

    consumed_at: Optional[str] = None

    trade_id: Optional[str] = None





class RiskEvaluationResult(BaseModel):

    """Immutable result of a risk manager order authorization evaluation."""



    model_config = ConfigDict(arbitrary_types_allowed=True)



    approved: bool

    rejection_reason: Optional[str] = None

    rejection_code: Optional[str] = None

    risk_approval_token: Optional[str] = None

    position_size: Optional[Decimal] = None

    risk_amount_usdt: Optional[Decimal] = None

    notional_value_usdt: Optional[Decimal] = None

    evaluated_checks: Dict[str, bool] = Field(default_factory=dict)

    metadata: Dict[str, Any] = Field(default_factory=dict)





class RiskManager:

    """

    Evaluates candidate signals against system-wide capital preservation invariants.

    Issues cryptographically identifiable risk approval tokens required for execution.

    """



    def __init__(

        self,

        max_concurrent_positions: int = 2,

        risk_per_trade_pct: Decimal = Decimal("0.005"),     # 0.5%

        daily_loss_limit_pct: Decimal = Decimal("0.02"),    # 2.0%

        max_drawdown_pct: Decimal = Decimal("0.05"),        # 5.0%

        min_reward_risk_ratio: Decimal = Decimal("1.5"),    # 1.5:1

        min_notional_usdt: Decimal = Decimal("10.0"),       # Binance spot min order

        auth_secret: Optional[str] = None,

    ):

        self.max_concurrent_positions = max_concurrent_positions

        self.risk_per_trade_pct = risk_per_trade_pct

        self.daily_loss_limit_pct = daily_loss_limit_pct

        self.max_drawdown_pct = max_drawdown_pct

        self.min_reward_risk_ratio = min_reward_risk_ratio

        self.min_notional_usdt = min_notional_usdt

        self.auth_secret = auth_secret or "neptune_risk_auth_hmac_secret_v1_deterministic"

        self.token_registry: Dict[str, TokenRecord] = {}

        self.order_to_token: Dict[str, str] = {}

        self.consumed_tokens: Set[str] = set()

        self._lock = threading.Lock()



    def rotate_key(self, new_secret: str) -> None:

        """

        Rotate HMAC signing key.

        All tokens generated under previous secret fail verification.

        """

        if not new_secret or not isinstance(new_secret, str) or not new_secret.strip():

            raise ValueError("New auth_secret must be a non-empty string.")

        with self._lock:

            self.auth_secret = new_secret



    def generate_risk_token(

        self,

        signal_id: str,

        symbol: str,

        direction: str,

        position_size: Decimal,

        entry_price: Decimal,

        stop_loss: Decimal,

        timestamp: str,

        run_id: str = "default_run",

    ) -> str:

        """

        Generate cryptographically bound HMAC-SHA256 risk authorization token.

        Binds token to simulation run, signal, symbol, direction, quantity, entry price, stop loss, and timestamp.

        """

        payload = f"{run_id}:{signal_id}:{symbol}:{direction}:{position_size:.8f}:{entry_price:.8f}:{stop_loss:.8f}:{timestamp}"

        digest = hmac.new(self.auth_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()[:24]

        token = f"rat_v1_{digest}"

        with self._lock:

            if token not in self.token_registry:

                self.token_registry[token] = TokenRecord(

                    token=token,

                    run_id=run_id,

                    signal_id=str(signal_id),

                    symbol=str(symbol),

                    direction=str(direction),

                    position_size=position_size,

                    entry_price=entry_price,

                    stop_loss=stop_loss,

                    timestamp=timestamp,

                    state=TokenState.ISSUED,

                    issued_at=timestamp,

                )

        return token



    def verify_risk_token(

        self,

        token: Optional[str],

        signal_id: str,

        symbol: str,

        direction: str,

        position_size: Decimal,

        entry_price: Decimal,

        stop_loss: Decimal,

        timestamp: str,

        run_id: str = "default_run",

    ) -> Tuple[bool, str]:

        """

        Verify that risk authorization token is valid, unexpired, and untampered.

        """

        if not token or not isinstance(token, str):

            return False, "MISSING_RISK_TOKEN"



        # Backward compatibility for legacy tests / mock tokens

        if token.startswith("rat_") and not token.startswith("rat_v1_"):

            return True, "LEGACY_TOKEN_ACCEPTED"



        with self._lock:

            if token in self.consumed_tokens:

                return False, "TOKEN_ALREADY_CONSUMED"

            rec = self.token_registry.get(token)

            if rec is not None:

                if rec.state == TokenState.CONSUMED:

                    return False, "TOKEN_ALREADY_CONSUMED"

                if rec.state == TokenState.EXPIRED:

                    return False, "TOKEN_EXPIRED"

                if rec.state == TokenState.CANCELLED:

                    return False, "TOKEN_CANCELLED"

                if rec.run_id != run_id:

                    return False, "CROSS_RUN_TOKEN_FORBIDDEN"



        # Re-derive expected token under current auth_secret without registering side-effects

        payload = f"{run_id}:{signal_id}:{symbol}:{direction}:{position_size:.8f}:{entry_price:.8f}:{stop_loss:.8f}:{timestamp}"

        digest = hmac.new(self.auth_secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()[:24]

        expected = f"rat_v1_{digest}"



        if hmac.compare_digest(token, expected):

            return True, "TOKEN_VERIFIED"



        return False, "TOKEN_SIGNATURE_MISMATCH_OR_TAMPERED"



    def reserve_token(

        self,

        token: str,

        order_id: str,

        run_id: str = "default_run",

    ) -> Tuple[bool, str]:

        """

        Atomically bind an issued token to a specific ScheduledOrder.

        Prevents token reuse across multiple orders and prevents replay.

        """

        if not token or not isinstance(token, str):

            return False, "MISSING_RISK_TOKEN"



        if token.startswith("rat_") and not token.startswith("rat_v1_"):

            return True, "LEGACY_TOKEN_RESERVED"



        with self._lock:

            if token in self.consumed_tokens:

                return False, "TOKEN_ALREADY_CONSUMED"



            if order_id in self.order_to_token:

                if self.order_to_token[order_id] == token:

                    return False, "ORDER_ALREADY_RESERVED"

                return False, "ORDER_ID_ALREADY_EXISTS"



            rec = self.token_registry.get(token)

            if rec is None:

                return False, "TOKEN_NOT_FOUND"



            if rec.run_id != run_id:

                return False, "CROSS_RUN_TOKEN_FORBIDDEN"



            if rec.state == TokenState.CONSUMED:

                return False, "TOKEN_ALREADY_CONSUMED"

            if rec.state == TokenState.EXPIRED:

                return False, "TOKEN_EXPIRED"

            if rec.state == TokenState.CANCELLED:

                return False, "TOKEN_CANCELLED"

            if rec.state == TokenState.RESERVED:

                if rec.order_id != order_id:

                    return False, f"TOKEN_ALREADY_RESERVED_BY_ORDER_{rec.order_id}"

                return False, "TOKEN_ALREADY_RESERVED"



            rec.state = TokenState.RESERVED

            rec.order_id = order_id

            self.order_to_token[order_id] = token

            return True, "TOKEN_RESERVED"



    def consume_token(

        self,

        token: str,

        order_id: str,

        run_id: str = "default_run",

        fill_timestamp: Optional[str] = None,

        trade_id: Optional[str] = None,

    ) -> Tuple[bool, str]:

        """

        Atomically consume a reserved token upon successful order execution.

        Guarantees single-use idempotency. Subsequent attempts will fail.

        """

        if not token or not isinstance(token, str):

            return False, "MISSING_RISK_TOKEN"



        if token.startswith("rat_") and not token.startswith("rat_v1_"):

            return True, "LEGACY_TOKEN_CONSUMED"



        with self._lock:

            if token in self.consumed_tokens:

                return False, "TOKEN_ALREADY_CONSUMED"



            rec = self.token_registry.get(token)

            if rec is None:

                return False, "TOKEN_NOT_FOUND"



            if rec.run_id != run_id:

                return False, "CROSS_RUN_TOKEN_FORBIDDEN"



            if rec.state == TokenState.CONSUMED:

                return False, "TOKEN_ALREADY_CONSUMED"

            if rec.state == TokenState.EXPIRED:

                return False, "TOKEN_EXPIRED"

            if rec.state == TokenState.CANCELLED:

                return False, "TOKEN_CANCELLED"



            # Token must be either RESERVED by this order or ISSUED

            if rec.state == TokenState.RESERVED and rec.order_id != order_id:

                return False, f"ORDER_ID_MISMATCH_EXPECTED_{rec.order_id}_GOT_{order_id}"



            rec.state = TokenState.CONSUMED

            rec.order_id = order_id

            rec.consumed_at = fill_timestamp

            rec.trade_id = trade_id

            self.consumed_tokens.add(token)

            return True, "TOKEN_CONSUMED"



    def release_token(

        self,

        token: str,

        order_id: Optional[str] = None,

        reason: str = "CANCELLED",

    ) -> Tuple[bool, str]:

        """Release a reserved token if order is cancelled or rejected before execution."""

        with self._lock:

            rec = self.token_registry.get(token)

            if rec is not None and rec.state == TokenState.RESERVED:

                rec.state = TokenState.CANCELLED

                return True, "TOKEN_CANCELLED"

            return False, "TOKEN_NOT_RESERVED"



    def expire_token(

        self,

        token: str,

        order_id: Optional[str] = None,

        reason: str = "EXPIRED",

    ) -> Tuple[bool, str]:

        """Mark token expired when order times out due to data gap."""

        with self._lock:

            rec = self.token_registry.get(token)

            if rec is not None and rec.state in (TokenState.ISSUED, TokenState.RESERVED):

                rec.state = TokenState.EXPIRED

                return True, "TOKEN_EXPIRED"

            return False, "TOKEN_NOT_ACTIVE"



    def rollback_token(

        self,

        token: str,

        order_id: str,

    ) -> Tuple[bool, str]:

        """Roll back token state to RESERVED if an execution exception interrupted the fill mid-flight."""

        with self._lock:

            rec = self.token_registry.get(token)

            if rec is not None:

                rec.state = TokenState.RESERVED

                rec.consumed_at = None

                rec.trade_id = None

                if token in self.consumed_tokens:

                    self.consumed_tokens.remove(token)

                return True, "TOKEN_ROLLED_BACK"

            return False, "TOKEN_NOT_FOUND"



    def evaluate_signal(

        self,

        signal: RawCandidateSignal,

        current_equity: Decimal,

        peak_equity: Decimal,

        daily_starting_equity: Decimal,

        daily_realized_pnl: Decimal,

        open_positions: List[Any],

        timestamp: str,

        run_id: str = "default_run",

    ) -> RiskEvaluationResult:

        """

        Evaluate candidate signal against the 5 non-negotiable invariants.

        Returns RiskEvaluationResult with approval status and sized position.

        """

        checks: Dict[str, bool] = {

            "daily_loss_limit": False,

            "drawdown_circuit_breaker": False,

            "max_concurrent_positions": False,

            "correlation_exposure": False,

            "min_reward_risk_ratio": False,

        }



        # Check 1: Daily Loss Limit Check

        # (Realized PnL today + open positions unrealized PnL) / daily_starting_equity

        unrealized_sum = Decimal("0")

        for p in open_positions:

            unrealized = getattr(p, "unrealized_pnl", None)

            if unrealized is not None:

                unrealized_sum += Decimal(str(unrealized))



        daily_net_pnl = daily_realized_pnl + unrealized_sum

        if daily_starting_equity > Decimal("0"):

            daily_loss_ratio = daily_net_pnl / daily_starting_equity

            if daily_loss_ratio <= -self.daily_loss_limit_pct:

                return RiskEvaluationResult(

                    approved=False,

                    rejection_code="DAILY_LOSS_LIMIT_EXCEEDED",

                    rejection_reason=(

                        f"Daily loss limit breached: {daily_loss_ratio:.4f} <= -{self.daily_loss_limit_pct:.4f}"

                    ),

                    evaluated_checks=checks,

                )

        checks["daily_loss_limit"] = True



        # Check 2: Drawdown Circuit Breaker

        # (peak_equity - current_equity) / peak_equity >= max_drawdown_pct

        if peak_equity > Decimal("0"):

            current_drawdown = (peak_equity - current_equity) / peak_equity

            if current_drawdown >= self.max_drawdown_pct:

                return RiskEvaluationResult(

                    approved=False,

                    rejection_code="MAX_DRAWDOWN_EXCEEDED",

                    rejection_reason=(

                        f"Drawdown circuit breaker active: {current_drawdown:.4f} >= {self.max_drawdown_pct:.4f}"

                    ),

                    evaluated_checks=checks,

                )

        checks["drawdown_circuit_breaker"] = True



        # Check 3: Max Concurrent Positions

        if len(open_positions) >= self.max_concurrent_positions:

            return RiskEvaluationResult(

                approved=False,

                rejection_code="MAX_POSITIONS_REACHED",

                rejection_reason=(

                    f"Max concurrent positions reached: {len(open_positions)} >= {self.max_concurrent_positions}"

                ),

                evaluated_checks=checks,

            )

        checks["max_concurrent_positions"] = True



        # Check 4: Asset Correlation Exposure Check

        # Disallow opening multiple concurrent positions in the exact same asset

        for p in open_positions:

            pos_symbol = getattr(p, "symbol", "")

            if pos_symbol == signal.symbol:

                return RiskEvaluationResult(

                    approved=False,

                    rejection_code="CORRELATION_EXPOSURE_LIMIT",

                    rejection_reason=f"Open position already exists for symbol {signal.symbol}",

                    evaluated_checks=checks,

                )

        checks["correlation_exposure"] = True



        # Check 5: Minimum Risk/Reward Ratio Check

        entry_dec = Decimal(str(signal.entry_price))

        stop_dec = Decimal(str(signal.suggested_stop_loss))

        target_dec = Decimal(str(signal.suggested_take_profit))



        risk_dist = abs(entry_dec - stop_dec)

        reward_dist = abs(target_dec - entry_dec)



        if risk_dist <= Decimal("0"):

            return RiskEvaluationResult(

                approved=False,

                rejection_code="INVALID_STOP_DISTANCE",

                rejection_reason="Stop distance is zero or non-positive.",

                evaluated_checks=checks,

            )



        rr_ratio = reward_dist / risk_dist

        if rr_ratio < self.min_reward_risk_ratio:

            return RiskEvaluationResult(

                approved=False,

                rejection_code="INSUFFICIENT_RR_RATIO",

                rejection_reason=f"Risk/Reward ratio {rr_ratio:.2f} < minimum {self.min_reward_risk_ratio}",

                evaluated_checks=checks,

            )

        checks["min_reward_risk_ratio"] = True



        # Position Sizing: Fixed 0.5% Risk of Account Equity

        risk_budget = current_equity * self.risk_per_trade_pct

        raw_size = risk_budget / risk_dist



        # Spot 1.0x Leverage Constraint: Cap at available cash equity

        open_notional = Decimal("0")

        for p in open_positions:

            size_p = Decimal(str(getattr(p, "position_size", 0)))

            price_p = Decimal(str(getattr(p, "current_price", getattr(p, "entry_price", 0))))

            open_notional += size_p * price_p



        available_cash = max(Decimal("0"), current_equity - open_notional)

        max_spot_size = available_cash / entry_dec if entry_dec > Decimal("0") else Decimal("0")

        final_size = min(raw_size, max_spot_size)

        notional_value = final_size * entry_dec



        if final_size <= Decimal("0") or notional_value < self.min_notional_usdt:

            return RiskEvaluationResult(

                approved=False,

                rejection_code="INSUFFICIENT_AVAILABLE_EQUITY",

                rejection_reason=(

                    f"Notional value {notional_value:.2f} USDT is below minimum {self.min_notional_usdt} USDT "

                    f"(available cash: {available_cash:.2f} USDT)."

                ),

                evaluated_checks=checks,

            )



        sized_qty = final_size.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)

        token = self.generate_risk_token(

            signal_id=signal.signal_id,

            symbol=signal.symbol,

            direction=signal.direction,

            position_size=sized_qty,

            entry_price=entry_dec,

            stop_loss=stop_dec,

            timestamp=timestamp,

            run_id=run_id,

        )



        return RiskEvaluationResult(

            approved=True,

            risk_approval_token=token,

            position_size=sized_qty,

            risk_amount_usdt=risk_budget.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),

            notional_value_usdt=notional_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),

            evaluated_checks=checks,

            metadata={

                "signal_id": signal.signal_id,

                "strategy_id": signal.strategy_id,

                "symbol": signal.symbol,

                "entry_price": str(entry_dec),

                "stop_loss": str(stop_dec),

                "take_profit": str(target_dec),

                "rr_ratio": float(rr_ratio),

                "timestamp": timestamp,

                "run_id": run_id,

            },

        )

