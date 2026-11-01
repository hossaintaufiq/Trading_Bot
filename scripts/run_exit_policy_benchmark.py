#!/usr/bin/env python3
"""
NEPTUNE — Milestone 4.2 Historical Strategy Evaluation & Exit Policy Benchmark CLI

Executes systematic, reproducible benchmark comparison across:
- Symbols: BTCUSDT, ETHUSDT, BNBUSDT
- Timeframes: 15m, 1h, 4h
- Policies: FIXED_BRACKET vs BALANCED

Outputs institutional-grade metrics, regime breakdowns, reversal analytics,
and out-of-sample degradation reports.
"""
import asyncio
import json
import os
import sys
from decimal import Decimal

# Ensure backend package is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.simulation.benchmark import ExitPolicyBenchmark, BenchmarkReport
from app.simulation.models import BacktestConfig


async def main():
    print("=" * 80)
    print("NEPTUNE — MILESTONE 4.2 HISTORICAL STRATEGY EVALUATION & EXIT BENCHMARK")
    print("=" * 80)

    symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    timeframes = ["15m", "1h", "4h"]

    config = BacktestConfig(
        strategy_id="trend_momentum_pullback_v1",
        symbols=symbols,
        timeframe="15m",
        initial_capital=Decimal("1000.0"),
        trailing_atr_multiplier=Decimal("2.0"),
        trailing_activation_threshold_r=Decimal("1.0"),
        taker_fee_pct=Decimal("0.001"),
        maker_fee_pct=Decimal("0.001"),
        slippage_pct=Decimal("0.0005"),
        spread_bps=Decimal("2.0"),
        save_to_db=True,
        save_to_parquet=True,
    )

    benchmark = ExitPolicyBenchmark(
        base_config=config,
        train_ratio=0.70,
        min_candles_required=100,
    )

    print("\nRunning benchmark across 9 symbol/timeframe pairs...")
    report = await benchmark.run_benchmark(
        symbols=symbols,
        timeframes=timeframes,
    )

    print("\n" + "=" * 80)
    print("BENCHMARK EXECUTION SUMMARY")
    print("=" * 80)
    print(f"Benchmark ID:     {report.benchmark_id}")
    print(f"Git Commit:       {report.git_commit}")
    print(f"Train / Test:     {int(report.train_ratio * 100)}% In-Sample / {int((1 - report.train_ratio) * 100)}% Out-of-Sample")
    print(f"Total Evaluated:  {report.aggregate_summary.get('total_evaluations', 0)}")
    print(f"Successful Pairs: {report.aggregate_summary.get('successful_evaluations', 0)}")
    print(f"Insufficient:     {report.aggregate_summary.get('insufficient_data_count', 0)}")
    print(f"Aggregate Fixed Net PnL:    ${report.aggregate_summary.get('aggregate_fixed_net_pnl', 0.0):.2f}")
    print(f"Aggregate Balanced Net PnL: ${report.aggregate_summary.get('aggregate_balanced_net_pnl', 0.0):.2f}")
    print(f"Aggregate PnL Delta:        ${report.aggregate_summary.get('aggregate_net_pnl_delta', 0.0):.2f}")

    print("\n" + "-" * 80)
    print(f"{'SYMBOL':<10} {'TF':<5} {'STATUS':<15} {'CANDLES':<8} {'FIXED TRD':<10} {'BAL TRD':<10} {'NET PNL FIX':<12} {'NET PNL BAL':<12} {'DELTA':<10}")
    print("-" * 80)

    for ev in report.evaluations:
        if ev.status == "SUCCESS" and ev.full_period:
            fp = ev.full_period
            fix_pnl = float(fp.fixed_metrics.net_profit)
            bal_pnl = float(fp.balanced_metrics.net_profit)
            delta_pnl = bal_pnl - fix_pnl
            print(f"{ev.symbol:<10} {ev.timeframe:<5} {ev.status:<15} {ev.total_candles:<8} {fp.fixed_trades_count:<10} {fp.balanced_trades_count:<10} ${fix_pnl:<11.2f} ${bal_pnl:<11.2f} ${delta_pnl:<9.2f}")
        else:
            print(f"{ev.symbol:<10} {ev.timeframe:<5} {ev.status:<15} {ev.total_candles:<8} {'-':<10} {'-':<10} {'-':<12} {'-':<12} {'-':<10}")

    print("\n" + "=" * 80)
    print("DETAILED METRIC COMPARISON (FIXED_BRACKET vs BALANCED)")
    print("=" * 80)

    for ev in report.evaluations:
        if ev.status != "SUCCESS" or not ev.full_period:
            continue
        fp = ev.full_period
        fm = fp.fixed_metrics
        bm = fp.balanced_metrics
        dm = fp.delta_metrics

        print(f"\n>>> {ev.symbol} [{ev.timeframe}] ({ev.dataset_start} -> {ev.dataset_end})")
        print(f"    {'Metric':<28} {'FIXED_BRACKET':<16} {'BALANCED':<16} {'DELTA':<16}")
        print("    " + "-" * 72)
        print(f"    {'Total Trades':<28} {fm.total_trades:<16} {bm.total_trades:<16} {dm['total_trades_delta']:<+16}")
        print(f"    {'Win Rate':<28} {fm.win_rate*100:<15.1f}% {bm.win_rate*100:<15.1f}% {dm['win_rate_delta']*100:<+15.1f}%")
        print(f"    {'Gross Profit':<28} ${float(fm.gross_profit):<15.2f} ${float(bm.gross_profit):<15.2f} ${dm['gross_profit_delta']:<+15.2f}")
        print(f"    {'Gross Loss':<28} ${float(fm.gross_loss):<15.2f} ${float(bm.gross_loss):<15.2f} ${dm['gross_loss_delta']:<+15.2f}")
        print(f"    {'Net P&L':<28} ${float(fm.net_profit):<15.2f} ${float(bm.net_profit):<15.2f} ${dm['net_pnl_delta']:<+15.2f}")
        print(f"    {'Net Expectancy/Trade':<28} ${float(fm.expectancy_per_trade):<15.2f} ${float(bm.expectancy_per_trade):<15.2f} ${dm['expectancy_delta']:<+15.2f}")
        print(f"    {'Profit Factor':<28} {fm.profit_factor:<16.2f} {bm.profit_factor:<16.2f} {dm['profit_factor_delta']:<+16.2f}")
        print(f"    {'Average Win':<28} ${float(fm.average_win):<15.2f} ${float(bm.average_win):<15.2f} -")
        print(f"    {'Average Loss':<28} ${float(fm.average_loss):<15.2f} ${float(bm.average_loss):<15.2f} -")
        print(f"    {'Max Drawdown %':<28} {fm.max_drawdown_pct:<15.2f}% {bm.max_drawdown_pct:<15.2f}% {dm['max_drawdown_pct_delta']:<+15.2f}%")
        print(f"    {'Max Drawdown $':<28} ${float(fm.max_drawdown_amount):<15.2f} ${float(bm.max_drawdown_amount):<15.2f} ${dm['max_drawdown_amount_delta']:<+15.2f}")
        print(f"    {'Sharpe Ratio':<28} {fm.sharpe_ratio:<16.2f} {bm.sharpe_ratio:<16.2f} {dm['sharpe_delta']:<+16.2f}")
        print(f"    {'Sortino Ratio':<28} {fm.sortino_ratio:<16.2f} {bm.sortino_ratio:<16.2f} {dm['sortino_delta']:<+16.2f}")
        print(f"    {'Max Consecutive Losses':<28} {fm.max_consecutive_losses:<16} {bm.max_consecutive_losses:<16} -")
        print(f"    {'Average MFE':<28} ${float(fm.average_mfe):<15.2f} ${float(bm.average_mfe):<15.2f} ${dm['average_mfe_delta']:<+15.2f}")
        print(f"    {'Average MAE':<28} ${float(fm.average_mae):<15.2f} ${float(bm.average_mae):<15.2f} ${dm['average_mae_delta']:<+15.2f}")
        print(f"    {'Avg Holding Duration':<28} {fm.average_holding_duration_seconds/3600:<15.1f}h {bm.average_holding_duration_seconds/3600:<15.1f}h {dm['holding_duration_seconds_delta']/3600:<+15.1f}h")
        print(f"    {'Total Fees':<28} ${float(fm.total_fees):<15.2f} ${float(bm.total_fees):<15.2f} ${dm['total_fees_delta']:<+15.2f}")
        print(f"    {'Total Spread':<28} ${float(fm.total_spread):<15.2f} ${float(bm.total_spread):<15.2f} ${dm['total_spread_delta']:<+15.2f}")
        print(f"    {'Total Slippage':<28} ${float(fm.total_slippage):<15.2f} ${float(bm.total_slippage):<15.2f} ${dm['total_slippage_delta']:<+15.2f}")

        # Exit reasons breakdown
        print("    Exit Reasons (Fixed):   ", {k: v["total_trades"] for k, v in fm.performance_by_exit_reason.items()})
        print("    Exit Reasons (Balanced):", {k: v["total_trades"] for k, v in bm.performance_by_exit_reason.items()})

        # Reversal analysis
        rm = ev.reversal_analysis
        if rm:
            print(f"    Reversal Analysis:       Detections={rm.get('total_reversal_detections', 0)}, Exits={rm.get('total_reversal_exits', 0)}, Superseded={rm.get('total_reversal_superseded', 0)}, Avg PnL=${rm.get('average_reversal_exit_pnl', 0.0):.2f}")
            if rm.get("performance_by_combination"):
                print("    Reversal Combinations:  ", rm["performance_by_combination"])

        # Out-of-sample breakdown
        if ev.in_sample and ev.out_of_sample:
            is_fix = float(ev.in_sample.fixed_metrics.net_profit)
            oos_fix = float(ev.out_of_sample.fixed_metrics.net_profit)
            is_bal = float(ev.in_sample.balanced_metrics.net_profit)
            oos_bal = float(ev.out_of_sample.balanced_metrics.net_profit)
            print(f"    In-Sample / OOS Split:   IS(70%) Fixed=${is_fix:.2f}, OOS(30%) Fixed=${oos_fix:.2f} (WFE={ev.walk_forward_efficiency_fixed:.2f}, Degr={ev.degradation_fixed_pct:.1f}%)")
            print(f"                             IS(70%) Bal=${is_bal:.2f}, OOS(30%) Bal=${oos_bal:.2f} (WFE={ev.walk_forward_efficiency_balanced:.2f}, Degr={ev.degradation_balanced_pct:.1f}%)")

    # Export report to JSON for permanent traceability
    export_dir = os.path.join("storage", "exports")
    os.makedirs(export_dir, exist_ok=True)
    export_path = os.path.join(export_dir, f"{report.benchmark_id}_benchmark.json")
    with open(export_path, "w") as f:
        json.dump(report.model_dump(mode="json"), f, indent=2)
    print(f"\nSaved full benchmark report artifact to: {export_path}")

    return report


if __name__ == "__main__":
    asyncio.run(main())

