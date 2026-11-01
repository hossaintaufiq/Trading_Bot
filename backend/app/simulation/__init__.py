"""NEPTUNE Historical Simulation and Backtesting Module."""
from app.simulation.engine import HistoricalBacktestEngine
from app.simulation.execution import PaperExecutionSimulator
from app.simulation.metrics import calculate_backtest_metrics
from app.simulation.models import (
    ActivePosition,
    BacktestConfig,
    BacktestMetrics,
    BacktestResult,
    EquityPoint,
    SimulatedTrade,
)
from app.simulation.reversal import MultiFactorReversalDetector, ReversalDecision
from app.simulation.walk_forward import WalkForwardValidator

__all__ = [
    "ActivePosition",
    "BacktestConfig",
    "BacktestMetrics",
    "BacktestResult",
    "EquityPoint",
    "HistoricalBacktestEngine",
    "MultiFactorReversalDetector",
    "PaperExecutionSimulator",
    "ReversalDecision",
    "SimulatedTrade",
    "WalkForwardValidator",
    "calculate_backtest_metrics",
]

