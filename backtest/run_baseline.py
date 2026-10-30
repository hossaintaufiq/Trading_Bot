"""
Automated Multi-Timeframe Baseline Backtest Runner for Stage 2.
Evaluates Original vs Fixed logic across 12 months, 7 symbols, 3 timeframes (5m, 15m, 1h),
with 0.10% fee and 0.075% BNB-discount cases.
"""

import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List

from backtest.data_loader import BinanceDataLoader
from backtest.simulator import BacktestEngine
from backtest.metrics import compute_performance_metrics

logger = logging.getLogger("backtest_runner")


def load_dataset(loader: BinanceDataLoader, symbols: List[str], timeframe: str) -> Dict[str, pd.DataFrame]:
    """Load cached dataset for symbols on a given timeframe."""
    data = {}
    for sym in symbols:
        safe_sym = sym.replace("/", "_")
        path = os.path.join(loader.cache_dir, f"{safe_sym}_{timeframe}.csv")
        if os.path.exists(path):
            df = pd.read_csv(path)
            # Add precomputed dt column for fast timestamp queries
            df["dt"] = pd.to_datetime(df["time"], unit="s", utc=True)
            data[sym] = df
        else:
            logger.warning(f"File not found: {path}")
    return data


def run_single_simulation(
    data: Dict[str, pd.DataFrame],
    timeframe: str,
    fee_pct: float,
    slippage_pct: float,
    use_original: bool,
    run_label: str
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Execute a single multi-asset backtest run and return (metrics, trades)."""
    engine = BacktestEngine(
        strategy_name="neptune_fleet",
        config={"strategies": {}},
        initial_capital=10000.0,
        trade_amount=100.0,
        fee_pct=fee_pct,
        slippage_pct=slippage_pct,
        max_open_positions=5,
        max_correlated_positions=2,
        use_original_logic=use_original
    )

    trades = engine.run_multi_asset(data)
    metrics = compute_performance_metrics(trades, engine.equity_curve, timeframe=timeframe)
    metrics["run_label"] = run_label
    metrics["timeframe"] = timeframe
    metrics["fee_pct"] = fee_pct
    metrics["slippage_pct"] = slippage_pct
    metrics["logic_version"] = "ORIGINAL" if use_original else "STAGE_1_FIXED"

    # Add quarterly breakdown if trades exist
    if trades:
        df_tr = pd.DataFrame(trades)
        df_tr["dt"] = pd.to_datetime(df_tr["entry_time"], unit="s", utc=True)
        quarterly = {}
        for q, grp in df_tr.groupby(df_tr["dt"].dt.to_period("Q")):
            w = grp[grp["realized_pnl"] > 0]
            quarterly[str(q)] = {
                "trades": len(grp),
                "wins": len(w),
                "win_rate_pct": round((len(w) / len(grp)) * 100.0, 1),
                "net_pnl": round(float(grp["realized_pnl"].sum()), 2),
                "fees": round(float(grp["total_fees"].sum()), 2)
            }
        metrics["breakdown_by_quarter"] = quarterly

    return metrics, trades


def run_all_baseline_experiments():
    loader = BinanceDataLoader(cache_dir="backtest/data/12m")
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT", "SUI/USDT"]
    os.makedirs("results", exist_ok=True)

    timeframes = ["1h", "15m"]
    # Add 5m if available
    if os.path.exists(os.path.join(loader.cache_dir, "BTC_USDT_5m.csv")):
        timeframes.append("5m")

    all_summaries = []

    for tf in timeframes:
        print(f"\n>>> Running Backtest Experiments for Timeframe: {tf} ...")
        data = load_dataset(loader, symbols, tf)
        if not data:
            print(f"Skipping {tf}: Data not found.")
            continue

        # 1. Original Logic, Standard Fee (0.10%)
        m_orig_std, tr_orig_std = run_single_simulation(
            data, tf, fee_pct=0.10, slippage_pct=0.05, use_original=True,
            run_label=f"ORIGINAL_{tf}_Fee0.10"
        )
        if tr_orig_std:
            pd.DataFrame(tr_orig_std).to_csv(f"results/trades_ORIGINAL_{tf}_Fee0.10.csv", index=False)
        all_summaries.append(m_orig_std)

        # 2. Original Logic, BNB Discount Fee (0.075%)
        m_orig_bnb, tr_orig_bnb = run_single_simulation(
            data, tf, fee_pct=0.075, slippage_pct=0.05, use_original=True,
            run_label=f"ORIGINAL_{tf}_Fee0.075_BNB"
        )
        if tr_orig_bnb:
            pd.DataFrame(tr_orig_bnb).to_csv(f"results/trades_ORIGINAL_{tf}_Fee0.075_BNB.csv", index=False)
        all_summaries.append(m_orig_bnb)

        # 3. Fixed Stage 1 Logic, Standard Fee (0.10%)
        m_fix_std, tr_fix_std = run_single_simulation(
            data, tf, fee_pct=0.10, slippage_pct=0.05, use_original=False,
            run_label=f"FIXED_{tf}_Fee0.10"
        )
        if tr_fix_std:
            pd.DataFrame(tr_fix_std).to_csv(f"results/trades_FIXED_{tf}_Fee0.10.csv", index=False)
        all_summaries.append(m_fix_std)

        # 4. Fixed Stage 1 Logic, BNB Discount Fee (0.075%)
        m_fix_bnb, tr_fix_bnb = run_single_simulation(
            data, tf, fee_pct=0.075, slippage_pct=0.05, use_original=False,
            run_label=f"FIXED_{tf}_Fee0.075_BNB"
        )
        if tr_fix_bnb:
            pd.DataFrame(tr_fix_bnb).to_csv(f"results/trades_FIXED_{tf}_Fee0.075_BNB.csv", index=False)
        all_summaries.append(m_fix_bnb)

        print(f"[{tf}] Completed. Original PnL: ${m_orig_std['net_pnl_usd']:.2f} (WR: {m_orig_std['win_rate_pct']}%), Fixed PnL: ${m_fix_std['net_pnl_usd']:.2f} (WR: {m_fix_std['win_rate_pct']}%)")

    # Save full JSON summary
    with open("results/baseline_summary.json", "w") as f:
        json.dump(all_summaries, f, indent=2)

    # Save Comparison CSV
    comp_rows = []
    for s in all_summaries:
        comp_rows.append({
            "Run Label": s.get("run_label"),
            "Timeframe": s.get("timeframe"),
            "Logic": s.get("logic_version"),
            "Fee (%)": s.get("fee_pct"),
            "Total Trades": s.get("total_trades"),
            "Win Rate (%)": s.get("win_rate_pct"),
            "Payoff Ratio": s.get("payoff_ratio"),
            "Profit Factor": s.get("profit_factor"),
            "Expectancy / Trade ($)": s.get("expectancy_per_trade_usd"),
            "Net PnL ($)": s.get("net_pnl_usd"),
            "Fees Paid ($)": s.get("fees_paid_usd"),
            "Max Drawdown (%)": s.get("max_drawdown_pct"),
            "Sharpe Ratio": s.get("sharpe_ratio"),
            "Avg Hold (min)": s.get("avg_hold_minutes")
        })

    df_comp = pd.DataFrame(comp_rows)
    df_comp.to_csv("results/baseline_comparison.csv", index=False)

    print("\n" + "="*100)
    print("STAGE 2 BASELINE RESULTS SUMMARY (12 MONTHS, 7 SYMBOLS)")
    print("="*100)
    print(df_comp.to_string(index=False))
    print("="*100 + "\n")

    return df_comp


if __name__ == "__main__":
    run_all_baseline_experiments()
