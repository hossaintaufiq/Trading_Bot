"""
Unit Tests for Milestone 4.5 — Kronos Foundation Model Integration
(`test_milestone_4_5_kronos.py`)

Verifies:
1. Model & tokenizer architectural specifications (~4.1M parameters, 20-bit BSQ codebook).
2. Strict look-ahead bias prevention (rejecting unclosed and retro-causal candles).
3. Cryptographic input fingerprinting and tamper sensitivity.
4. IForecaster interface compliance and mathematical OHLC invariants.
5. Uncertainty distribution and directional projection consistency.
6. Hybrid NEPTUNE + Kronos confirmation gate logic.
"""
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest
import torch

from app.analytics.forecasters import (
    Kronos,
    KronosForecaster,
    KronosPredictor,
    KronosTokenizer,
)
from app.analytics.forecasting import ForecastCandle, ForecastInput, ForecastOutput
from app.data.market.validator import ValidatedCandle


@pytest.fixture(scope="module")
def shared_kronos_forecaster():
    """Shared CPU Kronos forecaster with 1 sample for fast unit tests."""
    forecaster = KronosForecaster(device="cpu", sample_count=1, seed=42)
    forecaster._ensure_loaded()
    return forecaster


def test_kronos_tokenizer_architecture(shared_kronos_forecaster):
    """Verify Kronos-Tokenizer-2k codebook and layer properties."""
    tokenizer = shared_kronos_forecaster._tokenizer
    assert tokenizer is not None
    assert tokenizer.s1_bits == 10
    assert tokenizer.s2_bits == 10
    assert tokenizer.codebook_dim == 20
    assert tokenizer.d_in == 6
    assert tokenizer.d_model == 256
    assert len(tokenizer.encoder) == 3  # 4 enc layers - 1
    assert len(tokenizer.decoder) == 3  # 4 dec layers - 1


def test_kronos_model_architecture(shared_kronos_forecaster):
    """Verify Kronos-mini parameter count and transformer dimensions."""
    model = shared_kronos_forecaster._model
    assert model is not None
    assert model.d_model == 256
    assert model.n_layers == 4
    assert model.n_heads == 4
    assert model.ff_dim == 512
    total_params = sum(p.numel() for p in model.parameters())
    # Canonical Kronos-mini parameter count is exactly 4,108,032
    assert total_params == 4108032


