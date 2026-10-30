"""
Proposal A Strategy Engine: Higher-Timeframe Macro Trend Following.
Strictly implements the pre-registered protocol from PLAN_A.md:
- 17 Liquid Assets, 2019-2026
- Closed-candle signals, next-bar open execution
- 70% In-Sample Train / 30% Out-of-Sample Test split
- Grid search on Train (54 candidate sets), single evaluation on Test
- Neighbor parameter robustness (+/- 20%)
- 100-seed random-entry baseline with identical exits
- Buy-and-hold BTC benchmark
- Per-year breakdown (2019-2026)
- Fee tiers: 0.10% (standard) and 0.075% (BNB discount)
"""

import os
import sys
import time
import json
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, List, Tuple

sys.path.insert(0, os.getcwd())

DATA_DIR = "backtest/data/proposal_a"
SYMBOLS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "XRP/USDT", "ADA/USDT",
    "DOGE/USDT", "SOL/USDT", "TRX/USDT", "LTC/USDT", "LINK/USDT",
    "AVAX/USDT", "DOT/USDT", "MATIC/USDT", "NEAR/USDT", "ATOM/USDT",
    "UNI/USDT", "SUI/USDT"
]


def compute_features(df: pd.DataFrame, ema_period: int, donchian_entry: int, donchian_exit: int, atr_period: int = 14) -> pd.DataFrame:
    """Precompute indicators vectorially without lookahead bias."""
    d = df.copy()
    c = d["close"]
    h = d["high"]
    l = d["low"]

    # 1. Trend EMA
    d["ema_trend"] = c.ewm(span=ema_period, adjust=False).mean()

    # 2. Donchian Channel High (shifted by 1 so current bar cannot see itself)
    d["donchian_high"] = h.rolling(donchian_entry).max().shift(1)

    # 3. Donchian Channel Low for Exit (shifted by 1)
    d["donchian_low"] = l.rolling(donchian_exit).max().shift(1)

    # 4. ATR
    tr1 = h - l
    tr2 = (h - c.shift(1)).abs()
    tr3 = (l - c.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    d["atr"] = tr.rolling(atr_period).mean()

    return d


def load_all_data(timeframe: str) -> Dict[str, pd.DataFrame]:
    data = {}
    for sym in SYMBOLS:
        safe = sym.replace("/", "_")
        p = os.path.join(DATA_DIR, f"{safe}_{timeframe}.csv")
        if os.path.exists(p):
            df = pd.read_csv(p)
            df["dt"] = pd.to_datetime(df["time"], unit="s", utc=True)
            data[sym] = df
    return data


def simulate_portfolio(
    data_dict: Dict[str, pd.DataFrame],
    ema_period: int,
    donchian_entry: int,
    donchian_exit: int,
    stop_atr_mult: float,
    trail_atr_mult: float,
    fee_pct: float = 0.10,
    slippage_pct: float = 0.05,
    trade_amt: float = 100.0,
    max_positions: int = 5,
    max_alts: int = 3,
    start_time: int = 0,
    end_time: int = 9999999999
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Chronological multi-asset simulation.
    Signals on closed candle t, fills at open of candle t+1.
    Conservative intrabar execution.
    """
    # 1. Precompute features for each symbol
    precomputed = {}
    all_timestamps = set()
    for sym, df in data_dict.items():
        feat = compute_features(df, ema_period, donchian_entry, donchian_exit)
        # Filter within range if specified
        precomputed[sym] = {
            "time": feat["time"].to_numpy(dtype=int),
            "open": feat["open"].to_numpy(dtype=float),
            "high": feat["high"].to_numpy(dtype=float),
            "low": feat["low"].to_numpy(dtype=float),
            "close": feat["close"].to_numpy(dtype=float),
            "ema_trend": feat["ema_trend"].to_numpy(dtype=float),
            "donchian_high": feat["donchian_high"].to_numpy(dtype=float),
            "donchian_low": feat["donchian_low"].to_numpy(dtype=float),
            "atr": feat["atr"].to_numpy(dtype=float)
        }
        all_timestamps.update(feat["time"].tolist())

    sorted_times = sorted([t for t in all_timestamps if start_time <= t <= end_time])
    time_to_idx = {sym: {t: i for i, t in enumerate(arr["time"])} for sym, arr in precomputed.items()}

    positions = {}
    pending_orders = []
    closed_trades = []

    fee_rate = fee_pct / 100.0
    slip_rate = slippage_pct / 100.0

    for current_time in sorted_times:
        # Step A: Fill pending orders at Open
        rem_orders = []
        for o in pending_orders:
            sym = o["symbol"]
            if sym in precomputed and current_time in time_to_idx[sym]:
                idx = time_to_idx[sym][current_time]
                arr = precomputed[sym]
                open_p = arr["open"][idx]
                exec_buy = open_p * (1.0 + slip_rate)
                buy_fee = trade_amt * fee_rate
                qty = (trade_amt - buy_fee) / exec_buy
                atr = arr["atr"][idx] if not np.isnan(arr["atr"][idx]) else open_p * 0.02

                initial_stop = exec_buy - (stop_atr_mult * atr)
                r_dist = max(0.0001, exec_buy - initial_stop)

                positions[sym] = {
                    "entry_time": current_time,
                    "entry_price": exec_buy,
                    "open_p": open_p,
                    "quantity": qty,
                    "cost": trade_amt,
                    "buy_fee": buy_fee,
                    "initial_stop": initial_stop,
                    "stop_price": initial_stop,
                    "r_dist": r_dist,
                    "highest_seen": exec_buy,
                    "be_activated": False,
                    "bars_held": 0
                }
            else:
                rem_orders.append(o)
        pending_orders = rem_orders

        # Step B: Check open positions
        to_close = []
        for sym, pos in list(positions.items()):
            if sym not in precomputed or current_time not in time_to_idx[sym]:
                continue
            idx = time_to_idx[sym][current_time]
            arr = precomputed[sym]
            open_p = arr["open"][idx]
            high_p = arr["high"][idx]
            low_p = arr["low"][idx]
            close_p = arr["close"][idx]
            curr_atr = arr["atr"][idx] if not np.isnan(arr["atr"][idx]) else open_p * 0.02
            pos["bars_held"] += 1

            if high_p > pos["highest_seen"]:
                pos["highest_seen"] = high_p

            # 1. Break-Even Ratchet after +1R
            gain = pos["highest_seen"] - pos["entry_price"]
            if gain >= 1.0 * pos["r_dist"]:
                be_price = pos["entry_price"] * (1.0 + 2.0 * fee_rate + 2.0 * slip_rate)
                if pos["stop_price"] < be_price:
                    pos["stop_price"] = be_price
                    pos["be_activated"] = True

                # 2. ATR Trailing runner exit
                trail_price = pos["highest_seen"] - (trail_atr_mult * curr_atr)
                if trail_price > pos["stop_price"]:
                    pos["stop_price"] = trail_price

            # 3. Check Stop-Loss breach
            if low_p <= pos["stop_price"]:
                to_close.append((sym, pos["stop_price"], "Stop Loss / Trailing Stop", current_time))
            # 4. Chandelier Exit: Close below N-period low
            elif close_p < arr["donchian_low"][idx]:
                to_close.append((sym, close_p, "Donchian Exit Channel", current_time))

        for sym, exit_p, reason, t_exit in to_close:
            if sym in positions:
                pos = positions.pop(sym)
                exec_sell = exit_p * (1.0 - slip_rate)
                gross_proceeds = pos["quantity"] * exec_sell
                sell_fee = gross_proceeds * fee_rate
                net_proceeds = gross_proceeds - sell_fee
                net_pnl = net_proceeds - pos["cost"]

                # Detailed arithmetic reconciliation
                total_fees = pos["buy_fee"] + sell_fee
                buy_slip = pos["quantity"] * (pos["entry_price"] - pos["open_p"])
                sell_slip = pos["quantity"] * (exit_p - exec_sell)
                total_slip = buy_slip + sell_slip
                gross_pnl = net_pnl + total_fees + total_slip

                closed_trades.append({
                    "symbol": sym,
                    "entry_time": pos["entry_time"],
                    "exit_time": t_exit,
                    "bars_held": pos["bars_held"],
                    "entry_price": pos["entry_price"],
                    "exit_price": exec_sell,
                    "gross_pnl": gross_pnl,
                    "fees_paid": total_fees,
                    "slippage_paid": total_slip,
                    "net_pnl": net_pnl,
                    "reason": reason
                })

        # Step C: Generate signals on CLOSED bar at current_time
        if len(positions) + len(pending_orders) < max_positions:
            for sym, arr in precomputed.items():
                if current_time not in time_to_idx[sym]:
                    continue
                idx = time_to_idx[sym][current_time]
                if idx < 60:
                    continue
                if sym in positions or any(o["symbol"] == sym for o in pending_orders):
                    continue

                # Correlation cap: Max alts
                if sym != "BTC/USDT":
                    curr_alts = len([s for s in positions if s != "BTC/USDT"]) + len([o for o in pending_orders if o["symbol"] != "BTC/USDT"])
                    if curr_alts >= max_alts:
                        continue

                c = arr["close"][idx]
                ema = arr["ema_trend"][idx]
                dh = arr["donchian_high"][idx]

                # Pre-registered Entry Condition: Close > Trend EMA AND Close > Donchian High
                if not np.isnan(ema) and not np.isnan(dh):
                    if c > ema and c > dh:
                        pending_orders.append({"symbol": sym, "signal_time": current_time})
                        if len(positions) + len(pending_orders) >= max_positions:
                            break

    # Metrics summary
    if not closed_trades:
        return [], {"trades": 0, "net_pnl": 0.0, "win_rate": 0.0, "profit_factor": 0.0, "expectancy": 0.0}

    df_t = pd.DataFrame(closed_trades)
    n = len(df_t)
    w = df_t[df_t["net_pnl"] > 0]
    l = df_t[df_t["net_pnl"] <= 0]
    wr = len(w) / n * 100.0 if n > 0 else 0.0
    net_pnl = df_t["net_pnl"].sum()
    gross_pnl = df_t["gross_pnl"].sum()
    fees = df_t["fees_paid"].sum()
    slippage = df_t["slippage_paid"].sum()

    gp = w["net_pnl"].sum() if len(w) > 0 else 0.0
    gl = abs(l["net_pnl"].sum()) if len(l) > 0 else 0.0
    pf = (gp / gl) if gl > 0 else (99.0 if gp > 0 else 0.0)
    avg_w = w["net_pnl"].mean() if len(w) > 0 else 0.0
    avg_l = abs(l["net_pnl"].mean()) if len(l) > 0 else 0.0
    payoff = avg_w / avg_l if avg_l > 0 else 0.0
    exp = net_pnl / n if n > 0 else 0.0

    # Max Drawdown
    cum = df_t["net_pnl"].cumsum()
    eq = 10000.0 + cum
    peak = eq.cummax()
    dd = (eq - peak) / peak * 100.0
    max_dd = abs(dd.min()) if len(dd) > 0 else 0.0

    summary = {
        "trades": n,
        "win_rate": round(wr, 2),
        "payoff": round(payoff, 2),
        "profit_factor": round(pf, 2),
        "gross_pnl": round(gross_pnl, 2),
        "fees_paid": round(fees, 2),
        "slippage_paid": round(slippage, 2),
        "net_pnl": round(net_pnl, 2),
        "expectancy": round(exp, 4),
        "max_drawdown": round(max_dd, 2)
    }
    return closed_trades, summary


def run_random_entry_baseline(data_dict: Dict[str, pd.DataFrame], best_params: Dict[str, Any], start_time: int, end_time: int, num_seeds: int = 100) -> Dict[str, Any]:
    """100-seed random entry baseline using the SAME exits and costs over the SAME period."""
    print(f"Running 100-seed random entry baseline for Proposal A...", flush=True)
    seeds_results = []
    all_timestamps = set()
    precomputed = {}
    for sym, df in data_dict.items():
        feat = compute_features(df, int(best_params["ema"]), int(best_params["entry"]), int(best_params["exit"]))
        precomputed[sym] = {
            "time": feat["time"].to_numpy(dtype=int),
            "open": feat["open"].to_numpy(dtype=float),
            "high": feat["high"].to_numpy(dtype=float),
            "low": feat["low"].to_numpy(dtype=float),
            "close": feat["close"].to_numpy(dtype=float),
            "donchian_low": feat["donchian_low"].to_numpy(dtype=float),
            "atr": feat["atr"].to_numpy(dtype=float)
        }
        all_timestamps.update(feat["time"].tolist())

    sorted_times = sorted([t for t in all_timestamps if start_time <= t <= end_time])
    time_to_idx = {sym: {t: i for i, t in enumerate(arr["time"])} for sym, arr in precomputed.items()}

    fee_rate = 0.001
    slip_rate = 0.0005
    trade_amt = 100.0

    for seed in range(1, num_seeds + 1):
        rng = np.random.default_rng(seed)
        positions = {}
        pending_orders = []
        trades = []

        for current_time in sorted_times:
            # Fill pending
            rem = []
            for sym in pending_orders:
                if sym in precomputed and current_time in time_to_idx[sym]:
                    idx = time_to_idx[sym][current_time]
                    arr = precomputed[sym]
                    open_p = arr["open"][idx]
                    exec_buy = open_p * (1.0 + slip_rate)
                    buy_fee = trade_amt * fee_rate
                    qty = (trade_amt - buy_fee) / exec_buy
                    atr = arr["atr"][idx] if not np.isnan(arr["atr"][idx]) else open_p * 0.02
                    initial_stop = exec_buy - (best_params["stop_atr"] * atr)
                    r_dist = max(0.0001, exec_buy - initial_stop)

                    positions[sym] = {
                        "entry_time": current_time,
                        "entry_price": exec_buy,
                        "quantity": qty,
                        "cost": trade_amt,
                        "buy_fee": buy_fee,
                        "stop_price": initial_stop,
                        "r_dist": r_dist,
                        "highest_seen": exec_buy,
                        "bars_held": 0
                    }
                else:
                    rem.append(sym)
            pending_orders = rem

            # Exits
            to_close = []
            for sym, pos in list(positions.items()):
                if sym not in precomputed or current_time not in time_to_idx[sym]:
                    continue
                idx = time_to_idx[sym][current_time]
                arr = precomputed[sym]
                high_p = arr["high"][idx]
                low_p = arr["low"][idx]
                close_p = arr["close"][idx]
                curr_atr = arr["atr"][idx] if not np.isnan(arr["atr"][idx]) else arr["open"][idx] * 0.02
                pos["bars_held"] += 1

                if high_p > pos["highest_seen"]:
                    pos["highest_seen"] = high_p

                gain = pos["highest_seen"] - pos["entry_price"]
                if gain >= 1.0 * pos["r_dist"]:
                    be = pos["entry_price"] * 1.003
                    pos["stop_price"] = max(pos["stop_price"], be)
                    trail = pos["highest_seen"] - (best_params["trail_atr"] * curr_atr)
                    if trail > pos["stop_price"]:
                        pos["stop_price"] = trail

                if low_p <= pos["stop_price"]:
                    to_close.append((sym, pos["stop_price"]))
                elif close_p < arr["donchian_low"][idx]:
                    to_close.append((sym, close_p))

            for sym, exit_p in to_close:
                pos = positions.pop(sym)
                exec_sell = exit_p * (1.0 - slip_rate)
                gross = pos["quantity"] * exec_sell
                sell_fee = gross * fee_rate
                net = gross - sell_fee
                pnl = net - pos["cost"]
                trades.append(pnl)

            # Random entries
            if len(positions) + len(pending_orders) < 5:
                for sym in precomputed:
                    if sym in positions or sym in pending_orders:
                        continue
                    if rng.random() < 0.02:  # calibrated entry frequency
                        pending_orders.append(sym)
                        if len(positions) + len(pending_orders) >= 5:
                            break

        if trades:
            s_trades = pd.Series(trades)
            w = s_trades[s_trades > 0]
            l = s_trades[s_trades <= 0]
            pf = w.sum() / abs(l.sum()) if abs(l.sum()) > 0 else 0.0
            seeds_results.append({
                "seed": seed,
                "trades": len(s_trades),
                "win_rate": len(w) / len(s_trades) * 100.0,
                "profit_factor": pf,
                "net_pnl": s_trades.sum(),
                "expectancy": s_trades.mean()
            })

    df_seeds = pd.DataFrame(seeds_results)
    return {
        "mean_trades": round(float(df_seeds["trades"].mean()), 1),
        "mean_win_rate": round(float(df_seeds["win_rate"].mean()), 2),
        "mean_profit_factor": round(float(df_seeds["profit_factor"].mean()), 2),
        "mean_net_pnl": round(float(df_seeds["net_pnl"].mean()), 2),
        "mean_expectancy": round(float(df_seeds["expectancy"].mean()), 4),
        "std_expectancy": round(float(df_seeds["expectancy"].std()), 4),
        "spread_expectancy": [round(float(df_seeds["expectancy"].min()), 4), round(float(df_seeds["expectancy"].max()), 4)]
    }


def compute_btc_buy_and_hold(btc_df: pd.DataFrame, start_time: int, end_time: int) -> Dict[str, Any]:
    sub = btc_df[(btc_df["time"] >= start_time) & (btc_df["time"] <= end_time)].copy()
    if sub.empty:
        return {}
    p_start = sub["open"].iloc[0]
    p_end = sub["close"].iloc[-1]
    ret_pct = (p_end - p_start) / p_start * 100.0
    sub["cummax"] = sub["close"].cummax()
    sub["dd"] = (sub["close"] - sub["cummax"]) / sub["cummax"] * 100.0
    max_dd = abs(sub["dd"].min())
    return {
        "start_price": round(p_start, 2),
        "end_price": round(p_end, 2),
        "return_pct": round(ret_pct, 2),
        "net_pnl_on_10k": round(10000.0 * (ret_pct / 100.0), 2),
        "max_drawdown_pct": round(max_dd, 2)
    }


def compute_per_year_breakdown(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not trades:
        return []
    df_t = pd.DataFrame(trades)
    df_t["dt"] = pd.to_datetime(df_t["entry_time"], unit="s", utc=True)
    df_t["year"] = df_t["dt"].dt.year

    yearly = []
    for yr, grp in df_t.groupby("year"):
        w = grp[grp["net_pnl"] > 0]
        l = grp[grp["net_pnl"] <= 0]
        gp = w["net_pnl"].sum() if len(w) > 0 else 0.0
        gl = abs(l["net_pnl"].sum()) if len(l) > 0 else 0.0
        pf = gp / gl if gl > 0 else (99.0 if gp > 0 else 0.0)
        yearly.append({
            "year": int(yr),
            "trades": len(grp),
            "win_rate": round(len(w) / len(grp) * 100.0, 1),
            "profit_factor": round(pf, 2),
            "net_pnl": round(float(grp["net_pnl"].sum()), 2),
            "expectancy": round(float(grp["net_pnl"].mean()), 4),
            "is_positive": bool(float(grp["net_pnl"].sum()) > 0)
        })
    return yearly


def main():
    print("=" * 80)
    print("EXECUTING PROPOSAL A EMPIRICAL VALIDATION (PLAN_A.md)")
    print("=" * 80)

    # 1. Load Data for 4h and 1d
    data_4h = load_all_data("4h")
    data_1d = load_all_data("1d")

    print(f"Loaded 4h dataset for {len(data_4h)} symbols.")
    print(f"Loaded 1d dataset for {len(data_1d)} symbols.")

    # Get chronological time bounds for 4h
    all_times = set()
    for d in data_4h.values():
        all_times.update(d["time"].tolist())
    sorted_times = sorted(list(all_times))
    total_bars = len(sorted_times)

    # 70% In-Sample Train / 30% Out-of-Sample Test
    split_idx = int(total_bars * 0.70)
    train_start = sorted_times[0]
    train_end = sorted_times[split_idx]
    test_start = sorted_times[split_idx + 1]
    test_end = sorted_times[-1]

    t_train_start_str = datetime.fromtimestamp(train_start, tz=timezone.utc).strftime("%Y-%m-%d")
    t_train_end_str = datetime.fromtimestamp(train_end, tz=timezone.utc).strftime("%Y-%m-%d")
    t_test_start_str = datetime.fromtimestamp(test_start, tz=timezone.utc).strftime("%Y-%m-%d")
    t_test_end_str = datetime.fromtimestamp(test_end, tz=timezone.utc).strftime("%Y-%m-%d")

    print(f"\nChronological Split Specifications:")
    print(f"  In-Sample TRAIN (70%): {t_train_start_str} to {t_train_end_str} ({split_idx} bars)")
    print(f"  Out-of-Sample TEST (30%): {t_test_start_str} to {t_test_end_str} ({total_bars - split_idx} bars)")

    # 2. Pre-registered Parameter Grid on In-Sample (Train)
    # T in {150, 200}, N in {20, 40, 55}, K in {2.0, 2.5, 3.0}, M in {2.0, 2.5, 3.0}
    # Donchian exit fixed at 10 bars
    ema_vals = [150, 200]
    donchian_vals = [20, 40, 55]
    stop_atr_vals = [2.0, 2.5, 3.0]
    trail_atr_vals = [2.0, 2.5, 3.0]

    grid_results = []
    print(f"\nRunning In-Sample Parameter Grid Exploration on 4h ({len(ema_vals)*len(donchian_vals)*len(stop_atr_vals)*len(trail_atr_vals)} candidate configurations)...")
    t0 = time.time()

    config_num = 0
    for ema in ema_vals:
        for entry in donchian_vals:
            for stop_atr in stop_atr_vals:
                for trail_atr in trail_atr_vals:
                    config_num += 1
                    _, summary = simulate_portfolio(
                        data_4h,
                        ema_period=ema,
                        donchian_entry=entry,
                        donchian_exit=10,
                        stop_atr_mult=stop_atr,
                        trail_atr_mult=trail_atr,
                        fee_pct=0.10,
                        slippage_pct=0.05,
                        start_time=train_start,
                        end_time=train_end
                    )
                    summary["ema"] = ema
                    summary["entry"] = entry
                    summary["exit"] = 10
                    summary["stop_atr"] = stop_atr
                    summary["trail_atr"] = trail_atr
                    summary["config_id"] = config_num
                    grid_results.append(summary)

    print(f"Completed {len(grid_results)} in-sample grid evaluations in {time.time()-t0:.1f}s.")
    df_grid = pd.DataFrame(grid_results)
    df_grid.sort_values(by="profit_factor", ascending=False, inplace=True)
    os.makedirs("results/proposal_a", exist_ok=True)
    df_grid.to_csv("results/proposal_a/in_sample_grid_search_4h.csv", index=False)

    print("\nTop 5 In-Sample Configurations (by Profit Factor):")
    print(df_grid[["config_id", "ema", "entry", "stop_atr", "trail_atr", "trades", "win_rate", "payoff", "profit_factor", "net_pnl", "expectancy"]].head(5).to_string(index=False))

    best_cfg = df_grid.iloc[0].to_dict()
    print(f"\n>>> Selected Best In-Sample Configuration: Config #{int(best_cfg['config_id'])}")
    print(f"    EMA: {int(best_cfg['ema'])}, Donchian Entry: {int(best_cfg['entry'])}, Stop ATR: {best_cfg['stop_atr']}, Trail ATR: {best_cfg['trail_atr']}")
    print(f"    Train PnL: ${best_cfg['net_pnl']}, Profit Factor: {best_cfg['profit_factor']}, Expectancy: ${best_cfg['expectancy']}/trade")

    # 3. Robustness Sensitivity Check on Neighbors (+/- 20%)
    print("\n" + "="*80)
    print("STEP 2: NEIGHBOR PARAMETER ROBUSTNESS CHECK (+/- 20% on In-Sample)")
    print("="*80)
    neighbors = [
        {"desc": "Stop ATR -20%", "stop_atr": round(best_cfg["stop_atr"] * 0.80, 2), "trail_atr": best_cfg["trail_atr"], "entry": int(best_cfg["entry"])},
        {"desc": "Stop ATR +20%", "stop_atr": round(best_cfg["stop_atr"] * 1.20, 2), "trail_atr": best_cfg["trail_atr"], "entry": int(best_cfg["entry"])},
        {"desc": "Trail ATR -20%", "stop_atr": best_cfg["stop_atr"], "trail_atr": round(best_cfg["trail_atr"] * 0.80, 2), "entry": int(best_cfg["entry"])},
        {"desc": "Trail ATR +20%", "stop_atr": best_cfg["stop_atr"], "trail_atr": round(best_cfg["trail_atr"] * 1.20, 2), "entry": int(best_cfg["entry"])},
        {"desc": "Entry Window -20%", "stop_atr": best_cfg["stop_atr"], "trail_atr": best_cfg["trail_atr"], "entry": max(10, int(best_cfg["entry"] * 0.80))},
        {"desc": "Entry Window +20%", "stop_atr": best_cfg["stop_atr"], "trail_atr": best_cfg["trail_atr"], "entry": int(best_cfg["entry"] * 1.20)}
    ]
    neighbor_results = []
    for n_cfg in neighbors:
        _, n_sum = simulate_portfolio(
            data_4h,
            ema_period=int(best_cfg["ema"]),
            donchian_entry=n_cfg["entry"],
            donchian_exit=10,
            stop_atr_mult=n_cfg["stop_atr"],
            trail_atr_mult=n_cfg["trail_atr"],
            fee_pct=0.10,
            slippage_pct=0.05,
            start_time=train_start,
            end_time=train_end
        )
        n_sum["variation"] = n_cfg["desc"]
        neighbor_results.append(n_sum)
    df_neighbors = pd.DataFrame(neighbor_results)
    df_neighbors.to_csv("results/proposal_a/neighbor_robustness_check.csv", index=False)
    print(df_neighbors[["variation", "trades", "win_rate", "profit_factor", "net_pnl", "expectancy"]].to_string(index=False))

    # 4. SINGLE OUT-OF-SAMPLE TEST EVALUATION (FROZEN 30%)
    print("\n" + "="*80)
    print("STEP 3: FROZEN OUT-OF-SAMPLE TEST EVALUATION (EXACTLY ONCE)")
    print(f"Period: {t_test_start_str} to {t_test_end_str}")
    print("="*80)

    # 4.A Standard 0.10% Taker Fee Case
    oos_trades_010, oos_summary_010 = simulate_portfolio(
        data_4h,
        ema_period=int(best_cfg["ema"]),
        donchian_entry=int(best_cfg["entry"]),
        donchian_exit=10,
        stop_atr_mult=best_cfg["stop_atr"],
        trail_atr_mult=best_cfg["trail_atr"],
        fee_pct=0.10,
        slippage_pct=0.05,
        start_time=test_start,
        end_time=test_end
    )

    # 4.B Discount 0.075% BNB Case
    oos_trades_0075, oos_summary_0075 = simulate_portfolio(
        data_4h,
        ema_period=int(best_cfg["ema"]),
        donchian_entry=int(best_cfg["entry"]),
        donchian_exit=10,
        stop_atr_mult=best_cfg["stop_atr"],
        trail_atr_mult=best_cfg["trail_atr"],
        fee_pct=0.075,
        slippage_pct=0.05,
        start_time=test_start,
        end_time=test_end
    )

    # Save OOS trades
    pd.DataFrame(oos_trades_010).to_csv("results/proposal_a/out_of_sample_trades_fee010.csv", index=False)
    pd.DataFrame(oos_trades_0075).to_csv("results/proposal_a/out_of_sample_trades_fee0075.csv", index=False)

    print("\nOUT-OF-SAMPLE TEST RESULTS (Best Configuration):")
    print(f"Standard Fee (0.10%): Trades={oos_summary_010['trades']} | WR={oos_summary_010['win_rate']}% | Payoff={oos_summary_010['payoff']} | PF={oos_summary_010['profit_factor']} | Net=${oos_summary_010['net_pnl']} | Exp=${oos_summary_010['expectancy']}/trade | MaxDD={oos_summary_010['max_drawdown']}%")
    print(f"Discount Fee (0.075%): Trades={oos_summary_0075['trades']} | WR={oos_summary_0075['win_rate']}% | Payoff={oos_summary_0075['payoff']} | PF={oos_summary_0075['profit_factor']} | Net=${oos_summary_0075['net_pnl']} | Exp=${oos_summary_0075['expectancy']}/trade | MaxDD={oos_summary_0075['max_drawdown']}%")

    # 5. Full 7.8-Year Simulation (2019 to 2026) for Yearly Breakdown
    full_trades, full_summary = simulate_portfolio(
        data_4h,
        ema_period=int(best_cfg["ema"]),
        donchian_entry=int(best_cfg["entry"]),
        donchian_exit=10,
        stop_atr_mult=best_cfg["stop_atr"],
        trail_atr_mult=best_cfg["trail_atr"],
        fee_pct=0.10,
        slippage_pct=0.05,
        start_time=sorted_times[0],
        end_time=sorted_times[-1]
    )
    yearly_breakdown = compute_per_year_breakdown(full_trades)
    df_yearly = pd.DataFrame(yearly_breakdown)
    df_yearly.to_csv("results/proposal_a/yearly_breakdown_2019_2026.csv", index=False)
    print("\nPER-YEAR RESULTS (2019 to 2026, 0.10% Fee):")
    print(df_yearly[["year", "trades", "win_rate", "profit_factor", "net_pnl", "expectancy", "is_positive"]].to_string(index=False))

    positive_years = df_yearly["is_positive"].sum()
    total_years = len(df_yearly)
    pct_positive_years = (positive_years / total_years) * 100.0 if total_years > 0 else 0.0

    # 6. Benchmarks over the OOS Test Period
    btc_df = data_4h.get("BTC/USDT", pd.DataFrame())
    btc_bench = compute_btc_buy_and_hold(btc_df, test_start, test_end)
    print(f"\nBENCHMARK 1: BUY-AND-HOLD BTC (Over OOS Test Period):")
    print(f"  Return: {btc_bench.get('return_pct')}% | Net on $10k: ${btc_bench.get('net_pnl_on_10k')} | Max Drawdown: {btc_bench.get('max_drawdown_pct')}%")

    random_bench = run_random_entry_baseline(data_4h, best_cfg, test_start, test_end, num_seeds=100)
    print(f"\nBENCHMARK 2: 100-SEED RANDOM ENTRY BASELINE (Over OOS Test Period):")
    print(f"  Mean Trades: {random_bench['mean_trades']} | Mean WR: {random_bench['mean_win_rate']}% | Mean PF: {random_bench['mean_profit_factor']}")
    print(f"  Mean Net PnL: ${random_bench['mean_net_pnl']} | Mean Expectancy: ${random_bench['mean_expectancy']}/trade (std: ${random_bench['std_expectancy']})")

    # Z-Score comparison
    oos_exp = oos_summary_010["expectancy"]
    rand_mean_exp = random_bench["mean_expectancy"]
    rand_std_exp = random_bench["std_expectancy"]
    z_score = (oos_exp - rand_mean_exp) / rand_std_exp if rand_std_exp > 0 else 0.0
    print(f"  Strategy vs Random Z-Score: {z_score:.2f} sigma")

    # 7. Check Pre-Registered Pass Criteria (All 6 Must Pass OOS)
    c1 = oos_summary_010["expectancy"] > 0.0
    c2 = oos_summary_010["trades"] >= 200
    c3 = oos_summary_010["profit_factor"] >= 1.30
    c4 = oos_summary_010["max_drawdown"] < 25.0
    c5 = pct_positive_years >= 60.0
    c6 = z_score > 2.0

    criteria_table = [
        {"Criterion": "1. Net Expectancy > $0.00", "Required": "> $0.00", "Measured": f"${oos_summary_010['expectancy']}", "Pass": bool(c1)},
        {"Criterion": "2. Sample Size >= 200 trades", "Required": ">= 200", "Measured": f"{oos_summary_010['trades']}", "Pass": bool(c2)},
        {"Criterion": "3. Profit Factor >= 1.30", "Required": ">= 1.30", "Measured": f"{oos_summary_010['profit_factor']}", "Pass": bool(c3)},
        {"Criterion": "4. Max Drawdown < 25%", "Required": "< 25.0%", "Measured": f"{oos_summary_010['max_drawdown']}%", "Pass": bool(c4)},
        {"Criterion": "5. Positive in >= 60% of years", "Required": ">= 60.0%", "Measured": f"{pct_positive_years:.1f}% ({positive_years}/{total_years} yrs)", "Pass": bool(c5)},
        {"Criterion": "6. Beats Random by > 2.0 sigma", "Required": "> 2.0 sigma", "Measured": f"{z_score:.2f} sigma", "Pass": bool(c6)}
    ]

    all_passed = c1 and c2 and c3 and c4 and c5 and c6
    print("\n" + "="*80)
    print("FINAL PRE-REGISTERED VALIDATION AUDIT (PLAN_A.md)")
    print("="*80)
    for c in criteria_table:
        status_icon = "PASSED [OK]" if c["Pass"] else "FAILED [X]"
        print(f"  {c['Criterion']:<36} | Req: {c['Required']:<12} | Measured: {c['Measured']:<20} | {status_icon}")
    print("="*80)
    print(f"FINAL PROPOSAL A VERDICT: {'PASSED VALIDATION' if all_passed else 'FAILED VALIDATION - NO PASS'}")
    print("="*80)

    # Save complete audit report JSON
    final_output = {
        "status": "PASSED" if all_passed else "FAILED",
        "best_configuration": best_cfg,
        "criteria": criteria_table,
        "oos_summary_010": oos_summary_010,
        "oos_summary_0075": oos_summary_0075,
        "btc_benchmark": btc_bench,
        "random_benchmark": random_bench,
        "yearly_breakdown": yearly_breakdown,
        "neighbor_robustness": neighbor_results,
        "total_configs_tested": len(grid_results) + len(neighbors) + 2
    }
    with open("results/proposal_a/final_validation_report.json", "w") as f:
        json.dump(final_output, f, indent=2)


if __name__ == "__main__":
    main()
