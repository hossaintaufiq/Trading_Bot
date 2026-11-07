"""
NEPTUNE Dual-Timeframe Strategy V2 — 2026 Out-of-Sample (OOS) Partition Experiment
(`run_dual_timeframe_v2_oos2026_experiment.py`)

Mission:
Evaluate Candidate A2-V2 (`DualTimeframeTrendStrategyV2` / `htf_trend_following_v2` / `SHR-001-V2` / ADR-036)
across the 2026 Out-of-Sample Partition under realistic execution costs, strict risk controls, and double-entry accounting.
"""

import asyncio
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
from app.strategies.dual_timeframe_trend_v2 import DualTimeframeConfigV2, DualTimeframeTrendStrategyV2


def run_null_centered_block_bootstrap(
    trade_pnls: np.ndarray,
    n_resamples: int = 2000,
    block_size: int = 5,
    seed: int = 42,
) -> Tuple[float, float, float, float]:
    """
    Moving Block Bootstrap to compute empirical p-value and 95% confidence interval.
    """
    if len(trade_pnls) < 2:
        return 0.0, 1.0, 0.0, 0.0

    rng = np.random.default_rng(seed)
    n = len(trade_pnls)
    actual_mean = float(np.mean(trade_pnls))

    # Center under null hypothesis H0: mu = 0
    centered = trade_pnls - actual_mean

    n_blocks = int(np.ceil(n / block_size))
    boot_means = np.empty(n_resamples)
    boot_centered_means = np.empty(n_resamples)

    for i in range(n_resamples):
        indices = rng.integers(0, max(1, n - block_size + 1), size=n_blocks)
        sample = np.concatenate([trade_pnls[idx : idx + block_size] for idx in indices])[:n]
        sample_centered = np.concatenate([centered[idx : idx + block_size] for idx in indices])[:n]

        boot_means[i] = np.mean(sample)
        boot_centered_means[i] = np.mean(sample_centered)

    p_value = float(np.mean(boot_centered_means >= actual_mean))
    ci_lower = float(np.percentile(boot_means, 2.5))
    ci_upper = float(np.percentile(boot_means, 97.5))

    return actual_mean, p_value, ci_lower, ci_upper


