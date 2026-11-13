"""
Daily Donchian Trend Strategy (`daily_trend_v1` / SHR-002 / ADR-037)

Long-only spot trend following on CLOSED daily candles:
- Enter long when the close breaks above the highest close of the prior `entry_lookback` days.
- Exit when the close falls below the lowest close of the prior `exit_lookback` days.
- Otherwise flat (cash). Signals are decided at a candle close and filled at the NEXT open (A-09).

Rationale: low turnover keeps the 0.32% round-trip cost small relative to trend moves.
Candidate selected on 2018-2023 only; 2024-2026 evaluated once (see ADR-037).
No profitability is assumed (A-08, S-07).
"""
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd
from pydantic import BaseModel

from app.strategies.base_strategy import BaseStrategy, RawSignal, SignalDirection, TimeFrame


class DailyTrendConfig(BaseModel):
    entry_lookback: int = 20
    exit_lookback: int = 10


def compute_positions(closes: List[float], entry_lookback: int, exit_lookback: int) -> List[int]:
    """
    Return the desired position (1 long / 0 flat) AFTER each bar's close.
    Uses only closes up to and including bar i (channels are computed from PRIOR bars), so
    the state at i can be acted on at the open of bar i+1 with no look-ahead.
    """
    state = 0
    out: List[int] = []
    for i, c in enumerate(closes):
        if state == 0:
            if i >= entry_lookback and c > max(closes[i - entry_lookback : i]):
                state = 1
        else:
            if i >= exit_lookback and c < min(closes[i - exit_lookback : i]):
                state = 0
        out.append(state)
    return out


class DailyTrendStrategy(BaseStrategy):
    strategy_id = "daily_trend_v1"
    strategy_name = "Daily Donchian Trend (long-only)"
    supported_timeframes = [TimeFrame.D1]

    def __init__(self, config: Optional[DailyTrendConfig] = None):
        self.config = config or DailyTrendConfig()

    def get_entry_conditions(self) -> List[str]:
        return [f"Daily close > highest close of prior {self.config.entry_lookback} days"]

    def get_exit_conditions(self) -> List[str]:
        return [f"Daily close < lowest close of prior {self.config.exit_lookback} days (exit at next open)"]

    def get_invalidation_rules(self) -> List[str]:
        return ["Portfolio drawdown circuit breaker (see ADR-037)", "Candle not closed"]

    def position_state(self, df: pd.DataFrame) -> int:
        """Desired position after the last closed candle in df (1 long, 0 flat)."""
        if "is_closed" in df.columns:
            df = df[df["is_closed"] == True]  # noqa: E712  (A-09)
        pos = compute_positions([float(x) for x in df["close"]], self.config.entry_lookback, self.config.exit_lookback)
        return pos[-1] if pos else 0

    def evaluate(self, df: pd.DataFrame, symbol: str, timeframe: TimeFrame = TimeFrame.D1) -> Optional[RawSignal]:
        """Emit a LONG signal only on the bar where the state flips from flat to long."""
        if "is_closed" in df.columns:
            df = df[df["is_closed"] == True]  # noqa: E712
        closes = [float(x) for x in df["close"]]
        pos = compute_positions(closes, self.config.entry_lookback, self.config.exit_lookback)
        if len(pos) < 2 or not (pos[-1] == 1 and pos[-2] == 0):
            return None
        lb = self.config.exit_lookback
        stop = min(closes[-1 - lb : -1])
        ts = df["timestamp"].iloc[-1] if "timestamp" in df.columns else datetime.now(timezone.utc)
        ts = pd.Timestamp(ts).to_pydatetime()
        return RawSignal(
            strategy_id=self.strategy_id, symbol=symbol, timeframe=TimeFrame.D1,
            direction=SignalDirection.LONG,
            entry_price=closes[-1], stop_price=stop, target_price=closes[-1] * 10,  # no fixed target; trend exit
            signal_strength=0.5, invalidation_price=stop, max_holding_candles=10_000,
            generated_at=ts,
            explanation=f"Close broke {self.config.entry_lookback}-day high; exit on {lb}-day low break.",
            metadata={"entry_lookback": self.config.entry_lookback, "exit_lookback": lb},
        )
