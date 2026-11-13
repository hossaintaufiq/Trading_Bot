"""
Strategy Base Interface — all strategies must implement this contract.

Rules:
- Strategies are independent. They do not call each other.
- Strategies do NOT execute orders. They generate signals only.
- Signals must pass through the Central Brain → Signal Validator → Risk Manager.
- Every strategy must define its own stop, target, and invalidation rules.
- Strategies must declare which timeframes they support.
"""
import abc
from datetime import datetime
from enum import Enum
from typing import List, Optional

import pandas as pd
from pydantic import BaseModel


class SignalDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class TimeFrame(str, Enum):
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


class RawSignal(BaseModel):
    """Output of a strategy evaluation — not yet validated or approved."""
    strategy_id: str
    symbol: str
    timeframe: TimeFrame
    direction: SignalDirection
    entry_price: float
    stop_price: float
    target_price: float
    signal_strength: float          # 0.0 – 1.0
    invalidation_price: float
    max_holding_candles: int
    generated_at: datetime
    explanation: str
    metadata: dict = {}

    @property
    def reward_risk_ratio(self) -> float:
        """Compute R:R ratio. Positive for valid setups."""
        if self.direction == SignalDirection.LONG:
            risk = self.entry_price - self.stop_price
            reward = self.target_price - self.entry_price
        else:
            risk = self.stop_price - self.entry_price
            reward = self.entry_price - self.target_price

        if risk <= 0:
            return 0.0
        return reward / risk


class BacktestResult(BaseModel):
    strategy_id: str
    symbol: str
    timeframe: TimeFrame
    period_start: datetime
    period_end: datetime
    total_trades: int
    win_rate: float
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    max_drawdown_pct: float
    net_pnl_pct: float
    sharpe_ratio: Optional[float] = None
    notes: str = ""


class BaseStrategy(abc.ABC):
    """
    Abstract base for all NEPTUNE trading strategies.

    Subclasses must implement:
      - strategy_id: str
      - strategy_name: str
      - supported_timeframes: List[TimeFrame]
      - evaluate(df: pd.DataFrame, symbol: str, timeframe: TimeFrame) -> Optional[RawSignal]
    """

    strategy_id: str = "base"
    strategy_name: str = "Base Strategy"
    supported_timeframes: List[TimeFrame] = []

    @abc.abstractmethod
    def evaluate(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: TimeFrame,
    ) -> Optional[RawSignal]:
        """
        Evaluate market conditions and return a RawSignal if a setup is found.

        IMPORTANT:
        - df must contain ONLY fully closed candles.
        - df must be sorted ascending by timestamp.
        - This method must NOT be used for live order execution.
        - A returned signal is a raw proposal — it still requires validation and risk approval.

        Returns None if no valid setup is found.
        """
        ...

    @abc.abstractmethod
    def get_entry_conditions(self) -> List[str]:
        """Human-readable entry condition descriptions."""
        ...

    @abc.abstractmethod
    def get_exit_conditions(self) -> List[str]:
        """Human-readable exit condition descriptions."""
        ...

    @abc.abstractmethod
    def get_invalidation_rules(self) -> List[str]:
        """Conditions that invalidate a pending signal."""
        ...

    def is_timeframe_supported(self, timeframe: TimeFrame) -> bool:
        return timeframe in self.supported_timeframes

    def __repr__(self) -> str:
        return f"<Strategy id={self.strategy_id} name={self.strategy_name}>"

