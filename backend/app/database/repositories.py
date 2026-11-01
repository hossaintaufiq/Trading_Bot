"""
Storage Repository Interfaces.

Business logic must depend on these interfaces, never on SQLite or filesystem directly.
This enables storage backends to be swapped without changing domain logic.
"""
import abc
from datetime import datetime
from typing import List, Optional, Protocol

import pandas as pd


class IMarketDataRepository(Protocol):
    """Interface for reading and writing market candle data."""

    async def save_candles(
        self, symbol: str, timeframe: str, df: pd.DataFrame
    ) -> int:
        """Upsert candles into Parquet storage. Returns count written."""
        ...

    async def load_candles(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """Load candles from Parquet storage. Returns DataFrame sorted by timestamp asc."""
        ...

    async def get_latest_candle_time(
        self, symbol: str, timeframe: str
    ) -> Optional[datetime]:
        """Return the timestamp of the most recent stored candle."""
        ...


class ISignalRepository(Protocol):
    """Interface for persisting and querying signals."""

    async def save_signal(self, signal: dict) -> str:
        """Persist a signal. Returns signal_id."""
        ...

    async def get_signal(self, signal_id: str) -> Optional[dict]:
        ...

    async def list_signals(
        self, symbol: Optional[str] = None, limit: int = 50
    ) -> List[dict]:
        ...


class IOrderRepository(Protocol):
    """Interface for paper order persistence."""

    async def create_order(self, order: dict) -> str:
        """Persist a new paper order. Returns order_id."""
        ...

    async def update_order(self, order_id: str, updates: dict) -> None:
        ...

    async def get_order(self, order_id: str) -> Optional[dict]:
        ...

    async def list_open_orders(self) -> List[dict]:
        ...


class IPositionRepository(Protocol):
    """Interface for position accounting."""

    async def open_position(self, position: dict) -> str:
        """Open a new position. Returns position_id."""
        ...

    async def update_position(self, position_id: str, updates: dict) -> None:
        ...

    async def close_position(self, position_id: str, close_data: dict) -> None:
        ...

    async def get_open_positions(self) -> List[dict]:
        ...

    async def get_position(self, position_id: str) -> Optional[dict]:
        ...


class IBrainDecisionRepository(Protocol):
    """Interface for Central Brain state transition records."""

    async def record_transition(self, decision: dict) -> str:
        """Record a brain state transition. Returns decision_id."""
        ...

    async def list_decisions(self, limit: int = 100) -> List[dict]:
        ...


class ISimulationRepository(Protocol):
    """Interface for simulation records and Parquet path outputs."""

    async def save_simulation_record(self, record: dict) -> str:
        """Save simulation metadata. Returns simulation_id."""
        ...

    async def save_simulation_paths(
        self, simulation_id: str, paths_df: pd.DataFrame
    ) -> None:
        """Save 1000 simulated paths to Parquet."""
        ...

    async def get_simulation_record(self, simulation_id: str) -> Optional[dict]:
        ...

    async def load_simulation_paths(self, simulation_id: str) -> pd.DataFrame:
        ...


class IBacktestRepository(Protocol):
    """Interface for backtest run summaries and trade outputs."""

    async def save_backtest_run(self, run_data: dict) -> str:
        """Save backtest metadata summary. Returns backtest_id."""
        ...

    async def get_backtest_run(self, backtest_id: str) -> Optional[dict]:
        ...

    async def list_backtest_runs(
        self, strategy_id: Optional[str] = None, limit: int = 50
    ) -> List[dict]:
        ...