async def run_dual_timeframe_v2_oos2026_experiment(
    universe: Optional[List[str]] = None,
    btc_priority: bool = False,
    export_subfolder: str = "dual_timeframe_v2_oos2026_experiment"
) -> Dict[str, Any]:
    symbols = universe or ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    mode_desc = f"Universe: {','.join(symbols)} | BTC-Priority: {btc_priority}"
    print("=" * 80)
    print(f"NEPTUNE DUAL-TIMEFRAME STRATEGY V2 — 2026 OOS EXPERIMENT ({mode_desc})")
    print("=" * 80)

    start_iso = "2026-01-01T00:00:00Z"
    end_iso = "2026-11-01T23:00:00Z"

    # 1. Setup Execution & Risk Constraints
    initial_capital = Decimal("1000.00")
    taker_fee_pct = Decimal("0.001")     # 0.10% (Binance spot taker)
    slippage_pct = Decimal("0.0005")    # 0.05%
    spread_half = Decimal("0.0001")     # 0.01% (half-spread)

    ledger = PortfolioLedger(initial_capital=initial_capital, taker_fee_pct=taker_fee_pct)

    risk_manager = RiskManager(
        max_concurrent_positions=2,
        risk_per_trade_pct=Decimal("0.005"),  # 0.5% base risk
        daily_loss_limit_pct=Decimal("0.02"),  # 2.0%
        max_drawdown_pct=Decimal("0.05"),      # 5.0%
        min_reward_risk_ratio=Decimal("1.5"),
    )

    # Frozen configuration identical to ADR-036
    strategy_config = DualTimeframeConfigV2(
        fast_ema_4h=50,
        slow_ema_4h=200,
        min_adx_4h=24.0,
        adx_period_4h=14,
        fast_ema_1h=21,
        slow_ema_1h=50,
        atr_period_1h=14,
        atr_stop_multiplier=2.0,
        min_reward_risk_ratio=2.5,
        swing_pivot_lookback_1h=5,
        max_holding_candles_1h=96,
        breakeven_trigger_r=1.5,
        breakeven_buffer_pct=0.0035,
        symbol_cooldown_stops=2,
        symbol_cooldown_hours=168,
        cppi_dd_threshold=0.048,
        cppi_min_risk_multiplier=0.25,
    )

    strategy = DualTimeframeTrendStrategyV2(strategy_config)
    repo = ParquetMarketDataRepository()

    print("\nLoading historical market datasets for 2026 Out-of-Sample partition...")
    data_1h: Dict[str, pd.DataFrame] = {}
    data_4h: Dict[str, pd.DataFrame] = {}

    for sym in symbols:
        df1 = await repo.load_candles(sym, "1h")
        df4 = await repo.load_candles(sym, "4h")

        df1["timestamp"] = pd.to_datetime(df1["timestamp"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        df4["timestamp"] = pd.to_datetime(df4["timestamp"], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        df1_val = df1[(df1["timestamp"] >= start_iso) & (df1["timestamp"] <= end_iso)].sort_values("timestamp").reset_index(drop=True)
        df4_val = df4[(df4["timestamp"] >= start_iso) & (df4["timestamp"] <= end_iso)].sort_values("timestamp").reset_index(drop=True)

        df1_val["is_closed"] = True
        df4_val["is_closed"] = True

        data_1h[sym] = df1_val
        data_4h[sym] = df4_val
        print(f"  {sym}: Loaded {len(df1_val)} 1h candles, {len(df4_val)} 4h candles.")

    # 3. Synchronize Timeline
    ref_sym = symbols[0]
    all_timestamps = sorted(data_1h[ref_sym]["timestamp"].tolist())
    total_bars = len(all_timestamps)
    print(f"\nSynchronized 1h simulation timeline: {total_bars} bars (2026-01-01 to 2026-11-01).")

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

    symbol_consecutive_stops: Dict[str, int] = {s: 0 for s in symbols}
    symbol_cooldown_until: Dict[str, Optional[int]] = {s: None for s in symbols}

    start_time_proc = time.time()
    print("\nExecuting event-driven chronological simulation across 2026...")

    for idx, ts in enumerate(all_timestamps):
        day_str = ts[:10]
        if current_day != day_str:
            current_day = day_str
            daily_starting_equity = ledger.get_total_equity()
            daily_realized_pnl = Decimal("0")

        # --- STEP 1: Process Pending Orders at Bar T Open ---
        new_pending = []
        for order in pending_orders:
            sym = order["symbol"]
            sym_df = data_1h[sym]
            curr_row = sym_df.iloc[idx]
            open_price = Decimal(str(curr_row["open"]))

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
            pos.entry_bar_idx = idx
            pos.holding_candles = 0
            pos.highest_high = open_price
            pos.risk_r = fill_price - order["stop_loss"]
            pos.is_breakeven = False

            try:
                ledger.process_order_fill(pos)
            except Exception:
                rejected_orders_count += 1

        pending_orders = new_pending

        # --- STEP 2: Evaluate Active Position Exits & Breakeven Ratchet ---
        surviving_positions = []
        for pos in list(ledger.open_positions):
            pos.holding_candles = getattr(pos, "holding_candles", 0) + 1
            sym = pos.symbol
            curr_row = data_1h[sym].iloc[idx]

            curr_open = Decimal(str(curr_row["open"]))
            curr_high = Decimal(str(curr_row["high"]))
            curr_low = Decimal(str(curr_row["low"]))
            curr_close = Decimal(str(curr_row["close"]))

            if not hasattr(pos, "highest_high"):
                pos.highest_high = pos.entry_price
            if curr_high > pos.highest_high:
                pos.highest_high = curr_high

            risk_r = getattr(pos, "risk_r", pos.entry_price - pos.stop_loss)
            if risk_r <= Decimal("0"):
                risk_r = pos.entry_price * Decimal("0.01")

            gain_r = (curr_high - pos.entry_price) / risk_r
            if gain_r >= Decimal(str(strategy_config.breakeven_trigger_r)) and not getattr(pos, "is_breakeven", False):
                be_factor = Decimal("1.0") + Decimal(str(strategy_config.breakeven_buffer_pct))
                new_stop = (pos.entry_price * be_factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                if new_stop > pos.stop_loss:
                    pos.stop_loss = new_stop
                    pos.is_breakeven = True

            hit_stop = curr_low <= pos.stop_loss
            hit_target = (pos.take_profit is not None) and (curr_high >= pos.take_profit)
            hit_time_stop = pos.holding_candles >= strategy_config.max_holding_candles_1h

            exit_triggered = False
            exit_price = curr_close
            exit_reason = "HOLD"

            if hit_stop:
                exit_triggered = True
                if getattr(pos, "is_breakeven", False) and pos.stop_loss >= pos.entry_price:
                    exit_reason = "BREAKEVEN_STOP"
                else:
                    exit_reason = "STOP_LOSS"
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
                net_pnl = (gross_pnl - total_fees).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

                if exit_reason == "STOP_LOSS":
                    symbol_consecutive_stops[sym] += 1
                    if symbol_consecutive_stops[sym] >= strategy_config.symbol_cooldown_stops:
                        symbol_cooldown_until[sym] = idx + strategy_config.symbol_cooldown_hours
                else:
                    symbol_consecutive_stops[sym] = 0

                trade = SimulatedTrade(
                    trade_id=f"trd_oos_{pos.position_id}",
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

        # --- STEP 4: Strategy Evaluation, Risk Scaling & Order Submission ---
        if idx < 250:
            continue

        if circuit_breaker_tripped:
            continue

        if (len(ledger.open_positions) + len(pending_orders)) >= 2:
            continue

        eval_symbols = list(symbols)
        if btc_priority:
            eval_symbols.sort(key=lambda s: 0 if s == "BTCUSDT" else 1)

        for sym in eval_symbols:
            if any(p.symbol == sym for p in ledger.open_positions) or any(o["symbol"] == sym for o in pending_orders):
                continue
            if (len(ledger.open_positions) + len(pending_orders)) >= 2:
                break

            # Check Symbol Cooldown
            if symbol_cooldown_until[sym] is not None:
                if idx < symbol_cooldown_until[sym]:
                    continue
                else:
                    symbol_cooldown_until[sym] = None

            df1_slice = data_1h[sym].iloc[: idx + 1]
            df4_slice = data_4h[sym][data_4h[sym]["timestamp"] <= ts]

            raw_signal = strategy.evaluate(df1_slice, sym, df_4h=df4_slice)
            if raw_signal is not None:
                candidate_signals_count += 1

                # CPPI Adaptive Risk Sizing
                dd_thresh = Decimal(str(strategy_config.cppi_dd_threshold))
                min_mult = Decimal(str(strategy_config.cppi_min_risk_multiplier))
                cushion = max(min_mult, (dd_thresh - drawdown_pct) / dd_thresh)
                scaled_risk = (Decimal("0.005") * cushion).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                risk_manager.risk_per_trade_pct = scaled_risk

                cand_signal = RawCandidateSignal(
                    signal_id=f"SIG-OOS-{sym}-{idx}",
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
                    if idx + 1 < total_bars:
                        pending_orders.append({
                            "signal_id": cand_signal.signal_id,
                            "symbol": sym,
                            "size": risk_eval.position_size,
                            "stop_loss": Decimal(str(raw_signal.stop_price)),
                            "take_profit": Decimal(str(raw_signal.target_price)),
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

    net_pnl_array = np.array([float(t.net_pnl) for t in trades]) if trades else np.array([0.0])
    mean_boot, p_val, ci_lower, ci_upper = run_null_centered_block_bootstrap(net_pnl_array, block_size=min(len(net_pnl_array), 8))

    per_symbol: Dict[str, Any] = {}
    for s in symbols:
        s_trades = [t for t in trades if t.symbol == s]
        s_wins = [t for t in s_trades if t.net_pnl > Decimal("0")]
        s_losses = [t for t in s_trades if t.net_pnl <= Decimal("0")]
        s_gross = sum((t.gross_pnl for t in s_trades), Decimal("0"))
        s_fees = sum((t.fees for t in s_trades), Decimal("0"))
        s_net = sum((t.net_pnl for t in s_trades), Decimal("0"))
        s_wr = (len(s_wins) / len(s_trades)) if s_trades else 0.0
        per_symbol[s] = {
            "total_trades": len(s_trades),
            "winning_trades": len(s_wins),
            "losing_trades": len(s_losses),
            "win_rate_pct": round(s_wr * 100, 2),
            "gross_pnl_usdt": round(float(s_gross), 2),
            "fees_usdt": round(float(s_fees), 2),
            "net_pnl_usdt": round(float(s_net), 2),
        }

    summary = {
        "experiment_id": f"EXP-2026-OOS-{export_subfolder.upper()}",
        "strategy_id": strategy.strategy_id,
        "partition": "2026 Out-of-Sample",
        "period_start": start_iso,
        "period_end": end_iso,
        "symbols": symbols,
        "btc_priority": btc_priority,
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
    print(f"EXPERIMENT RESULTS: DUAL-TIMEFRAME TREND FOLLOWING V2 (2026 OOS - {mode_desc})")
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
    print(f"Profit Factor:                {profit_factor:.2f}")
    print(f"Payoff Ratio (Win/Loss):      {payoff_ratio:.2f}")
    print(f"Net Expectancy per Trade:     ${net_expectancy:.4f} USDT")
    print(f"Bootstrap Empirical p-value:  {p_val:.4f} (Null: Expectancy <= 0)")
    print(f"Bootstrap 95% CI:             [${ci_lower:.4f}, ${ci_upper:.4f}] USDT")

    print("\nPer-Symbol Breakdown:")
    for s, m in per_symbol.items():
        print(f"  {s}: Net P&L = ${m['net_pnl_usdt']:+.2f} USDT | Trades = {m['total_trades']} | Win Rate = {m['win_rate_pct']:.1f}%")

    export_dir = os.path.abspath(f"storage/exports/{export_subfolder}")
    os.makedirs(export_dir, exist_ok=True)

    with open(os.path.join(export_dir, "summary_metrics.json"), "w") as f:
        json.dump(summary, f, indent=2)

    with open(os.path.join(export_dir, "trade_ledger.json"), "w") as f:
        json.dump([t.model_dump() for t in trades], f, indent=2, default=str)

    with open(os.path.join(export_dir, "equity_curve.json"), "w") as f:
        json.dump(equity_curve, f, indent=2)

    with open(os.path.join(export_dir, "per_symbol_metrics.json"), "w") as f:
        json.dump(per_symbol, f, indent=2)

    print(f"\nAll artifacts exported successfully to:\n  {export_dir}")
    return summary


if __name__ == "__main__":
    asyncio.run(run_dual_timeframe_v2_oos2026_experiment())
