"""
Unit tests for Dual-Timeframe V2 2026 Out-of-Sample (OOS) Experiment
"""
import json
import os
import pytest


def test_2026_oos_export_completeness():
    export_dir = os.path.abspath("storage/exports/dual_timeframe_v2_oos2026_experiment")
    assert os.path.isdir(export_dir), f"Export dir {export_dir} does not exist"

    summary_file = os.path.join(export_dir, "summary_metrics.json")
    trade_file = os.path.join(export_dir, "trade_ledger.json")
    equity_file = os.path.join(export_dir, "equity_curve.json")
    per_symbol_file = os.path.join(export_dir, "per_symbol_metrics.json")

    for fpath in [summary_file, trade_file, equity_file, per_symbol_file]:
        assert os.path.isfile(fpath), f"File {fpath} does not exist"

    with open(summary_file) as f:
        summary = json.load(f)

    assert summary["partition"] == "2026 Out-of-Sample"
    assert summary["total_executed_trades"] > 0
    assert summary["initial_capital_usdt"] == 1000.0
    assert summary["max_drawdown_pct"] < 5.0
    assert summary["circuit_breaker_tripped"] is False


def test_2026_btc_only_export_and_drawdown():
    export_dir = os.path.abspath("storage/exports/oos2026_btc_only")
    assert os.path.isdir(export_dir), f"Export dir {export_dir} does not exist"

    summary_file = os.path.join(export_dir, "summary_metrics.json")
    assert os.path.isfile(summary_file)

    with open(summary_file) as f:
        summary = json.load(f)

    assert summary["max_drawdown_pct"] <= 2.5
    assert summary["circuit_breaker_tripped"] is False
    assert summary["gross_pnl_usdt"] > 0


def test_2026_trade_ledger_invariants():
    export_dir = os.path.abspath("storage/exports/dual_timeframe_v2_oos2026_experiment")
    trade_file = os.path.join(export_dir, "trade_ledger.json")

    with open(trade_file) as f:
        trades = json.load(f)

    assert len(trades) > 0
    for t in trades:
        assert float(t["entry_price"]) > 0
        assert float(t["exit_price"]) > 0
        assert float(t["position_size"]) > 0
        assert t["direction"] in ["LONG", "SHORT"]

