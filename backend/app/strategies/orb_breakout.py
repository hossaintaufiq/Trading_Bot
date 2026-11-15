"""
Opening-Range Breakout, crypto edition (`orb_breakout_v1` / ADR-038).

Adapted from the day-trader-skill method (opening range -> first closing break -> stop at range
midpoint -> R-multiple target -> flat by session end) to a 24/7 market: the "session" is the UTC day
and the "open" is 00:00 UTC. Long-only, spot, no leverage.

Rules (A-09): only fully closed candles are used. The trigger is the first closed bar after the
opening range whose CLOSE is above the range high; a wick above is not a trigger. Entries stop at
`cutoff_bar`. The target defaults to 1.5R so the setup satisfies the project's minimum R:R of 1.5.
No profitability is assumed (A-08, S-07): this is a research candidate that must be backtested.
"""
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd
from pydantic import BaseModel

from app.strategies.base_strategy import BaseStrategy, RawSignal, SignalDirection, TimeFrame


class ORBConfig(BaseModel):
    bars_per_day: int = 96     # 15m bars per UTC day
    or_bars: int = 4           # opening range = first 4 bars (1 hour at 15m)
    cutoff_bar: int = 48       # no entries at/after bar 48 (12:00 UTC at 15m)
    target_r: float = 1.5      # target = signal close + target_r * risk


@dataclass(frozen=True)
class ORBSetup:
    trigger_idx: int           # bar (within the day) whose close broke the range
    range_high: float
    range_low: float
    stop: float                # range midpoint
    signal_price: float        # close of the trigger bar


def find_setup(day: pd.DataFrame, cfg: ORBConfig) -> Optional[ORBSetup]:
    """First closed bar after the opening range that closes above the range high. `day` = closed bars of one UTC day."""
    if len(day) <= cfg.or_bars:
        return None
    highs, lows, closes = (day[c].astype(float).tolist() for c in ("high", "low", "close"))
    rh, rl = max(highs[: cfg.or_bars]), min(lows[: cfg.or_bars])
    stop = (rh + rl) / 2
    for i in range(cfg.or_bars, min(cfg.cutoff_bar, len(day))):
        if closes[i] > rh:
            return ORBSetup(i, rh, rl, stop, closes[i]) if closes[i] > stop else None
    return None


class ORBStrategy(BaseStrategy):
    strategy_id = "orb_breakout_v1"
    strategy_name = "Opening-Range Breakout (UTC day, long-only)"
    supported_timeframes = [TimeFrame.M15]

    def __init__(self, config: Optional[ORBConfig] = None):
        self.config = config or ORBConfig()

    def get_entry_conditions(self) -> List[str]:
        c = self.config
        return [f"First closed bar after the first {c.or_bars} bars of the UTC day that closes above the range high",
                f"Trigger before bar {c.cutoff_bar} of the day"]

    def get_exit_conditions(self) -> List[str]:
        return ["Stop at the opening-range midpoint", f"Target at {self.config.target_r}R",
                "Flat at the last bar of the UTC day"]

    def get_invalidation_rules(self) -> List[str]:
        return ["Next open at or below the stop (gap)", "Candle not closed", "Entry window passed"]

    def evaluate(self, df: pd.DataFrame, symbol: str, timeframe: TimeFrame = TimeFrame.M15) -> Optional[RawSignal]:
        """Signal only when the LAST closed bar is the trigger bar of today's range."""
        if "is_closed" in df.columns:
            df = df[df["is_closed"] == True]  # noqa: E712  (A-09)
        if df.empty:
            return None
        ts = pd.to_datetime(df["timestamp"], utc=True)
        day = df[ts.dt.normalize() == ts.iloc[-1].normalize()].reset_index(drop=True)
        setup = find_setup(day, self.config)
        if setup is None or setup.trigger_idx != len(day) - 1:
            return None
        risk = setup.signal_price - setup.stop
        return RawSignal(
            strategy_id=self.strategy_id, symbol=symbol, timeframe=TimeFrame.M15, direction=SignalDirection.LONG,
            entry_price=setup.signal_price, stop_price=setup.stop,
            target_price=setup.signal_price + self.config.target_r * risk,
            signal_strength=0.5, invalidation_price=setup.stop,
            max_holding_candles=self.config.bars_per_day - setup.trigger_idx,
            generated_at=pd.Timestamp(ts.iloc[-1]).to_pydatetime(),
            explanation=f"Closed above opening range high {setup.range_high:.2f}; stop at midpoint {setup.stop:.2f}.",
            metadata={"range_high": setup.range_high, "range_low": setup.range_low, "trigger_idx": setup.trigger_idx},
        )
