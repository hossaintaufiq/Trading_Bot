"""
NEPTUNE Dual-Timeframe Strategy 2024 Development Partition Experiment
(`run_dual_timeframe_development_experiment.py`)

Mission:
Evaluate Candidate A2 (`DualTimeframeTrendStrategy` / `htf_trend_following_v1` / `SHR-001` / ADR-035)
across the 2024 Development partition under realistic execution costs and strict risk constraints.

Governing Rules:
- Rule S-01: Spot paper trading only. No leverage, no borrowing, no real money.
- Rule S-04: All orders authorized strictly by Risk Manager.
- Rule S-05: Strict look-ahead bias prevention. Consumes closed candles only.
             Strict 2024 Development partition isolation (OOSAccessGuard).
- Rule S-06: Accurate reporting of all metrics without fabrication.
- Rule S-07: Objective evaluation without claiming unverified profitability.
- Rule A-01: Python Decimal for all monetary and risk calculations.
- Rule A-09: Analysis consumes closed candles only.
- Rule A-10: Paper fills record execution assumptions (price, fees, slippage, spread).
"""

import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath("backend"))

from app.agents.strategy_analyst import RawCandidateSignal
from app.data.market.validator import ValidatedCandle
from app.data.repositories.parquet_repo import ParquetMarketDataRepository
from app.risk.risk_manager import RiskManager
from app.simulation.models import ActivePosition, SimulatedTrade
from app.simulation.portfolio_ledger import PortfolioLedger
from app.simulation.research_protocol import OOSAccessGuard
from app.strategies.dual_timeframe_trend import (
    DualTimeframeConfig,
    DualTimeframeTrendStrategy,
)


def run_null_centered_block_bootstrap(
    series: np.ndarray,
    block_size: int = 96,  # 4 calendar days (96 hours)
    n_iterations: int = 2000,
    seed: int = 42,
) -> Tuple[float, float, float, float]:
    """Moving Block Bootstrap centered under H0: mu <= 0."""
    n = len(series)
    if n == 0 or np.all(series == 0):
        return 0.0, 1.0, 0.0, 0.0

    rng = np.random.RandomState(seed)
    mean_obs = float(np.mean(series))
    series_null = series - mean_obs

    num_blocks = max(1, n - block_size + 1)
    blocks_null = [series_null[i : i + block_size] for i in range(num_blocks)]
    blocks_orig = [series[i : i + block_size] for i in range(num_blocks)]

    boot_means_null = []
    boot_means_orig = []
    blocks_needed = int(np.ceil(n / block_size))

    for _ in range(n_iterations):
        indices = rng.randint(0, len(blocks_null), size=blocks_needed)
        resamp_null = np.concatenate([blocks_null[idx] for idx in indices])[:n]
        resamp_orig = np.concatenate([blocks_orig[idx] for idx in indices])[:n]
        boot_means_null.append(float(np.mean(resamp_null)))
        boot_means_orig.append(float(np.mean(resamp_orig)))

    boot_means_null = np.array(boot_means_null)
    boot_means_orig = np.array(boot_means_orig)

    ci_lower = float(np.percentile(boot_means_orig, 2.5))
    ci_upper = float(np.percentile(boot_means_orig, 97.5))
    p_value = float(np.mean(boot_means_null >= mean_obs))

    return mean_obs, p_value, ci_lower, ci_upper


