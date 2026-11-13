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
class Event:
    """One paper fill (A-10: price includes slippage + half spread; fee recorded)."""
    date: str
    symbol: str
    side: str            # BUY | SELL
    price: Decimal
    qty: Decimal
    fee: Decimal
    net_pnl: Optional[Decimal] = None   # SELL only: profit after all costs


@dataclass
class SleeveResult:
    equity: Dict[str, Decimal] = field(default_factory=dict)   # date -> sleeve equity at close
    cash: Dict[str, Decimal] = field(default_factory=dict)     # date -> sleeve cash at close
    trades: List[Trade] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
    qty: Decimal = Decimal(0)                                  # coins held at the end
    entry_price: Decimal = Decimal(0)


def load_daily(symbol: str) -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / f"{symbol}.parquet").sort_values("timestamp").reset_index(drop=True)


def run_sleeve(symbol: str, df: pd.DataFrame, capital: Decimal, cfg: DailyTrendConfig, active_from: int = 0) -> SleeveResult:
    """`active_from`: bar index before which the account is flat; a trend already running then is NOT entered."""
    closes = [float(x) for x in df["close"]]
    desired = compute_positions(closes, cfg.entry_lookback, cfg.exit_lookback)
    if active_from > 0 and desired[active_from - 1] == 1:
        # a trend was already running when the account opened: skip it, wait for the next fresh buy signal
        j = active_from
        while j < len(desired) and desired[j] == 1:
            j += 1
        for k in range(j):
            desired[k] = 0
    elif active_from > 0:
        for k in range(active_from):
            desired[k] = 0
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
            res.events.append(Event(ts, symbol, "BUY", px, q, fee))
        elif prev == 0 and qty > 0:
            px = open_i * (1 - SLIP - HALF_SPREAD)
            fee = qty * px * FEE
            proceeds = qty * px - fee
            cash += proceeds
            res.trades.append(Trade(symbol, entry_t, ts, entry_px, px, proceeds - entry_cost, fees_in + fee))
            res.events.append(Event(ts, symbol, "SELL", px, qty, fee, proceeds - entry_cost))
            qty = Decimal(0)
        res.equity[ts] = cash + qty * Decimal(str(df["close"].iloc[i]))
        res.cash[ts] = cash
    res.qty, res.entry_price = qty, entry_px
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


def run_account(symbols: List[str], start: str, initial: Decimal = Decimal("1000"),
                cfg: Optional[DailyTrendConfig] = None) -> dict:
    """Paper account opened flat on `start` with `initial` USDT split equally across symbols.
    Returns every fill with the account's cash / coins / total value right after it."""
    cfg = cfg or DailyTrendConfig()
    per = initial / len(symbols)
    sleeves, frames = {}, {}
    for s in symbols:
        df = load_daily(s)
        idx = int((df["timestamp"] < pd.Timestamp(start, tz="UTC")).sum())      # first bar of the account
        frames[s] = df
        sleeves[s] = run_sleeve(s, df.iloc[max(0, idx - 120):].reset_index(drop=True), per, cfg,
                                active_from=min(idx, 120))
    dates = sorted(d for d in set.intersection(*[set(r.equity) for r in sleeves.values()]) if d >= start)
    total = {d: sum(r.equity[d] for r in sleeves.values()) for d in dates}
    cash = {d: sum(r.cash[d] for r in sleeves.values()) for d in dates}
    events = sorted((e for r in sleeves.values() for e in r.events if e.date >= start), key=lambda e: (e.date, e.symbol))
    close_px = {s: {d.strftime("%Y-%m-%d"): Decimal(str(c)) for d, c in zip(f["timestamp"], f["close"])} for s, f in frames.items()}
    ledger, prev, cash_run, held = [], initial, initial, {s: Decimal(0) for s in symbols}
    for e in events:                      # replay fill by fill so same-day trades each show their own effect
        amount = e.price * e.qty
        if e.side == "BUY":
            cash_run -= amount + e.fee
            held[e.symbol] += e.qty
        else:
            cash_run += amount - e.fee
            held[e.symbol] -= e.qty
        coins = sum((held[s] * close_px[s][e.date] for s in symbols), Decimal(0))
        t = cash_run + coins
        ledger.append({
            "date": e.date, "symbol": e.symbol, "side": e.side, "price": float(e.price), "qty": float(e.qty),
            "amount": float(amount), "fee": float(e.fee),
            "profit": float(e.net_pnl) if e.net_pnl is not None else None,
            "cash_after": float(cash_run), "coins_after": float(coins), "total_after": float(t),
            "total_change": float(t - prev),
        })
        prev = t
    holdings = []
    for s, r in sleeves.items():
        if r.qty > 0:
            last = Decimal(str(frames[s]["close"].iloc[-1]))
            holdings.append({"symbol": s, "qty": float(r.qty), "bought_at": float(r.entry_price),
                             "value": float(r.qty * last), "unrealized_pct": float((last / r.entry_price - 1) * 100)})
    now = total[dates[-1]]
    return {
        "start": start, "initial": float(initial), "total_now": float(now), "cash_now": float(cash[dates[-1]]),
        "coins_now": float(now - cash[dates[-1]]), "return_pct": float((now / initial - 1) * 100),
        "fees_paid": float(sum(e.fee for e in events)), "holdings": holdings, "ledger": ledger,
        "curve": [{"date": d, "total": float(total[d])} for d in dates[:: max(1, len(dates) // 500)]] + [{"date": dates[-1], "total": float(now)}],
    }
