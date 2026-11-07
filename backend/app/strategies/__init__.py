"""NEPTUNE Quantitative Trading Strategies Package."""
from app.strategies.base_strategy import (
    BaseStrategy,
    RawSignal,
    SignalDirection,
    TimeFrame,
)
from app.strategies.dual_timeframe_trend import (
    DualTimeframeConfig,
    DualTimeframeTrendStrategy,
)

__all__ = [
    "BaseStrategy",
    "RawSignal",
    "SignalDirection",
    "TimeFrame",
    "DualTimeframeConfig",
    "DualTimeframeTrendStrategy",
]

