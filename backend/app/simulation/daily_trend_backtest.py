"""
Daily trend paper backtest (ADR-037). Decimal accounting (A-01), UTC (A-02).

Execution model (A-09, A-10): a state change decided at the close of bar t is filled at the OPEN of bar t+1.
Buys fill at open*(1+slippage+half_spread); sells at open*(1-slippage-half_spread); fee on notional both sides.
Each symbol is an independent sleeve with equal starting capital (long-only, no leverage, cash earns 0).
"""
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from app.strategies.daily_trend import DailyTrendConfig, compute_positions

FEE = Decimal("0.001")
SLIP = Decimal("0.0005")
HALF_SPREAD = Decimal("0.0001")
DATA_DIR = Path(__file__).resolve().parents[3] / "storage" / "research" / "daily"


@dataclass
class Trade:
    symbol: str
    entry_time: str
    exit_time: str
    entry_price: Decimal
    exit_price: Decimal
    net_pnl: Decimal
    fees: Decimal


@dataclass
class SleeveResult:
    equity: Dict[str, Decimal] = field(default_factory=dict)   # date -> sleeve equity at close
    trades: List[Trade] = field(default_factory=list)


def load_daily(symbol: str) -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / f"{symbol}.parquet").sort_values("timestamp").reset_index(drop=True)


def run_sleeve(symbol: str, df: pd.DataFrame, capital: Decimal, cfg: DailyTrendConfig) -> SleeveResult:
    closes = [float(x) for x in df["close"]]
    desired = compute_positions(closes, cfg.entry_lookback, cfg.exit_lookback)
    cash, qty, entry_cost, entry_px, entry_t, fees_in = capital, Decimal(0), Decimal(0), Decimal(0), "", Decimal(0)
    res = SleeveResult()
    for i in range(len(df)):
        ts = df["timestamp"].iloc[i].strftime("%Y-%m-%d")
        open_i = Decimal(str(df["open"].iloc[i]))
        prev = desired[i - 1] if i > 0 else 0        # state known at previous close -> acted on at this open
        if prev == 1 and qty == 0:
            px = open_i * (1 + SLIP + HALF_SPREAD)
            q = cash / (px * (1 + FEE))
            fee = q * px * FEE
            cash -= q * px + fee
            qty, entry_px, entry_t, fees_in, entry_cost = q, px, ts, fee, q * px + fee
        elif prev == 0 and qty > 0:
            px = open_i * (1 - SLIP - HALF_SPREAD)
            fee = qty * px * FEE
            proceeds = qty * px - fee
            cash += proceeds
            res.trades.append(Trade(symbol, entry_t, ts, entry_px, px, proceeds - entry_cost, fees_in + fee))
            qty = Decimal(0)
        res.equity[ts] = cash + qty * Decimal(str(df["close"].iloc[i]))
    return res


def run_portfolio(symbols: List[str], start: str, end: str, initial: Decimal = Decimal("1000"),
                  cfg: Optional[DailyTrendConfig] = None, warmup_days: int = 120) -> dict:
    """Run sleeves with warm-up history before `start`; metrics are reported on [start, end] only."""
    cfg = cfg or DailyTrendConfig()
    per = initial / len(symbols)
    sleeves = {}
    for s in symbols:
        df = load_daily(s)
        t0 = pd.Timestamp(start, tz="UTC") - pd.Timedelta(days=warmup_days)
        df = df[(df["timestamp"] >= t0) & (df["timestamp"] <= pd.Timestamp(end, tz="UTC"))].reset_index(drop=True)
        sleeves[s] = run_sleeve(s, df, per, cfg)
    dates = sorted(set.intersection(*[set(r.equity) for r in sleeves.values()]))
    dates = [d for d in dates if start <= d <= end]
    # rebase: capital at the start date is the equity then (sleeves may be mid-trade after warm-up)
    base = sum(r.equity[dates[0]] for r in sleeves.values())
    curve = [(d, sum(r.equity[d] for r in sleeves.values()) / base * initial) for d in dates]
    peak, mdd = initial, Decimal(0)
    for _, e in curve:
        peak = max(peak, e)
        mdd = max(mdd, (peak - e) / peak)
    trades = [t for r in sleeves.values() for t in r.trades if start <= t.exit_time <= end]
    final = curve[-1][1]
    return {
        "start": start, "end": end, "initial": initial, "final": final,
        "net_return_pct": (final / initial - 1) * 100, "max_drawdown_pct": mdd * 100,
        "trades": trades, "equity_curve": curve,
        "total_fees": sum((t.fees for t in trades), Decimal(0)),
    }


def buy_and_hold(symbols: List[str], start: str, end: str, initial: Decimal = Decimal("1000")) -> Decimal:
    per, total = initial / len(symbols), Decimal(0)
    for s in symbols:
        df = load_daily(s)
        df = df[(df["timestamp"] >= pd.Timestamp(start, tz="UTC")) & (df["timestamp"] <= pd.Timestamp(end, tz="UTC"))]
        px_in = Decimal(str(df["open"].iloc[0])) * (1 + SLIP + HALF_SPREAD)
        q = per / (px_in * (1 + FEE))
        px_out = Decimal(str(df["close"].iloc[-1])) * (1 - SLIP - HALF_SPREAD)
        total += q * px_out * (1 - FEE)
    return (total / initial - 1) * 100


if __name__ == "__main__":
    syms = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    for label, a, b in [("TRAIN 2018-2023", "2018-01-01", "2023-12-31"), ("TEST 2024-2026", "2024-01-01", "2026-11-12")]:
        r = run_portfolio(syms, a, b)
        wins = sum(1 for t in r["trades"] if t.net_pnl > 0)
        print(f"{label}: final ${r['final']:.2f}  net {r['net_return_pct']:+.1f}%  maxDD {r['max_drawdown_pct']:.1f}%  "
              f"trades {len(r['trades'])} wins {wins}  fees ${r['total_fees']:.2f}  B&H {buy_and_hold(syms, a, b):+.1f}%")