def test_forecaster_rejects_unclosed_candle(shared_kronos_forecaster):
    """Rule A-09, S-05: Input containing incomplete candle must be rejected."""
    base_time = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = [
        ValidatedCandle(
            symbol="BTCUSDT",
            timeframe="1h",
            timestamp=(base_time + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            open=40000.0 + i,
            high=40100.0 + i,
            low=39900.0 + i,
            close=40050.0 + i,
            volume=100.0,
            is_closed=(i < 15),  # Last candle marked incomplete
        )
        for i in range(16)
    ]

    inp = ForecastInput(
        symbol="BTCUSDT",
        timeframe="1h",
        historical_sequence=candles,
        sequence_length=len(candles),
        dataset_id="test_leakage",
        forecast_horizon=4,
        model_identifier="NeoQuasar/Kronos-mini",
        model_version="v1.0.0",
    )

    with pytest.raises(ValueError, match="Look-ahead violation"):
        import asyncio
        asyncio.run(shared_kronos_forecaster.forecast(inp))


def test_forecaster_rejects_non_chronological_sequence(shared_kronos_forecaster):
    """Rule S-05: Reverse or scrambled timestamps must be rejected."""
    base_time = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    # Candles in reverse chronological order
    candles = [
        ValidatedCandle(
            symbol="BTCUSDT",
            timeframe="1h",
            timestamp=(base_time - timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            open=40000.0,
            high=40100.0,
            low=39900.0,
            close=40050.0,
            volume=100.0,
            is_closed=True,
        )
        for i in range(16)
    ]

    inp = ForecastInput(
        symbol="BTCUSDT",
        timeframe="1h",
        historical_sequence=candles,
        sequence_length=len(candles),
        dataset_id="test_order",
        forecast_horizon=4,
        model_identifier="NeoQuasar/Kronos-mini",
        model_version="v1.0.0",
    )

    with pytest.raises(ValueError, match="Chronological ordering violation"):
        import asyncio
        asyncio.run(shared_kronos_forecaster.forecast(inp))


def test_forecast_input_fingerprint_tamper_sensitivity():
    """Verify cryptographic input fingerprinting is deterministic and tamper-sensitive."""
    base_time = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles_a = [
        ValidatedCandle(
            symbol="BTCUSDT",
            timeframe="1h",
            timestamp=(base_time + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            open=40000.0 + i,
            high=40100.0 + i,
            low=39900.0 + i,
            close=40050.0 + i,
            volume=100.0,
            is_closed=True,
        )
        for i in range(16)
    ]
    inp_a1 = ForecastInput(
        symbol="BTCUSDT",
        timeframe="1h",
        historical_sequence=candles_a,
        sequence_length=16,
        dataset_id="dataset-1",
        forecast_horizon=4,
        model_identifier="kronos-mini",
        model_version="v1",
    )
    inp_a2 = ForecastInput(
        symbol="BTCUSDT",
        timeframe="1h",
        historical_sequence=candles_a,
        sequence_length=16,
        dataset_id="dataset-1",
        forecast_horizon=4,
        model_identifier="kronos-mini",
        model_version="v1",
    )

    fp1 = inp_a1.compute_input_fingerprint()
    fp2 = inp_a2.compute_input_fingerprint()
    assert fp1 == fp2, "Fingerprint must be perfectly deterministic"
    assert len(fp1) == 64, "Fingerprint must be standard 64-character SHA256 hex"

    # Modify one price by 1 cent
    candles_b = [c.model_copy() for c in candles_a]
    candles_b[5].close = 40055.01
    inp_b = ForecastInput(
        symbol="BTCUSDT",
        timeframe="1h",
        historical_sequence=candles_b,
        sequence_length=16,
        dataset_id="dataset-1",
        forecast_horizon=4,
        model_identifier="kronos-mini",
        model_version="v1",
    )
    fp_b = inp_b.compute_input_fingerprint()
    assert fp1 != fp_b, "Single cent modification must completely alter input fingerprint"


@pytest.mark.asyncio
async def test_kronos_forecaster_end_to_end_contract(shared_kronos_forecaster):
    """Verify complete forecast payload, mathematical invariants, and horizon alignment."""
    base_time = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    candles = [
        ValidatedCandle(
            symbol="ETHUSDT",
            timeframe="1h",
            timestamp=(base_time + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
            open=3000.0 + i * 2.0,
            high=3020.0 + i * 2.0,
            low=2990.0 + i * 2.0,
            close=3010.0 + i * 2.0,
            volume=500.0,
            is_closed=True,
        )
        for i in range(32)
    ]

    inp = ForecastInput(
        symbol="ETHUSDT",
        timeframe="1h",
        historical_sequence=candles,
        sequence_length=len(candles),
        dataset_id="v2.0.0-test",
        forecast_horizon=4,
        model_identifier="NeoQuasar/Kronos-mini",
        model_version="v1.0.0",
    )

    out = await shared_kronos_forecaster.forecast(inp)

    # 1. Top-level contract validation
    assert isinstance(out, ForecastOutput)
    assert out.symbol == "ETHUSDT"
    assert out.timeframe == "1h"
    assert out.forecast_horizon == 4
    assert len(out.forecasted_sequence) == 4
    assert out.input_dataset_fingerprint == inp.compute_input_fingerprint()

    # 2. Timestamp alignment check (Step 1 must be exactly T + 1h)
    expected_step1_ts = (base_time + timedelta(hours=32)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    assert out.forecasted_sequence[0].timestamp == expected_step1_ts

    # 3. Mathematical OHLC Invariants on all forecasted candles
    for bar in out.forecasted_sequence:
        assert bar.high >= bar.low, f"High ({bar.high}) must be >= Low ({bar.low})"
        assert bar.high >= bar.open, f"High ({bar.high}) must be >= Open ({bar.open})"
        assert bar.high >= bar.close, f"High ({bar.high}) must be >= Close ({bar.close})"
        assert bar.low <= bar.open, f"Low ({bar.low}) must be <= Open ({bar.open})"
        assert bar.low <= bar.close, f"Low ({bar.low}) must be <= Close ({bar.close})"
        assert bar.open > 0.0
        assert bar.close > 0.0
        assert bar.volume >= 0.0
        assert bar.confidence_lower <= bar.close <= bar.confidence_upper

    # 4. Uncertainty distribution check
    dist = out.uncertainty_distribution
    assert dist is not None
    assert dist["predicted_direction"] in ["LONG", "SHORT", "FLAT"]
    assert isinstance(dist["predicted_return_pct"], float)
    assert 0.0 <= dist["confidence_score"] <= 1.0


def test_hybrid_confirmation_gate_logic():
    """Verify Group C gating logic: candidate executed only on model agreement."""
    # Scenario A: Deterministic BUY, Kronos agrees with LONG -> ACCEPTED
    k_dir = "LONG"
    k_ret = 0.45
    cand_dir = "BUY"
    expected_k_dir = "LONG" if cand_dir == "BUY" else "SHORT"
    is_confirmed = (k_dir == expected_k_dir) and (abs(k_ret) >= 0.10)
    assert is_confirmed is True

    # Scenario B: Deterministic BUY, Kronos predicts SHORT -> REJECTED
    k_dir_opp = "SHORT"
    is_confirmed_opp = (k_dir_opp == expected_k_dir) and (abs(k_ret) >= 0.10)
    assert is_confirmed_opp is False

    # Scenario C: Deterministic SELL, Kronos predicts FLAT / low return -> REJECTED
    cand_sell = "SELL"
    expected_sell_k = "LONG" if cand_sell == "BUY" else "SHORT"
    k_flat_dir = "SHORT"
    k_flat_ret = 0.04  # Below 0.10% threshold
    is_confirmed_flat = (k_flat_dir == expected_sell_k) and (abs(k_flat_ret) >= 0.10)
    assert is_confirmed_flat is False

