"""
Monte Carlo Random-Entry Baseline Benchmark across 100 random seeds.
Evaluates random entries across the same 7 symbols over the same 12-month period,
using the exact same stop loss (1.5x ATR), take profit (2.5R target),
taker fee (0.10%), slippage (0.05%), and conservative intrabar tie-break.
"""

import os
import json
import time
import numpy as np
import pandas as pd
from typing import Dict, Any, List

from backtest.data_loader import BinanceDataLoader
from indicators import enrich_dataframe


def run_random_benchmark(num_seeds: int = 100, timeframe: str = "1h") -> Dict[str, Any]:
    loader = BinanceDataLoader(cache_dir="backtest/data/12m")
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT", "SUI/USDT"]

    print("Loading datasets for random benchmark...", flush=True)
    sym_arrays = {}
    all_times = set()
    for sym in symbols:
        safe_sym = sym.replace("/", "_")
        p = os.path.join(loader.cache_dir, f"{safe_sym}_{timeframe}.csv")
        if not os.path.exists(p):
            continue
        df = pd.read_csv(p)
        df["dt"] = pd.to_datetime(df["time"], unit="s", utc=True)
        edf = enrich_dataframe(df, {})
        all_times.update(edf["time"].tolist())
        sym_arrays[sym] = {
            "time": edf["time"].to_numpy(),
            "open": edf["open"].to_numpy(dtype=float),
            "high": edf["high"].to_numpy(dtype=float),
            "low": edf["low"].to_numpy(dtype=float),
            "close": edf["close"].to_numpy(dtype=float),
            "atr": edf["atr"].to_numpy(dtype=float) if "atr" in edf else (edf["close"].to_numpy(dtype=float) * 0.01)
        }

    sorted_times = sorted(list(all_times))
    time_to_idx = {sym: {t: i for i, t in enumerate(arr["time"])} for sym, arr in sym_arrays.items()}

    fee_pct = 0.10
    slippage_pct = 0.05
    trade_amount = 100.0
    max_open_positions = 3
    max_correlated = 2
    rr_ratio = 2.5
    atr_mult = 1.5

    seed_results = []
    print(f"Running {num_seeds} random simulation seeds...", flush=True)
    t0 = time.time()

    for seed in range(1, num_seeds + 1):
        rng = np.random.default_rng(seed)
        positions = {}
        closed_trades = []
        pending_buys = []

        # Probability of generating a random entry signal on a given bar for a coin: ~0.015 (average ~1000 trades/year)
        entry_prob = 0.012

        for t in sorted_times:
            # 1. Fill pending orders
            rem_buys = []
            for b_sym in pending_buys:
                if b_sym in sym_arrays and t in time_to_idx[b_sym]:
                    idx = time_to_idx[b_sym][t]
                    open_p = sym_arrays[b_sym]["open"][idx]
                    exec_p = open_p * (1.0 + slippage_pct / 100.0)
                    fee = trade_amount * (fee_pct / 100.0)
                    qty = (trade_amount - fee) / exec_p
                    atr = sym_arrays[b_sym]["atr"][idx]

                    sl = exec_p - (atr_mult * atr)
                    risk = max(0.0001, exec_p - sl)
                    tp = exec_p + (rr_ratio * risk)

                    positions[b_sym] = {
                        "entry_price": exec_p,
                        "quantity": qty,
                        "cost": trade_amount,
                        "buy_fee": fee,
                        "sl": sl,
                        "tp": tp,
                        "bars_held": 0
                    }
                else:
                    rem_buys.append(b_sym)
            pending_buys = rem_buys

            # 2. Check exits
            to_close = []
            for sym, pos in list(positions.items()):
                if sym not in sym_arrays or t not in time_to_idx[sym]:
                    continue
                idx = time_to_idx[sym][t]
                arr = sym_arrays[sym]
                high_p = arr["high"][idx]
                low_p = arr["low"][idx]
                close_p = arr["close"][idx]
                pos["bars_held"] += 1

                # Conservative tie-breaker
                if low_p <= pos["sl"] and high_p >= pos["tp"]:
                    to_close.append((sym, pos["sl"]))
                elif low_p <= pos["sl"]:
                    to_close.append((sym, pos["sl"]))
                elif high_p >= pos["tp"]:
                    to_close.append((sym, pos["tp"]))
                elif pos["bars_held"] >= 50:
                    to_close.append((sym, close_p))

            for sym, exit_p in to_close:
                pos = positions.pop(sym)
                exec_exit = exit_p * (1.0 - slippage_pct / 100.0)
                gross = pos["quantity"] * exec_exit
                sell_fee = gross * (fee_pct / 100.0)
                net = gross - sell_fee
                pnl = net - pos["cost"]
                closed_trades.append({
                    "pnl": pnl,
                    "fees": pos["buy_fee"] + sell_fee,
                    "gross_pnl": (pos["quantity"] * exit_p) - pos["cost"]
                })

            # 3. Random entries if slots available
            if len(positions) + len(pending_buys) < max_open_positions:
                for sym in symbols:
                    if sym in positions or sym in pending_buys:
                        continue
                    if sym != "BTC/USDT":
                        alts = len([s for s in positions if s != "BTC/USDT"]) + len([s for s in pending_buys if s != "BTC/USDT"])
                        if alts >= max_correlated:
                            continue
                    if rng.random() < entry_prob:
                        pending_buys.append(sym)
                        if len(positions) + len(pending_buys) >= max_open_positions:
                            break

        # Compute seed metrics
        if closed_trades:
            df_s = pd.DataFrame(closed_trades)
            n = len(df_s)
            w = df_s[df_s["pnl"] > 0]
            l = df_s[df_s["pnl"] <= 0]
            net_pnl = float(df_s["pnl"].sum())
            gross_pnl = float(df_s["gross_pnl"].sum())
            fees = float(df_s["fees"].sum())
            wr = (len(w) / n) * 100.0
            avg_w = float(w["pnl"].mean()) if len(w) > 0 else 0.0
            avg_l = float(abs(l["pnl"].mean())) if len(l) > 0 else 0.0
            payoff = (avg_w / avg_l) if avg_l > 0 else 0.0
            pf = float(w["pnl"].sum()) / float(abs(l["pnl"].sum())) if len(l) > 0 and abs(l["pnl"].sum()) > 0 else 0.0
            exp = net_pnl / n

            seed_results.append({
                "seed": seed,
                "trades": n,
                "win_rate_pct": wr,
                "payoff_ratio": payoff,
                "profit_factor": pf,
                "gross_pnl": gross_pnl,
                "net_pnl": net_pnl,
                "fees_paid": fees,
                "expectancy": exp
            })

    elapsed = time.time() - t0
    print(f"Completed 100 random seeds in {elapsed:.1f}s", flush=True)

    df_seeds = pd.DataFrame(seed_results)
    summary = {
        "num_seeds": len(df_seeds),
        "avg_trades": round(float(df_seeds["trades"].mean()), 1),
        "trades_spread": f"[{int(df_seeds['trades'].min())}, {int(df_seeds['trades'].max())}]",
        "avg_win_rate_pct": round(float(df_seeds["win_rate_pct"].mean()), 2),
        "win_rate_spread": f"[{df_seeds['win_rate_pct'].min():.2f}%, {df_seeds['win_rate_pct'].max():.2f}%] (std: {df_seeds['win_rate_pct'].std():.2f}%)",
        "avg_payoff_ratio": round(float(df_seeds["payoff_ratio"].mean()), 2),
        "payoff_spread": f"[{df_seeds['payoff_ratio'].min():.2f}, {df_seeds['payoff_ratio'].max():.2f}]",
        "avg_profit_factor": round(float(df_seeds["profit_factor"].mean()), 2),
        "profit_factor_spread": f"[{df_seeds['profit_factor'].min():.2f}, {df_seeds['profit_factor'].max():.2f}]",
        "avg_gross_pnl": round(float(df_seeds["gross_pnl"].mean()), 2),
        "avg_fees_paid": round(float(df_seeds["fees_paid"].mean()), 2),
        "avg_net_pnl": round(float(df_seeds["net_pnl"].mean()), 2),
        "net_pnl_spread": f"[${df_seeds['net_pnl'].min():.2f}, ${df_seeds['net_pnl'].max():.2f}] (std: ${df_seeds['net_pnl'].std():.2f})",
        "avg_expectancy_usd": round(float(df_seeds["expectancy"].mean()), 4),
        "expectancy_spread": f"[${df_seeds['expectancy'].min():.4f}, ${df_seeds['expectancy'].max():.4f}]"
    }

    df_seeds.to_csv("results/random_baseline_100_seeds.csv", index=False)
    with open("results/random_baseline_summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return summary


if __name__ == "__main__":
    res = run_random_benchmark(100)
    print("\n" + "="*80)
    print("100-SEED RANDOM ENTRY BASELINE BENCHMARK SUMMARY")
    print("="*80)
    for k, v in res.items():
        print(f"  {k}: {v}")
    print("="*80)
