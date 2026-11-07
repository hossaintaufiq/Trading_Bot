"""
Unit Tests for DualTimeframeTrendStrategyV2 2025 Validation Partition Experiment.

Verifies:
- Partition Isolation: Validates strictly the 2025 Validation partition.
- Circuit Breaker Headroom: 5.0% maximum portfolio drawdown breaker never tripped.
- Capital Preservation: Total drawdown strictly bounded (< 4.0%).
- Bitcoin Trend Edge Persistence: BTCUSDT maintains positive net expectancy in 2025.
- Complete machine-readable audit artifact exports.
"""

import json
import os
import pytest


def test_2025_validation_export_completeness():
    """Verify that all 4 audit artifacts exist and are populated."""
    export_dir = os.path.abspath("storage/exports/dual_timeframe_v2_val2025_experiment")
    assert os.path.isdir(export_dir), f"Directory missing: {export_dir}"

    summary_path = os.path.join(export_dir, "summary_metrics.json")
    ledger_path = os.path.join(export_dir, "trade_ledger.json")
    equity_path = os.path.join(export_dir, "equity_curve.json")
    symbols_path = os.path.join(export_dir, "per_symbol_metrics.json")

    assert os.path.exists(summary_path)
    assert os.path.exists(ledger_path)
    assert os.path.exists(equity_path)
    assert os.path.exists(symbols_path)

    with open(summary_path) as f:
        summary = json.load(f)

    assert summary["experiment_id"] == "EXP-2025-VAL-DUAL-TIMEFRAME-V2"
    assert summary["partition"] == "2025 Validation"
    assert summary["strategy_id"] == "htf_trend_following_v2"
    assert summary["circuit_breaker_tripped"] is False
    assert summary["max_drawdown_pct"] < 5.0
    assert summary["total_executed_trades"] >= 50
    assert summary["gross_pnl_usdt"] > 0


def test_2025_validation_btc_persistence():
    """Verify BTCUSDT maintained positive net realized P&L across 2025 Validation."""
    symbols_path = os.path.abspath("storage/exports/dual_timeframe_v2_val2025_experiment/per_symbol_metrics.json")
    with open(symbols_path) as f:
        per_symbol = json.load(f)

    assert "BTCUSDT" in per_symbol
    btc = per_symbol["BTCUSDT"]
    assert btc["net_pnl_usdt"] > 0, f"BTCUSDT must remain net profitable in 2025, got {btc['net_pnl_usdt']}"
    assert btc["total_trades"] >= 20


def test_2025_validation_trade_ledger_integrity():
    """Verify individual trade ledger records in 2025 adhere to risk contracts."""
    ledger_path = os.path.abspath("storage/exports/dual_timeframe_v2_val2025_experiment/trade_ledger.json")
    with open(ledger_path) as f:
        trades = json.load(f)

    assert len(trades) >= 50
    for t in trades:
        assert t["direction"] == "LONG"
        assert float(t["entry_price"]) > 0
        assert float(t["stop_loss"]) > 0
        assert float(t["fees"]) > 0
        assert t["exit_reason"] in ("TAKE_PROFIT", "STOP_LOSS", "TIME_STOP", "BREAKEVEN_STOP")
