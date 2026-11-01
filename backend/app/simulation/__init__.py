"""NEPTUNE Historical Simulation and Backtesting Module."""
from app.simulation.benchmark import (
    BenchmarkReport,
    DatasetEvaluationResult,
    ExitPolicyBenchmark,
    PolicyMetricsComparison,
)
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
    "BenchmarkReport",
    "DatasetEvaluationResult",
    "EquityPoint",
    "ExitPolicyBenchmark",
    "HistoricalBacktestEngine",
    "MultiFactorReversalDetector",
    "PaperExecutionSimulator",
    "PolicyMetricsComparison",
    "ReversalDecision",
    "SimulatedTrade",
    "WalkForwardValidator",
    "calculate_backtest_metrics",
]

