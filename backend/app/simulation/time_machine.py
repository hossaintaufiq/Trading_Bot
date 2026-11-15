"""
Time Machine (ADR-038): bootstrap forward simulation for one candidate trade.

Replays the rest of the UTC session many times from the symbol's OWN past sessions and reports how
often the target, the stop, or neither is touched first. Method adapted from day-trader-skill and
TIME_MACHINE_SPECIFICATION.md.

- `session_block` (default): resample whole past sessions' remaining bars, rescaled to the entry
  (keeps intraday volatility clustering and autocorrelation).
- `candle_iid`: resample each remaining bar independently from the same time-of-day slot.

Look-ahead (S-05): pass `before=<signal date>` to `session_matrix`; sessions on/after it are excluded.
Conservative tie rule: if a bar touches both levels, the stop is assumed first. This is a simulation of
history, not a prediction; fees/slippage are NOT modelled here (the backtest models them).
Probabilities are statistics, not money, so numpy floats are acceptable (A-01 concerns monetary values).
"""
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
import pandas as pd

OPEN, TARGET, STOP = 0, 1, 2


@dataclass(frozen=True)
class SessionMatrix:
    O: np.ndarray
    H: np.ndarray
    L: np.ndarray
    C: np.ndarray
    dates: Tuple[str, ...]

    @property
    def n_sessions(self) -> int:
        return len(self.dates)


@dataclass(frozen=True)
class TMResult:
    method: str
    n_paths: int
    seed: int
    n_sessions: int
    p_target: float
    p_stop: float
    p_open: float


def session_matrix(df: pd.DataFrame, bars_per_day: int = 96, before: Optional[pd.Timestamp] = None) -> SessionMatrix:
    """Full UTC days only, shape (sessions, bars). Days on/after `before` are excluded (no look-ahead)."""
    ts = pd.to_datetime(df["timestamp"], utc=True)
    day = ts.dt.normalize()
    if before is not None:
        keep = day < pd.Timestamp(before).tz_convert("UTC").normalize()
        df, day = df[keep], day[keep]
    cols = {k: [] for k in "OHLC"}
    dates = []
    for d, g in df.groupby(day, sort=True):
        if len(g) != bars_per_day:
            continue
        for k, c in zip("OHLC", ("open", "high", "low", "close")):
            cols[k].append(g[c].astype(float).to_numpy())
        dates.append(str(d.date()))
    arr = {k: np.array(v).reshape(len(dates), bars_per_day) for k, v in cols.items()}
    return SessionMatrix(arr["O"], arr["H"], arr["L"], arr["C"], tuple(dates))


def first_touch(highs: np.ndarray, lows: np.ndarray, stop: float, target: float) -> Tuple[np.ndarray, np.ndarray]:
    """Per path: outcome code (OPEN/TARGET/STOP) and the bar index of the first touch. Ties -> STOP."""
    highs, lows = np.atleast_2d(highs), np.atleast_2d(lows)
    n = highs.shape[1]
    s_hit, t_hit = lows <= stop, highs >= target
    s_idx = np.where(s_hit.any(1), s_hit.argmax(1), n)
    t_idx = np.where(t_hit.any(1), t_hit.argmax(1), n)
    out = np.where(s_idx <= t_idx, STOP, TARGET)
    out = np.where((s_idx == n) & (t_idx == n), OPEN, out)
    return out, np.minimum(s_idx, t_idx)


def run_time_machine(hist: SessionMatrix, k_fill: int, entry: float, stop: float, target: float,
                     n_paths: int = 1000, seed: int = 19, method: str = "session_block") -> TMResult:
    """Simulate bars k_fill..end of the session from `entry` (the last known close, bar k_fill-1)."""
    if hist.n_sessions == 0 or not (1 <= k_fill < hist.C.shape[1]):
        raise ValueError("need at least one historical session and 1 <= k_fill < bars_per_day")
    rng = np.random.default_rng(seed)
    t_steps = hist.C.shape[1] - k_fill
    if method == "session_block":
        rows = rng.integers(0, hist.n_sessions, n_paths)
        base = hist.C[rows, k_fill - 1][:, None]
        highs = entry * hist.H[rows, k_fill:] / base
        lows = entry * hist.L[rows, k_fill:] / base
    elif method == "candle_iid":
        cols = k_fill + np.arange(t_steps)
        idx = rng.integers(0, hist.n_sessions, (n_paths, t_steps))
        prev = hist.C[idx, cols - 1]
        close_ratio = hist.C[idx, cols] / prev
        path_close = entry * np.cumprod(close_ratio, axis=1)
        path_prev = np.concatenate([np.full((n_paths, 1), entry), path_close[:, :-1]], axis=1)
        highs = path_prev * hist.H[idx, cols] / prev
        lows = path_prev * hist.L[idx, cols] / prev
    else:
        raise ValueError(f"unknown method {method!r}")
    out, _ = first_touch(highs, lows, stop, target)
    return TMResult(method, n_paths, seed, hist.n_sessions,
                    float((out == TARGET).mean()), float((out == STOP).mean()), float((out == OPEN).mean()))
