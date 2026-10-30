"""
High-Speed Walk-Forward Backtester for Decision Engine.
Runs the upgraded 'Best Coin & Best Pattern' Decision Engine across 12 months,
with chronological 50% Train / 25% Validation / 25% Out-of-Sample Test splits.
Enforces realistic execution: closed-candle signals, next-open fill, taker fee 0.10%,
slippage 0.05%, conservative intrabar stop/target execution, break-even ratchet, and ATR runner trail.
"""

import os
import sys
import time
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backtest.data_loader import BinanceDataLoader
from backtest.decision_engine import DecisionEngine
from backtest.metrics import compute_performance_metrics
from indicators import enrich_dataframe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("decision_backtest")


def run_decision_backtest(
    timeframe: str = "1h",
    fee_pct: float = 0.10,
    slippage_pct: float = 0.05,
    max_open_positions: int = 3,
    max_correlated_positions: int = 2,
    trade_amount: float = 100.0,
    rr_ratio: float = 2.5,
    min_target_pct: float = 1.20
) -> Dict[str, Any]:
    loader = BinanceDataLoader(cache_dir="backtest/data/12m")
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT", "DOGE/USDT", "SUI/USDT"]

    # 1. Load & enrich data
    enriched = {}
    sym_arrays = {}
    all_timestamps = set()
    decision_engine = DecisionEngine(config={
        "min_target_pct": min_target_pct,
        "target_rr_ratio": rr_ratio,
        "atr_stop_multiplier": 1.5,
        "atr_trail_multiplier": 1.5
    })

    print(f"Loading and enriching {len(symbols)} symbols on {timeframe}...", flush=True)
    for sym in symbols:
        safe_sym = sym.replace("/", "_")
        p = os.path.join(loader.cache_dir, f"{safe_sym}_{timeframe}.csv")
        if not os.path.exists(p):
            print(f"Missing {p}")
            continue
        df = pd.read_csv(p)
        df["dt"] = pd.to_datetime(df["time"], unit="s", utc=True)
        edf = enrich_dataframe(df, {})
        enriched[sym] = edf
        all_timestamps.update(edf["time"].tolist())
        sym_arrays[sym] = {
            "open": edf["open"].to_numpy(dtype=float),
            "high": edf["high"].to_numpy(dtype=float),
            "low": edf["low"].to_numpy(dtype=float),
            "close": edf["close"].to_numpy(dtype=float),
            "atr": edf["atr"].to_numpy(dtype=float) if "atr" in edf else (edf["close"].to_numpy(dtype=float) * 0.01)
        }

    sorted_times = sorted(list(all_timestamps))
    total_bars = len(sorted_times)
    time_to_idx = {sym: {t: i for i, t in enumerate(df["time"])} for sym, df in enriched.items()}

    # Chronological Splits: Train 50%, Val 25%, Test 25%
    train_end_idx = int(total_bars * 0.50)
    val_end_idx = int(total_bars * 0.75)

    print(f"Total chronological bars: {total_bars}")
    print(f"Train period: 0 to {train_end_idx} (50%)")
    print(f"Val period:   {train_end_idx} to {val_end_idx} (25%)")
    print(f"Test period:  {val_end_idx} to {total_bars} (25% Out-of-Sample)")

    capital = 10000.0
    positions = {}
    closed_trades = []
    pending_orders = []
    equity_curve = []

    t0 = time.time()
    for bar_num, current_time in enumerate(sorted_times):
        # Determine split tag
        if bar_num < train_end_idx:
            split_tag = "TRAIN"
        elif bar_num < val_end_idx:
            split_tag = "VAL"
        else:
            split_tag = "TEST_OUT_OF_SAMPLE"

        # A. Fill pending buy orders at open
        remaining_orders = []
        for order in pending_orders:
            sym = order["symbol"]
            if sym in sym_arrays and current_time in time_to_idx[sym]:
                idx = time_to_idx[sym][current_time]
                open_p = sym_arrays[sym]["open"][idx]
                exec_p = open_p * (1.0 + slippage_pct / 100.0)
                fee = trade_amount * (fee_pct / 100.0)
                net_usdt = trade_amount - fee
                qty = net_usdt / exec_p
                capital -= trade_amount

                stop_px = order["plan"]["stop_price"]
                target_px = order["plan"]["target_price"]
                inv_px = order["plan"]["invalidation_price"]

                positions[sym] = {
                    "symbol": sym,
                    "split_tag": split_tag,
                    "setup_id": order["plan"]["setup_id"],
                    "setup_name": order["plan"]["setup_name"],
                    "entry_time": current_time,
                    "entry_price": exec_p,
                    "quantity": qty,
                    "cost_usdt": trade_amount,
                    "buy_fee": fee,
                    "highest_price": exec_p,
                    "initial_stop_price": stop_px,
                    "stop_loss_price": stop_px,
                    "take_profit_price": target_px,
                    "invalidation_price": inv_px,
                    "max_holding_bars": order["plan"]["max_holding_bars"],
                    "bars_held": 0,
                    "trailing_active": False,
                    "reason": order["plan"]["reason"]
                }
            else:
                remaining_orders.append(order)
        pending_orders = remaining_orders

        # B. Intrabar risk and exit checks for open positions
        symbols_to_close = []
        for sym, pos in list(positions.items()):
            if sym not in sym_arrays or current_time not in time_to_idx[sym]:
                continue
            idx = time_to_idx[sym][current_time]
            arr = sym_arrays[sym]
            open_p = arr["open"][idx]
            high_p = arr["high"][idx]
            low_p = arr["low"][idx]
            close_p = arr["close"][idx]
            curr_atr = arr["atr"][idx]

            pos["bars_held"] += 1
            entry_px = pos["entry_price"]
            sl = pos["stop_loss_price"]
            tp = pos["take_profit_price"]

            if high_p > pos["highest_price"]:
                pos["highest_price"] = high_p
            highest_seen = pos["highest_price"]

            # 1. Conservative tie-breaker: If both SL and TP touched on same bar -> SL hits first!
            hit_sl = low_p <= sl
            hit_tp = high_p >= tp
            if hit_sl and hit_tp:
                symbols_to_close.append((sym, sl, "Conservative SL Hit (Intrabar Tie-Break)"))
                continue
            if hit_sl:
                symbols_to_close.append((sym, sl, f"Hard Stop-Loss Hit (${sl:,.2f})"))
                continue
            if hit_tp:
                symbols_to_close.append((sym, tp, f"Take-Profit Target Hit (${tp:,.2f})"))
                continue

            # 2. Hold for Profit: Lock break-even (+fees) after +1.5R gain, and let trade run to target
            r_dist = max(0.0001, entry_px - pos["initial_stop_price"])
            gain = highest_seen - entry_px
            if gain >= 1.5 * r_dist:
                pos["trailing_active"] = True
                be_price = round(entry_px * 1.0035, 4)
                if pos["stop_loss_price"] < be_price:
                    pos["stop_loss_price"] = be_price

                # Wider runner trail (2.5x ATR) only after reaching +2.0R
                if gain >= 2.0 * r_dist:
                    trail_px = round(highest_seen - (2.5 * curr_atr), 4)
                    if trail_px > pos["stop_loss_price"]:
                        pos["stop_loss_price"] = trail_px

                if low_p <= pos["stop_loss_price"]:
                    symbols_to_close.append((sym, pos["stop_loss_price"], f"Protected Exit Hit (${pos['stop_loss_price']:,.2f})"))
                    continue

            # 3. Max holding bars
            if pos["bars_held"] >= pos["max_holding_bars"]:
                symbols_to_close.append((sym, close_p, f"Max Hold Exceeded ({pos['bars_held']} bars)"))
                continue

            # 4. Sell if needed: Invalidation price lost
            if close_p <= pos["invalidation_price"]:
                symbols_to_close.append((sym, close_p, f"Setup Invalidation: Lost support (${pos['invalidation_price']:,.2f})"))
                continue

        # Execute closes
        for sym, exit_p, exit_reason in symbols_to_close:
            pos = positions.pop(sym, None)
            if not pos:
                continue
            exec_exit = exit_p * (1.0 - slippage_pct / 100.0)
            gross = pos["quantity"] * exec_exit
            sell_fee = gross * (fee_pct / 100.0)
            net_proceeds = gross - sell_fee
            realized_pnl = net_proceeds - pos["cost_usdt"]
            total_fees = pos["buy_fee"] + sell_fee
            capital += net_proceeds

            closed_trades.append({
                "id": f"DEC-TRD-{len(closed_trades)+1}",
                "symbol": sym,
                "split_tag": pos["split_tag"],
                "setup_id": pos["setup_id"],
                "setup_name": pos["setup_name"],
                "entry_time": pos["entry_time"],
                "exit_time": current_time,
                "hold_bars": pos["bars_held"],
                "hold_duration_sec": current_time - pos["entry_time"],
                "entry_price": round(pos["entry_price"], 4),
                "exit_price": round(exec_exit, 4),
                "cost_usdt": round(pos["cost_usdt"], 2),
                "proceeds_usdt": round(net_proceeds, 2),
                "realized_pnl": round(realized_pnl, 4),
                "realized_pnl_pct": round((realized_pnl / pos["cost_usdt"]) * 100.0, 2),
                "total_fees": round(total_fees, 4),
                "reason": exit_reason
            })

        # C. Scan for entries on closed bar if slots available
        if len(positions) + len(pending_orders) < max_open_positions:
            # 1. Macro Regime Check
            btc_slice = pd.DataFrame()
            if "BTC/USDT" in enriched and current_time in time_to_idx["BTC/USDT"]:
                b_idx = time_to_idx["BTC/USDT"][current_time]
                btc_slice = enriched["BTC/USDT"].iloc[max(0, b_idx-60):b_idx+1]
            macro_regime = decision_engine.evaluate_macro_regime(btc_slice)

            # 2. Rank best coins
            ranked_coins = decision_engine.rank_best_coins(enriched, current_time, time_to_idx)

            # 3. Scan ranked coins in order of strength
            for c_score in ranked_coins:
                sym = c_score.symbol
                if sym in positions or any(o["symbol"] == sym for o in pending_orders):
                    continue

                # Correlation cap on alts
                if sym != "BTC/USDT":
                    alt_count = len([s for s in positions if s != "BTC/USDT"]) + len([o for o in pending_orders if o["symbol"] != "BTC/USDT"])
                    if alt_count >= max_correlated_positions:
                        continue

                c_idx = time_to_idx[sym][current_time]
                df_slice = enriched[sym].iloc[max(0, c_idx-60):c_idx+1]
                plan = decision_engine.evaluate_best_pattern(sym, df_slice, macro_regime)

                if plan:
                    pending_orders.append({
                        "symbol": sym,
                        "plan": plan,
                        "eval_time": current_time
                    })
                    if len(positions) + len(pending_orders) >= max_open_positions:
                        break

        # Equity calculation
        unrealized = 0.0
        for sym, pos in positions.items():
            if sym in sym_arrays and current_time in time_to_idx[sym]:
                idx = time_to_idx[sym][current_time]
                px = sym_arrays[sym]["close"][idx]
                unrealized += (pos["quantity"] * px * (1.0 - slippage_pct / 100.0) * (1.0 - fee_pct / 100.0)) - pos["cost_usdt"]
        tot_eq = capital + sum(p["cost_usdt"] for p in positions.values()) + unrealized
        equity_curve.append({"time": current_time, "equity": tot_eq})

    elapsed = time.time() - t0
    print(f"Simulation completed in {elapsed:.1f}s | Closed Trades: {len(closed_trades)}")

    # Compute Performance Metrics
    metrics_all = compute_performance_metrics(closed_trades, equity_curve, timeframe=timeframe)

    # Split breakdowns
    df_tr = pd.DataFrame(closed_trades) if closed_trades else pd.DataFrame()
    splits = {}
    if not df_tr.empty:
        for tag in ["TRAIN", "VAL", "TEST_OUT_OF_SAMPLE"]:
            grp = df_tr[df_tr["split_tag"] == tag]
            if not grp.empty:
                w = grp[grp["realized_pnl"] > 0]
                l = grp[grp["realized_pnl"] <= 0]
                gross_win = float(w["realized_pnl"].sum())
                gross_loss = float(abs(l["realized_pnl"].sum()))
                pf = (gross_win / gross_loss) if gross_loss > 0 else 0.0
                splits[tag] = {
                    "trades": len(grp),
                    "win_rate_pct": round((len(w) / len(grp)) * 100.0, 1),
                    "net_pnl": round(float(grp["realized_pnl"].sum()), 2),
                    "fees": round(float(grp["total_fees"].sum()), 2),
                    "avg_win": round(float(w["realized_pnl"].mean()), 2) if not w.empty else 0.0,
                    "avg_loss": round(float(abs(l["realized_pnl"].mean())), 2) if not l.empty else 0.0,
                    "payoff": round((float(w["realized_pnl"].mean()) / float(abs(l["realized_pnl"].mean()))), 2) if not w.empty and not l.empty else 0.0,
                    "profit_factor": round(pf, 2),
                    "expectancy": round(float(grp["realized_pnl"].mean()), 4)
                }

    metrics_all["splits"] = splits

    # Save trades CSV
    os.makedirs("results", exist_ok=True)
    if not df_tr.empty:
        df_tr.to_csv("results/trades_DECISION_ENGINE_1h.csv", index=False)
        with open("results/summary_DECISION_ENGINE_1h.json", "w") as f:
            json.dump(metrics_all, f, indent=2)

    return metrics_all, closed_trades


if __name__ == "__main__":
    metrics, trades = run_decision_backtest()
    print("\n" + "="*80)
    print("DECISION ENGINE WALK-FORWARD RESULTS")
    print("="*80)
    print(f"Total Trades: {metrics['total_trades']}")
    print(f"Overall Win Rate: {metrics['win_rate_pct']}%")
    print(f"Payoff Ratio: {metrics['payoff_ratio']:.2f}")
    print(f"Profit Factor: {metrics['profit_factor']:.2f}")
    print(f"Net PnL: ${metrics['net_pnl_usd']:.2f}")
    print(f"Expectancy: ${metrics['expectancy_per_trade_usd']:.4f} / trade")
    print("\nWALK-FORWARD CHRONOLOGICAL SPLITS:")
    for tag, s in metrics.get("splits", {}).items():
        print(f"  [{tag}]: {s['trades']} trades | WR: {s['win_rate_pct']}% | Payoff: {s['payoff']} | PF: {s['profit_factor']} | Net PnL: ${s['net_pnl']} | Exp: ${s['expectancy']}")
    print("="*80)
