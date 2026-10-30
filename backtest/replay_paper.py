"""
Replay validation script: Replays the ORIGINAL bot logic over the exact 14.4-hour
period of the 75 baseline paper trades and compares against paper_state.json.
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any

from backtest.data_loader import BinanceDataLoader
from backtest.simulator import BacktestEngine
from backtest.metrics import compute_performance_metrics


def run_paper_replay_validation():
    # 1. Load actual paper trades from paper_state.json
    with open("paper_state.json", "r") as f:
        paper_state = json.load(f)

    all_trades = paper_state.get("trades_history", [])
    paper_sells = [t for t in all_trades if t.get("side") == "SELL"]
    paper_buys = [t for t in all_trades if t.get("side") == "BUY"]

    paper_wins = [t for t in paper_sells if t.get("realized_pnl", 0) > 0]
    paper_losses = [t for t in paper_sells if t.get("realized_pnl", 0) <= 0]

    paper_n = len(paper_sells)
    paper_wr = (len(paper_wins) / paper_n) * 100.0 if paper_n > 0 else 0.0
    paper_avg_win = float(np.mean([t["realized_pnl"] for t in paper_wins])) if paper_wins else 0.0
    paper_avg_loss = float(np.mean([abs(t["realized_pnl"]) for t in paper_losses])) if paper_losses else 0.0
    paper_payoff = (paper_avg_win / paper_avg_loss) if paper_avg_loss > 0 else 0.0
    paper_tot_fees = float(sum(t.get("fee_usdt", 0) for t in paper_buys) + sum(t.get("fee_usdt", 0) for t in paper_sells))
    paper_net_pnl = float(sum(t.get("realized_pnl", 0) for t in paper_sells))

    # 2. Load 1m historical klines for the replay period
    loader = BinanceDataLoader(cache_dir="backtest/data/paper_replay")
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT", "SUI/USDT"]
    start_ms = 1793300000000
    end_ms = 1793360000000

    data_map = {}
    for sym in symbols:
        df, rep = loader.get_or_download_data(sym, "1m", start_ms, end_ms)
        data_map[sym] = df

    # 3. Replay with ORIGINAL logic (1.5% stop, 2.5% TP, 5 max positions, $100 per trade)
    sim_original = BacktestEngine(
        strategy_name="neptune_fleet",
        config={"strategies": {}},
        initial_capital=10000.0,
        trade_amount=100.0,
        fee_pct=0.10,
        slippage_pct=0.05,
        max_open_positions=5,
        use_original_logic=True
    )
    trades_sim_orig = sim_original.run_multi_asset(data_map)
    metrics_orig = compute_performance_metrics(trades_sim_orig, sim_original.equity_curve, timeframe="1m")

    # 4. Replay with FIXED Stage 1 logic
    sim_fixed = BacktestEngine(
        strategy_name="neptune_fleet",
        config={"strategies": {}},
        initial_capital=10000.0,
        trade_amount=100.0,
        fee_pct=0.10,
        slippage_pct=0.05,
        max_open_positions=5,
        max_correlated_positions=2,
        use_original_logic=False
    )
    trades_sim_fixed = sim_fixed.run_multi_asset(data_map)
    metrics_fixed = compute_performance_metrics(trades_sim_fixed, sim_fixed.equity_curve, timeframe="1m")

    # 5. Save results to results/
    os.makedirs("results", exist_ok=True)
    if trades_sim_orig:
        pd.DataFrame(trades_sim_orig).to_csv("results/paper_replay_sim_original_trades.csv", index=False)
    if trades_sim_fixed:
        pd.DataFrame(trades_sim_fixed).to_csv("results/paper_replay_sim_fixed_trades.csv", index=False)

    comparison = {
        "metric": [
            "Total Closed Trades",
            "Win Rate (%)",
            "Average Win ($)",
            "Average Loss ($)",
            "Payoff Ratio",
            "Total Fees Paid ($)",
            "Net Realized PnL ($)",
            "Profit Factor",
            "Expectancy / Trade ($)"
        ],
        "paper_actual": [
            paper_n,
            round(paper_wr, 1),
            round(paper_avg_win, 2),
            round(paper_avg_loss, 2),
            round(paper_payoff, 2),
            round(paper_tot_fees, 2),
            round(paper_net_pnl, 2),
            round(sum(t['realized_pnl'] for t in paper_wins) / max(0.01, sum(abs(t['realized_pnl']) for t in paper_losses)), 2),
            round(paper_net_pnl / max(1, paper_n), 3)
        ],
        "backtest_replay_original": [
            metrics_orig["total_trades"],
            metrics_orig["win_rate_pct"],
            metrics_orig["avg_win_usd"],
            metrics_orig["avg_loss_usd"],
            metrics_orig["payoff_ratio"],
            metrics_orig["fees_paid_usd"],
            metrics_orig["net_pnl_usd"],
            metrics_orig["profit_factor"],
            metrics_orig["expectancy_per_trade_usd"]
        ],
        "backtest_replay_fixed": [
            metrics_fixed["total_trades"],
            metrics_fixed["win_rate_pct"],
            metrics_fixed["avg_win_usd"],
            metrics_fixed["avg_loss_usd"],
            metrics_fixed["payoff_ratio"],
            metrics_fixed["fees_paid_usd"],
            metrics_fixed["net_pnl_usd"],
            metrics_fixed["profit_factor"],
            metrics_fixed["expectancy_per_trade_usd"]
        ]
    }

    df_comp = pd.DataFrame(comparison)
    df_comp.to_csv("results/paper_replay_comparison.csv", index=False)

    with open("results/paper_replay_summary.json", "w") as f:
        json.dump({
            "paper_actual": {
                "trades": paper_n,
                "win_rate": paper_wr,
                "avg_win": paper_avg_win,
                "avg_loss": paper_avg_loss,
                "payoff": paper_payoff,
                "fees": paper_tot_fees,
                "net_pnl": paper_net_pnl
            },
            "backtest_original": metrics_orig,
            "backtest_fixed": metrics_fixed
        }, f, indent=2)

    print("\n" + "="*80)
    print("BACKTESTER VALIDATION: REPLAY AGAINST 75 PAPER TRADES")
    print("="*80)
    print(df_comp.to_string(index=False))
    print("="*80 + "\n")

    return df_comp, metrics_orig, metrics_fixed


if __name__ == "__main__":
    run_paper_replay_validation()

