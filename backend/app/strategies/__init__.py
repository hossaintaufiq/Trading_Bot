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
from app.strategies.dual_timeframe_trend_v2 import (
    DualTimeframeConfigV2,
    DualTimeframeTrendStrategyV2,
)

__all__ = [
    "BaseStrategy",
    "RawSignal",
    "SignalDirection",
    "TimeFrame",
    "DualTimeframeConfig",
    "DualTimeframeTrendStrategy",
    "DualTimeframeConfigV2",
    "DualTimeframeTrendStrategyV2",
]

