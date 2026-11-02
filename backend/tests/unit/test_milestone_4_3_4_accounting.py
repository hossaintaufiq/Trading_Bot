"""
NEPTUNE Milestone 4.3.4 — Accounting Verification & Benchmark Consistency Test Suite

Validates:
1. Exact full-precision Decimal accounting identity.
2. Independent cent-rounding bounded discrepancy (max +/- $0.02 per trade).
3. Authoritative benchmark manifest structure, verification status, and file hashes.
4. Distinction between full-precision aggregate accounting, sum of rounded trade values,
   and display-rounded values.
5. Ledger integrity and persistence across all authoritative benchmark configurations.
"""
import os
import json
import hashlib
from decimal import Decimal, ROUND_HALF_UP
import pytest

from app.simulation.execution import PaperExecutionSimulator
from app.simulation.models import ActivePosition


def test_exact_full_precision_decimal_accounting_identity():
    """Verify that unquantized Decimal identity net == gross - fees - slippage - spread is bit-for-bit exact."""
    gross_raw = Decimal("123.456789")
    entry_fee_raw = Decimal("1.234567")
    exit_fee_raw = Decimal("1.456789")
    total_fees_raw = entry_fee_raw + exit_fee_raw
    slip_raw = Decimal("0.654321")
    spread_raw = Decimal("0.130864")

    net_raw = gross_raw - total_fees_raw - slip_raw - spread_raw
    assert net_raw == Decimal("123.456789") - Decimal("2.691356") - Decimal("0.654321") - Decimal("0.130864")
    assert net_raw == Decimal("119.980248")


def test_independent_cent_rounding_bounded_discrepancy():
    """Verify that independent rounding of 5 components produces at most +/- $0.02 variance on any trade."""
    sim = PaperExecutionSimulator(
        taker_fee_pct=Decimal("0.001"),
        maker_fee_pct=Decimal("0.001"),
        slippage_pct=Decimal("0.0005"),
        spread_bps=Decimal("2.0"),
    )
    pos = sim.simulate_entry(
        symbol="BTCUSDT",
        timeframe="15m",
        direction="LONG",
        raw_price=Decimal("65432.10"),
        position_size=Decimal("0.015432"),
        stop_loss=Decimal("64000.00"),
        take_profit=Decimal("68000.00"),
        signal_timestamp="2026-01-01T00:00:00Z",
        entry_timestamp="2026-01-01T00:15:00Z",
        market_regime="TRENDING_BULL",
        strategy_metadata={},
    )
    trade = sim._finalize_trade(
        position=pos,
        exit_price_raw=Decimal("66789.01"),
        exit_timestamp="2026-01-01T02:30:00Z",
        exit_reason="TRAILING_STOP",
    )

    # Reconstructed quantized components
    sum_quantized_components = trade.gross_pnl - trade.fees - trade.slippage_cost - trade.spread_cost
    discrepancy = abs(trade.net_pnl - sum_quantized_components)

    assert discrepancy <= Decimal("0.02"), (
        f"Trade rounding discrepancy {discrepancy} exceeds mathematical bound of $0.02"
    )


def test_accounting_three_tier_distinction():
    """Verify the 3 distinct accounting calculation tiers:
    1. Full-precision aggregate accounting (raw unquantized sums).
    2. Sum of individually rounded trade values (cents).
    3. Display-rounded aggregate values.
    """
    raw_pnls = [
        Decimal("10.004"), Decimal("20.004"), Decimal("30.004"),
        Decimal("40.004"), Decimal("50.004"), Decimal("60.004"),
    ]

    # Tier 1: Full-precision aggregate
    tier1_sum = sum(raw_pnls)  # 210.024
    assert tier1_sum == Decimal("210.024")

    # Tier 2: Sum of individually rounded values
    rounded_pnls = [p.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) for p in raw_pnls]
    # Each 10.004 quantizes to 10.00
    tier2_sum = sum(rounded_pnls)
    assert tier2_sum == Decimal("210.00")

    # Tier 3: Display-rounded aggregate
    tier3_from_tier1 = round(float(tier1_sum), 2)  # 210.02
    tier3_from_tier2 = round(float(tier2_sum), 2)  # 210.00

    assert tier3_from_tier1 == 210.02
    assert tier3_from_tier2 == 210.00
    assert abs(tier1_sum - tier2_sum) == Decimal("0.024")


def test_authoritative_manifest_file_and_schema():
    """Verify that benchmark_manifest.json exists, contains 12 authoritative runs, and valid SHA256 hashes."""
    manifest_path = "storage/exports/milestone_4_3_4/benchmark_manifest.json"
    assert os.path.exists(manifest_path), "Manifest file must exist in milestone_4_3_4"

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    assert len(manifest) == 12, "Manifest must contain exactly 12 authoritative benchmark runs"

    for record in manifest:
        assert record["verification_status"] == "VERIFIED_AUTHORITATIVE"
        assert record["source_commit"] == "a66fb17"
        assert record["exit_policy"] in ("BALANCED", "FIXED_BRACKET")
        assert len(record["symbols"]) == 3
        assert len(record["timeframes"]) == 3
        assert record["trade_count"] > 0
        assert os.path.exists(record["csv_ledger_path"]), f"Ledger missing: {record['csv_ledger_path']}"

        # Verify CSV sha256 hash
        h = hashlib.sha256()
        with open(record["csv_ledger_path"], "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        assert h.hexdigest() == record["csv_sha256"], f"SHA256 mismatch for {record['csv_ledger_path']}"


def test_accounting_reconciliation_bounded_aggregate_variance():
    """Verify that full_precision_accounting_reconciliation.csv confirms all 12 ledgers have bounded variance."""
    rec_path = "storage/exports/milestone_4_3_4/full_precision_accounting_reconciliation.csv"
    assert os.path.exists(rec_path), "Reconciliation CSV must exist"

    import pandas as pd
    df = pd.read_csv(rec_path)
    assert len(df) == 12

    for _, row in df.iterrows():
        assert abs(row["aggregate_rounding_difference"]) <= 0.20, (
            f"Aggregate rounding difference {row['aggregate_rounding_difference']} for {row['ledger_name']} exceeds $0.20"
        )
        assert row["max_single_trade_difference"] <= 0.02, (
            f"Single trade difference {row['max_single_trade_difference']} for {row['ledger_name']} exceeds $0.02"
        )