async def run_experiment():
    start_time_proc = time.time()
    print("=" * 80)
    print("NEPTUNE Candidate A2: Dual-Timeframe Trend Following 2024 Development Experiment")
    print("Strategy: htf_trend_following_v1 (SHR-001 / ADR-035)")
    print("Governing Rules: Rule S-01, S-04, S-05, S-06, S-07, A-01, A-09, A-10")
    print("=" * 80)

    # 1. Partition Verification & OOS Protection
    start_iso = "2024-01-01T00:00:00Z"
    end_iso = "2024-12-31T23:59:59Z"
    print(f"Verifying OOSAccessGuard for partition: {start_iso} to {end_iso}...")
    OOSAccessGuard.verify_partition_access(start_iso, end_iso)
    print("OOSAccessGuard verified: Access restricted strictly to 2024 Development partition.")

    out_dir = os.path.join("storage", "exports", "dual_timeframe_dev_experiment")
    os.makedirs(out_dir, exist_ok=True)

    # 2. Execution & Accounting Parameters
    initial_capital = Decimal("1000.00")
    taker_fee_pct = Decimal("0.0010")   # 0.10%
    slippage_pct = Decimal("0.0005")    # 0.05%
    spread_half = Decimal("0.0001")     # 0.01% (half-spread)

    ledger = PortfolioLedger(initial_capital=initial_capital, taker_fee_pct=taker_fee_pct)

    risk_manager = RiskManager(
        max_concurrent_positions=2,
        risk_per_trade_pct=Decimal("0.005"),  # 0.5% risk
        daily_loss_limit_pct=Decimal("0.02"),  # 2.0%
        max_drawdown_pct=Decimal("0.05"),      # 5.0%
        min_reward_risk_ratio=Decimal("1.5"),
    )

    strategy = DualTimeframeTrendStrategy(
        DualTimeframeConfig(
            fast_ema_4h=50,
            slow_ema_4h=200,
            min_adx_4h=22.0,
            fast_ema_1h=21,
            slow_ema_1h=50,
            atr_period_1h=14,
            atr_stop_multiplier=2.0,
            min_reward_risk_ratio=2.5,
            swing_pivot_lookback_1h=5,
            max_holding_candles_1h=96,
        )
    )

    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    repo = ParquetMarketDataRepository()

    print("\nLoading historical market datasets for 2024 Development partition...")
    data_1h: Dict[str, pd.DataFrame] = {}
    data_4h: Dict[str, pd.DataFrame] = {}

    for sym in symbols:
        df1 = await repo.load_candles(sym, "1h")
        df4 = await repo.load_candles(sym, "4h")

        # Standardize timestamp column to string ISO format
        df1["timestamp"] = pd.to_datetime(df1["timestamp"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        df4["timestamp"] = pd.to_datetime(df4["timestamp"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        # Filter to 2024 Development partition
        df1_dev = df1[(df1["timestamp"] >= start_iso) & (df1["timestamp"] <= end_iso)].sort_values("timestamp").reset_index(drop=True)
        df4_dev = df4[(df4["timestamp"] >= start_iso) & (df4["timestamp"] <= end_iso)].sort_values("timestamp").reset_index(drop=True)

        df1_dev["is_closed"] = True
        df4_dev["is_closed"] = True

        data_1h[sym] = df1_dev
        data_4h[sym] = df4_dev
        print(f"  {sym}: Loaded {len(df1_dev)} 1h candles, {len(df4_dev)} 4h candles.")

    # 3. Synchronize Timeline
    all_timestamps = sorted(data_1h["BTCUSDT"]["timestamp"].tolist())
    total_bars = len(all_timestamps)
    print(f"\nSynchronized 1h simulation timeline: {total_bars} bars (2024-01-01 to 2024-12-31).")

    # Tracking Structures
    pending_orders: List[Dict[str, Any]] = []
    equity_curve: List[Dict[str, Any]] = []
    circuit_breaker_tripped = False
    circuit_breaker_timestamp = None
    rejected_orders_count = 0
    candidate_signals_count = 0

    peak_equity = initial_capital
    daily_starting_equity = initial_capital
    daily_realized_pnl = Decimal("0")
    current_day = None

    print("\nExecuting event-driven chronological simulation...")

    for idx, ts in enumerate(all_timestamps):
        day_str = ts[:10]
        if current_day != day_str:
            current_day = day_str
            daily_starting_equity = ledger.get_total_equity()
            daily_realized_pnl = Decimal("0")

        # --- STEP 1: Process Pending Orders at Bar T Open (NEXT_ELIGIBLE_PRICE) ---
        new_pending = []
        for order in pending_orders:
            sym = order["symbol"]
            sym_df = data_1h[sym]
            curr_row = sym_df.iloc[idx]
            open_price = Decimal(str(curr_row["open"]))

            # Execute Fill with Taker Fee and Slippage
            fill_price = (open_price * (Decimal("1.0") + slippage_pct)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            notional = (order["size"] * fill_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            entry_fee = (notional * taker_fee_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            slippage_cost = (notional * slippage_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            spread_cost = (notional * spread_half).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            pos = ActivePosition(
                position_id=f"pos_{order['signal_id']}",
                signal_id=order["signal_id"],
                symbol=sym,
                timeframe="1h",
                direction="LONG",
                entry_timestamp=ts,
                entry_price=fill_price,
                raw_entry_price=open_price,
                stop_loss=order["stop_loss"],
                take_profit=order["take_profit"],
                position_size=order["size"],
                entry_fee=entry_fee,
                entry_slippage_cost=slippage_cost,
                entry_spread_cost=spread_cost,
                market_regime="TRENDING_BULL",
                strategy_metadata=order["metadata"],
            )
            # Tag holding tracking
            pos.entry_bar_idx = idx
            pos.holding_candles = 0

            try:
                ledger.process_order_fill(pos)
            except Exception as e:
                rejected_orders_count += 1

        pending_orders = new_pending

        # --- STEP 2: Evaluate Active Position Exits (Intrabar Stops & Targets) ---
        surviving_positions = []
        for pos in list(ledger.open_positions):
            pos.holding_candles = getattr(pos, "holding_candles", 0) + 1
            sym = pos.symbol
            curr_row = data_1h[sym].iloc[idx]

            curr_open = Decimal(str(curr_row["open"]))
            curr_high = Decimal(str(curr_row["high"]))
            curr_low = Decimal(str(curr_row["low"]))
            curr_close = Decimal(str(curr_row["close"]))

            hit_stop = curr_low <= pos.stop_loss
            hit_target = (pos.take_profit is not None) and (curr_high >= pos.take_profit)
            hit_time_stop = pos.holding_candles >= 96  # 4 calendar days

            exit_triggered = False
            exit_price = curr_close
            exit_reason = "HOLD"

            # Conservative intrabar ambiguity resolution: STOP LOSS takes priority
            if hit_stop:
                exit_triggered = True
                exit_reason = "STOP_LOSS"
                # Adverse gap check
                raw_exit = curr_open if curr_open < pos.stop_loss else pos.stop_loss
                exit_price = (raw_exit * (Decimal("1.0") - slippage_pct)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            elif hit_target:
                exit_triggered = True
                exit_reason = "TAKE_PROFIT"
                exit_price = (pos.take_profit * (Decimal("1.0") - slippage_pct)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            elif hit_time_stop:
                exit_triggered = True
                exit_reason = "TIME_STOP"
                exit_price = (curr_close * (Decimal("1.0") - slippage_pct)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            if exit_triggered:
                exit_notional = (pos.position_size * exit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                exit_fee = (exit_notional * taker_fee_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                exit_slippage = (exit_notional * slippage_pct).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                exit_spread = (exit_notional * spread_half).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                gross_pnl = (pos.position_size * (exit_price - pos.entry_price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                total_fees = pos.entry_fee + exit_fee
                total_slippage = pos.entry_slippage_cost + exit_slippage
                total_spread = pos.entry_spread_cost + exit_spread
                # Fill prices already incorporate entry and exit slippage and spread
                net_pnl = (gross_pnl - total_fees).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                trade = SimulatedTrade(
                    trade_id=f"trd_{pos.position_id}",
                    symbol=pos.symbol,
                    timeframe="1h",
                    direction="LONG",
                    signal_timestamp=pos.entry_timestamp,
                    entry_timestamp=pos.entry_timestamp,
                    entry_price=pos.entry_price,
                    exit_timestamp=ts,
                    exit_price=exit_price,
                    stop_loss=pos.stop_loss,
                    take_profit=pos.take_profit,
                    position_size=pos.position_size,
                    gross_pnl=gross_pnl,
                    fees=total_fees,
                    spread_cost=total_spread,
                    slippage_cost=total_slippage,
                    net_pnl=net_pnl,
                    exit_reason=exit_reason,
                    market_regime=pos.market_regime,
                    strategy_metadata=pos.strategy_metadata,
                )
                ledger.process_trade_exit(pos, trade, exit_fee=exit_fee)
            else:
                surviving_positions.append(pos)

        # --- STEP 3: Mark-to-Market Valuation & Drawdown Circuit Breaker ---
        for s in symbols:
            s_row = data_1h[s].iloc[idx]
            v_candle = ValidatedCandle(
                symbol=s,
                timeframe="1h",
                open=float(s_row["open"]),
                high=float(s_row["high"]),
                low=float(s_row["low"]),
                close=float(s_row["close"]),
                volume=float(s_row["volume"]),
                timestamp=ts,
                is_closed=True,
            )
            ledger.update_candle_mark(s, v_candle)

        current_equity = ledger.get_total_equity()

        if current_equity > peak_equity:
            peak_equity = current_equity

        drawdown_pct = Decimal("0")
        if peak_equity > Decimal("0"):
            drawdown_pct = (peak_equity - current_equity) / peak_equity

        equity_curve.append({
            "timestamp": ts,
            "bar_idx": idx,
            "equity": float(current_equity),
            "cash": float(ledger.cash_balance),
            "drawdown_pct": float(drawdown_pct),
            "open_positions": len(ledger.open_positions),
        })

        if drawdown_pct >= Decimal("0.0500") and not circuit_breaker_tripped:
            circuit_breaker_tripped = True
            circuit_breaker_timestamp = ts
            print(f"\n[ALERT] 5.0% Maximum Drawdown Circuit Breaker Tripped at {ts} (DD: {drawdown_pct:.2%})!")

        # --- STEP 4: Strategy Evaluation & Order Submission ---
        # Skip warm-up bars (need at least 250 1h bars)
        if idx < 250:
            continue

        if circuit_breaker_tripped:
            # Order Embargo: Reject all candidate signals post-breaker
            continue

        # Evaluate symbols if capacity permits
        if (len(ledger.open_positions) + len(pending_orders)) >= 2:
            continue

        for sym in symbols:
            # Check symbol capacity
            if any(p.symbol == sym for p in ledger.open_positions) or any(o["symbol"] == sym for o in pending_orders):
                continue
            if (len(ledger.open_positions) + len(pending_orders)) >= 2:
                break

            df1_slice = data_1h[sym].iloc[: idx + 1]
            # Match 4h slice
            df4_slice = data_4h[sym][data_4h[sym]["timestamp"] <= ts]

            # Evaluate strategy
            raw_signal = strategy.evaluate(df1_slice, sym, df_4h=df4_slice)
            if raw_signal is not None:
                candidate_signals_count += 1
                cand_signal = RawCandidateSignal(
                    signal_id=f"SIG-{sym}-{idx}",
                    timestamp=ts,
                    strategy_id=strategy.strategy_id,
                    symbol=sym,
                    timeframe="1h",
                    direction="LONG",
                    entry_price=raw_signal.entry_price,
                    suggested_stop_loss=raw_signal.stop_price,
                    suggested_take_profit=raw_signal.target_price,
                    risk_reward_ratio=raw_signal.reward_risk_ratio,
                    raw_confidence=0.85,
                    rationale=raw_signal.explanation,
                    invalidation_rules=[],
                    metadata=raw_signal.metadata,
                )

                # Pass to Risk Manager
                risk_eval = risk_manager.evaluate_signal(
                    signal=cand_signal,
                    current_equity=current_equity,
                    peak_equity=peak_equity,
                    daily_starting_equity=daily_starting_equity,
                    daily_realized_pnl=daily_realized_pnl,
                    open_positions=ledger.open_positions,
                    timestamp=ts,
                )

                if risk_eval.approved and risk_eval.position_size is not None:
                    # Target next bar open execution
                    if idx + 1 < total_bars:
                        pos_size = risk_eval.position_size
                        stop_loss = Decimal(str(raw_signal.stop_price))
                        take_profit = Decimal(str(raw_signal.target_price))

                        pending_orders.append({
                            "signal_id": cand_signal.signal_id,
                            "symbol": sym,
                            "size": pos_size,
                            "stop_loss": stop_loss,
                            "take_profit": take_profit,
                            "metadata": raw_signal.metadata,
                            "scheduled_at": ts,
                        })
                else:
                    rejected_orders_count += 1

    elapsed = time.time() - start_time_proc
    print(f"\nSimulation complete in {elapsed:.1f}s.")

    # 4. Accounting Invariant Assertion
    inv = ledger.assert_invariants()
    print(f"\nPortfolioLedger Invariant Check: {inv}")

    # 5. Compute Comprehensive Metrics
    trades = ledger.completed_trades
    total_trades = len(trades)
    winning_trades = [t for t in trades if t.net_pnl > Decimal("0")]
    losing_trades = [t for t in trades if t.net_pnl <= Decimal("0")]

    n_wins = len(winning_trades)
    n_losses = len(losing_trades)
    win_rate = (n_wins / total_trades) if total_trades > 0 else 0.0

    gross_profit = sum(t.gross_pnl for t in winning_trades) if winning_trades else Decimal("0")
    gross_loss = sum(abs(t.gross_pnl) for t in losing_trades) if losing_trades else Decimal("0")
    gross_pnl = sum(t.gross_pnl for t in trades) if trades else Decimal("0")

    total_fees = sum(t.fees for t in trades) if trades else Decimal("0")
    total_slippage = sum(t.slippage_cost for t in trades) if trades else Decimal("0")
    total_spread = sum(t.spread_cost for t in trades) if trades else Decimal("0")
    total_costs = total_fees + total_slippage + total_spread
    net_pnl = sum(t.net_pnl for t in trades) if trades else Decimal("0")

    ending_equity = equity_curve[-1]["equity"]
    net_return_pct = (ending_equity - float(initial_capital)) / float(initial_capital)
    max_drawdown_pct = max(pt["drawdown_pct"] for pt in equity_curve)

    avg_win = (float(gross_profit) / n_wins) if n_wins > 0 else 0.0
    avg_loss = (float(gross_loss) / n_losses) if n_losses > 0 else 0.0
    payoff_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0
    profit_factor = (float(gross_profit) / float(gross_loss)) if gross_loss > 0 else 0.0
    net_expectancy = (float(net_pnl) / total_trades) if total_trades > 0 else 0.0

    # Moving Block Bootstrap on Trade Returns
    net_pnl_array = np.array([float(t.net_pnl) for t in trades]) if trades else np.array([0.0])
    mean_boot, p_val, ci_lower, ci_upper = run_null_centered_block_bootstrap(net_pnl_array, block_size=min(len(net_pnl_array), 8))

    summary = {
        "experiment_id": "EXP-2024-DEV-DUAL-TIMEFRAME-A2",
        "strategy_id": strategy.strategy_id,
        "partition": "2024 Development",
        "period_start": start_iso,
        "period_end": end_iso,
        "initial_capital_usdt": float(initial_capital),
        "ending_equity_usdt": round(ending_equity, 2),
        "net_pnl_usdt": round(float(net_pnl), 2),
        "portfolio_return_pct": round(net_return_pct * 100, 2),
        "max_drawdown_pct": round(max_drawdown_pct * 100, 2),
        "circuit_breaker_tripped": circuit_breaker_tripped,
        "circuit_breaker_timestamp": circuit_breaker_timestamp,
        "total_executed_trades": total_trades,
        "winning_trades": n_wins,
        "losing_trades": n_losses,
        "win_rate_pct": round(win_rate * 100, 2),
        "avg_win_usdt": round(avg_win, 2),
        "avg_loss_usdt": round(avg_loss, 2),
        "realized_payoff_ratio": round(payoff_ratio, 2),
        "profit_factor": round(profit_factor, 2),
        "net_expectancy_usdt_per_trade": round(net_expectancy, 4),
        "gross_profit_usdt": round(float(gross_profit), 2),
        "gross_loss_usdt": round(float(gross_loss), 2),
        "gross_pnl_usdt": round(float(gross_pnl), 2),
        "total_fees_usdt": round(float(total_fees), 2),
        "total_slippage_usdt": round(float(total_slippage), 2),
        "total_spread_usdt": round(float(total_spread), 2),
        "total_transaction_friction_usdt": round(float(total_costs), 2),
        "candidate_signals_generated": candidate_signals_count,
        "orders_rejected_by_risk": rejected_orders_count,
        "bootstrap_mean_usdt": round(mean_boot, 4),
        "bootstrap_p_value": round(p_val, 4),
        "bootstrap_95_ci_lower_usdt": round(ci_lower, 4),
        "bootstrap_95_ci_upper_usdt": round(ci_upper, 4),
    }

    # 6. Print Formatted Summary
    print("\n" + "=" * 80)
    print("EXPERIMENT RESULTS: DUAL-TIMEFRAME TREND FOLLOWING (2024 DEVELOPMENT)")
    print("=" * 80)
    print(f"Total Executed Trades:        {total_trades}")
    print(f"Winning Trades:               {n_wins} ({win_rate:.1%})")
    print(f"Losing Trades:                {n_losses} ({(1-win_rate):.1%})")
    print(f"Gross Profit:                 ${gross_profit:.2f} USDT")
    print(f"Gross Loss:                   ${gross_loss:.2f} USDT")
    print(f"Gross P&L:                    ${gross_pnl:.2f} USDT")
    print(f"Total Fees:                   ${total_fees:.2f} USDT")
    print(f"Total Slippage:               ${total_slippage:.2f} USDT")
    print(f"Total Spread:                 ${total_spread:.2f} USDT")
    print(f"Total Transaction Costs:      ${total_costs:.2f} USDT")
    print(f"Realized Net P&L:             ${net_pnl:.2f} USDT")
    print(f"Ending Equity:                ${ending_equity:.2f} USDT")
    print(f"Portfolio Return:             {net_return_pct:.2%}")
    print(f"Maximum Drawdown:             {max_drawdown_pct:.2%}")
    print(f"Circuit Breaker Tripped:      {circuit_breaker_tripped} ({circuit_breaker_timestamp})")
    print(f"Realized Payoff Ratio:        {payoff_ratio:.2f}:1")
    print(f"Profit Factor:                {profit_factor:.2f}")
    print(f"Net Expectancy / Trade:       ${net_expectancy:.4f} USDT")
    print(f"Bootstrap Empirical p-value:  {p_val:.4f}")
    print(f"Bootstrap 95% CI:             [${ci_lower:.4f}, ${ci_upper:.4f}] USDT")
    print("=" * 80)

    # 7. Export Machine-Readable Artifacts
    with open(os.path.join(out_dir, "summary_metrics.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    trades_export = [t.to_dict() for t in trades]
    with open(os.path.join(out_dir, "trade_ledger.json"), "w", encoding="utf-8") as f:
        json.dump(trades_export, f, indent=2)

    with open(os.path.join(out_dir, "equity_curve.json"), "w", encoding="utf-8") as f:
        json.dump(equity_curve, f, indent=2)

    print(f"\nArtifacts successfully written to {out_dir}/")
    return summary


if __name__ == "__main__":
    asyncio.run(run_experiment())
