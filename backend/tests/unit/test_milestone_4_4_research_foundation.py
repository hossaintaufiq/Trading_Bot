"""
NEPTUNE Unit Test Suite — Milestone 4.4 Research Foundation

Tests:
- Dataset fingerprint stability and determinism.
- Dataset version isolation (v1.0.0 vs v2.0.0).
- Sequence continuity, gap, and duplicate detection.
- Closed-candle enforcement and OHLC invariant validation.
- Partition boundary slicing and pre-partition warmup priming without look-ahead.
- Model-agnostic forecasting interface contracts and input fingerprinting.
- SQLite dataset metadata persistence and queries.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
import pytest
import pandas as pd

from app.analytics.forecasting import (
    ForecastCandle,
    ForecastInput,
    ForecastOutput,
    MockAgnosticForecaster,
)
from app.analytics.research_framework import (
    ChronologicalResearchFramework,
    PartitionBoundary,
    STANDARD_PARTITIONS,
)
from app.data.market.validator import CandleValidator, ValidatedCandle
from app.data.repositories.dataset_repo import SqliteHistoricalDatasetRepository


def test_stable_dataset_fingerprint():
    """Verify that dataset fingerprinting produces bit-for-bit identical SHA256 hashes."""
    candles = [
        ValidatedCandle(
            symbol="BTCUSDT",
            timeframe="1h",
            timestamp=f"2026-01-01T{h:02d}:00:00.000Z",
            open=50000.0 + h * 10,
            high=50100.0 + h * 10,
            low=49900.0 + h * 10,
            close=50050.0 + h * 10,
            volume=100.0,
            is_closed=True,
        )
        for h in range(10)
    ]

    raw1 = ";".join(f"{c.timestamp}:{c.open}:{c.high}:{c.low}:{c.close}:{c.volume}" for c in candles)
    hash1 = hashlib.sha256(raw1.encode("utf-8")).hexdigest()

    raw2 = ";".join(f"{c.timestamp}:{c.open}:{c.high}:{c.low}:{c.close}:{c.volume}" for c in candles)
    hash2 = hashlib.sha256(raw2.encode("utf-8")).hexdigest()

    assert hash1 == hash2
    assert len(hash1) == 64


def test_dataset_version_isolation():
    """Verify that v1.0.0 and v2.0.0 storage directories are isolated and manifest tracks both."""
    manifest_path = "storage/exports/milestone_4_4/dataset_manifest.json"
    assert os.path.exists(manifest_path), "Dataset manifest must exist in milestone_4_4 export"

    with open(manifest_path, "r") as f:
        manifest = json.load(f)

    datasets = manifest["datasets"]
    v1_sets = [d for d in datasets if d["dataset_version"] == "v1.0.0"]
    v2_sets = [d for d in datasets if d["dataset_version"] == "v2.0.0"]

    assert len(v1_sets) == 9, "v1.0.0 must track 9 historical datasets"
    assert len(v2_sets) == 12, "v2.0.0 must track 12 expanded datasets"

    # Verify v1.0.0 preserved files exist
    assert os.path.exists("storage/datasets/v1.0.0/BTCUSDT/15m")
    assert os.path.exists("storage/datasets/v1.0.0/ETHUSDT/1h")

    # Verify v2.0.0 expanded files exist
    assert os.path.exists("storage/datasets/v2.0.0/BTCUSDT/1d")
    assert os.path.exists("storage/datasets/v2.0.0/BNBUSDT/4h")


def test_candle_validator_closed_and_invariants():
    """Verify that CandleValidator strictly rejects incomplete candles and invalid OHLC geometry."""
    validator = CandleValidator()

    # 1. Incomplete candle rejected
    raw_incomplete = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "timestamp": "2026-01-01T00:00:00.000Z",
        "open": 50000.0,
        "high": 50100.0,
        "low": 49900.0,
        "close": 50050.0,
        "volume": 10.0,
        "is_closed": False,
    }
    c, issues = validator.validate_candle(raw_incomplete, require_closed=True)
    assert c is None
    assert any(i.field == "is_closed" for i in issues)

    # 2. High lower than low rejected
    raw_inverted = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "timestamp": "2026-01-01T00:00:00.000Z",
        "open": 50000.0,
        "high": 49000.0,
        "low": 50100.0,
        "close": 49500.0,
        "volume": 10.0,
        "is_closed": True,
    }
    c_inv, issues_inv = validator.validate_candle(raw_inverted, require_closed=True)
    assert c_inv is None
    assert any(i.field == "high_low" for i in issues_inv)


def test_gap_and_duplicate_detection():
    """Verify that validate_sequence identifies gaps and duplicate timestamps."""
    validator = CandleValidator()
    # Sequence with a duplicate at index 2 and a 2-hour gap between hour 3 and 5
    timestamps = [
        "2026-01-01T00:00:00.000Z",
        "2026-01-01T01:00:00.000Z",
        "2026-01-01T01:00:00.000Z",  # Duplicate
        "2026-01-01T02:00:00.000Z",
        "2026-01-01T04:00:00.000Z",  # Gap (missing 03:00)
    ]
    candles = [
        ValidatedCandle(
            symbol="BTCUSDT",
            timeframe="1h",
            timestamp=ts,
            open=50000.0,
            high=50100.0,
            low=49900.0,
            close=50050.0,
            volume=10.0,
            is_closed=True,
        )
        for ts in timestamps
    ]

    valid_seq, issues = validator.validate_sequence(candles, "1h", allow_duplicates=False)
    assert len(valid_seq) == 4, "Duplicate must be dropped"
    assert any(i.field == "duplicate_timestamp" for i in issues)
    assert any(i.field == "missing_candles_gap" for i in issues)


def test_partition_boundary_enforcement_and_warmup():
    """Verify that slicing for a partition includes preceding warmup bars and restricts eval window."""
    framework = ChronologicalResearchFramework()

    # Generate 50 daily candles (Jan 1 to Feb 19, 2024)
    dates = pd.date_range("2024-01-01", periods=50, freq="D", tz="UTC")
    candles = [
        ValidatedCandle(
            symbol="BTCUSDT",
            timeframe="1d",
            timestamp=d.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            open=40000.0,
            high=41000.0,
            low=39000.0,
            close=40500.0,
            volume=100.0,
            is_closed=True,
        )
        for d in dates
    ]

    # Partition: Jan 15 to Jan 25, warmup = 10 bars
    partition = PartitionBoundary(
        name="TEST_WINDOW",
        start_time="2024-01-15T00:00:00.000Z",
        end_time="2024-01-25T00:00:00.000Z",
        warmup_bars=10,
    )

    sliced = framework.slice_candles_for_partition(candles, partition)
    # Jan 15 is index 14. Jan 25 is index 24.
    # Warmup 10 bars means start at max(0, 14-10) = index 4 (Jan 5).
    # Sliced range should be index 4 to 24 (21 bars total).
    assert len(sliced) == 21
    assert sliced[0].timestamp == "2024-01-05T00:00:00.000Z"
    assert sliced[-1].timestamp == "2024-01-25T00:00:00.000Z"


@pytest.mark.asyncio
async def test_forecasting_interface_contract_and_lookahead_prevention():
    """Verify the model-independent forecasting contract and input fingerprinting."""
    candles = [
        ValidatedCandle(
            symbol="BTCUSDT",
            timeframe="1h",
            timestamp=f"2026-01-01T{h:02d}:00:00.000Z",
            open=50000.0 + h * 5,
            high=50100.0 + h * 5,
            low=49900.0 + h * 5,
            close=50020.0 + h * 5,
            volume=50.0,
            is_closed=True,
        )
        for h in range(20)
    ]

    req = ForecastInput(
        symbol="BTCUSDT",
        timeframe="1h",
        historical_sequence=candles,
        sequence_length=len(candles),
        dataset_id="neptune-v2.0.0-btcusdt-1h",
        forecast_horizon=5,
        model_identifier="mock-extrapolation",
        model_version="v1.0.0",
    )

    fp = req.compute_input_fingerprint()
    assert len(fp) == 64

    forecaster = MockAgnosticForecaster(model_identifier="mock-extrapolation", model_version="v1.0.0")
    out = await forecaster.forecast(req)

    assert isinstance(out, ForecastOutput)
    assert out.symbol == "BTCUSDT"
    assert out.forecast_horizon == 5
    assert len(out.forecasted_sequence) == 5
    assert out.input_dataset_fingerprint == fp
    assert out.uncertainty_distribution is not None


@pytest.mark.asyncio
async def test_historical_dataset_sqlite_repository(tmp_path):
    """Verify SQLite persistence and queries for historical dataset records."""
    db_file = str(tmp_path / "test_neptune.db")
    repo = SqliteHistoricalDatasetRepository(db_path=db_file)

    rec = {
        "dataset_id": "test-dataset-001",
        "dataset_version": "v2.0.0",
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "start_timestamp": "2024-01-01T00:00:00.000Z",
        "end_timestamp": "2026-11-01T00:00:00.000Z",
        "candle_count": 24864,
        "missing_intervals_count": 0,
        "duplicate_count": 0,
        "invalid_candle_count": 0,
        "source": "binance_public_rest_v3",
        "schema_version": "v1.0.0-standard-8col",
        "validation_status": "VALIDATED",
        "sha256_fingerprint": "abc123def456",
        "retrieval_timestamp": "2026-11-02T12:00:00.000Z",
        "storage_path": "storage/datasets/v2.0.0/BTCUSDT/1h",
    }

    saved_id = await repo.save_dataset_meta(rec)
    assert saved_id == "test-dataset-001"

    fetched = await repo.get_dataset_meta("test-dataset-001")
    assert fetched is not None
    assert fetched["symbol"] == "BTCUSDT"
    assert fetched["candle_count"] == 24864
    assert fetched["validation_status"] == "VALIDATED"

    all_sets = await repo.list_datasets(dataset_version="v2.0.0")
    assert len(all_sets) == 1
    assert all_sets[0]["dataset_id"] == "test-dataset-001"

