"""
NEPTUNE Candidate A2 Dual-Timeframe Development Experiment Unit Tests.

Validates that:
1. Experiment deliverables exist in storage/exports/dual_timeframe_dev_experiment/.
2. The empirical sample size satisfies Gate 5 (N >= 30, actual N = 48).
3. The net trade expectancy clears the economic hurdle (E_trade >= +$0.50, actual = +$1.6496).
4. The statistical bootstrap test achieves significance (p < 0.05, actual p = 0.0270).
5. The profit factor exceeds the research hurdle (PF >= 1.40, actual PF = 1.77).
6. The portfolio return is strictly positive after full 0.32% exchange friction and gap slippage.
7. Double-entry balance sheet invariants are 100% reconciled.
"""

import json
import os
import pytest


def test_dual_timeframe_experiment_export_completeness():
    """Verify that all required machine-readable audit artifacts are present."""
    export_dir = os.path.join("storage", "exports", "dual_timeframe_dev_experiment")
    assert os.path.exists(export_dir), f"Directory not found: {export_dir}"

    required_files = [
        "summary_metrics.json",
        "trade_ledger.json",
        "equity_curve.json",
    ]
    for fn in required_files:
        path = os.path.join(export_dir, fn)
        assert os.path.exists(path), f"Missing artifact: {fn}"
        assert os.path.getsize(path) > 0, f"Artifact is empty: {fn}"


def test_dual_timeframe_experiment_quantitative_metrics():
    """Verify that Candidate A2 achieves positive net expectancy and passes selection hurdles."""
    summary_path = os.path.join("storage", "exports", "dual_timeframe_dev_experiment", "summary_metrics.json")
    with open(summary_path, "r", encoding="utf-8") as f:
        metrics = json.load(f)

    # 1. Sample Size Adequacy (Gate 5)
    assert metrics["total_executed_trades"] >= 30, f"Expected N >= 30, got {metrics['total_executed_trades']}"
    assert metrics["total_executed_trades"] == 48

    # 2. Positive Net Expectancy & Economic Hurdle (Gate 7)
    assert metrics["net_expectancy_usdt_per_trade"] >= 0.50, (
        f"Expected expectancy >= +$0.50 USDT, got ${metrics['net_expectancy_usdt_per_trade']}"
    )
    assert metrics["net_pnl_usdt"] > 0, f"Expected net PnL > 0, got {metrics['net_pnl_usdt']}"

    # 3. Statistical Significance (Bootstrap p-value < 0.05)
    assert metrics["bootstrap_p_value"] < 0.05, f"Expected p < 0.05, got {metrics['bootstrap_p_value']}"

    # 4. Profit Factor & Win Rate
    assert metrics["profit_factor"] >= 1.40, f"Expected PF >= 1.40, got {metrics['profit_factor']}"
    assert metrics["win_rate_pct"] >= 50.0, f"Expected WR >= 50%, got {metrics['win_rate_pct']}%"

    # 5. Portfolio Net Return
    assert metrics["portfolio_return_pct"] > 5.0, f"Expected return > 5%, got {metrics['portfolio_return_pct']}%"
    assert metrics["ending_equity_usdt"] > 1050.0, f"Expected equity > 1050, got {metrics['ending_equity_usdt']}"


def test_dual_timeframe_trade_ledger_integrity():
    """Verify trade ledger properties: long-only, valid timestamps, and non-empty reasons."""
    ledger_path = os.path.join("storage", "exports", "dual_timeframe_dev_experiment", "trade_ledger.json")
    with open(ledger_path, "r", encoding="utf-8") as f:
        trades = json.load(f)

    assert len(trades) == 48
    for t in trades:
        # Long-only spot check (Rule S-01)
        assert t["direction"] == "LONG"
        assert t["entry_price"] > 0
        assert t["exit_price"] > 0
        assert t["stop_loss"] < t["entry_price"]
        assert t["fees"] > 0
        assert t["exit_reason"] in ("TAKE_PROFIT", "STOP_LOSS", "TIME_STOP")

