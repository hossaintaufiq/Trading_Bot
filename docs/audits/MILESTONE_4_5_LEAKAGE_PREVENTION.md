# NEPTUNE — Milestone 4.5: Data Leakage Prevention & Audit Trail

> **Audit Identifier**: `AUDIT-M4.5-LEAKAGE-PREVENTION`  
> **Date**: 2026-11-02  
> **Status**: VERIFIED & TESTED  

---

## 1. Look-Ahead Bias Prevention Guarantees

In financial time-series forecasting, data leakage can easily create spurious accuracy. NEPTUNE enforces multi-layered technical controls to mathematically guarantee zero look-ahead bias:

### 1.1 Strict Closed-Candle Enforcement (Rule A-09)
The `ForecastInput` payload requires a sequence of `ValidatedCandle` objects.
At runtime, `KronosForecaster.forecast()` inspects every candle in the input sequence:
```python
for i, candle in enumerate(input_payload.historical_sequence):
    if not candle.is_closed:
        raise ValueError(
            f"Look-ahead violation: Candle index {i} ({candle.timestamp}) is marked incomplete (is_closed=False)."
        )
```
Any candle with `is_closed=False` causes immediate invocation failure. This is validated by unit test `test_forecaster_rejects_unclosed_candle`.

### 1.2 Chronological Sequence Order
`KronosForecaster` enforces that all input timestamps are strictly increasing in time:
```python
timestamps_dt = [c.dt_utc for c in input_payload.historical_sequence]
for i in range(1, len(timestamps_dt)):
    if timestamps_dt[i] <= timestamps_dt[i - 1]:
        raise ValueError(
            f"Chronological ordering violation: Candle {timestamps_dt[i]} does not strictly follow {timestamps_dt[i-1]}."
        )
```
This prevents retro-causal sequence concatenation or future bars accidentally shuffled into the context window. Tested by `test_forecaster_rejects_non_chronological_sequence`.

### 1.3 Forward Timestamp Alignment
Forecasted steps project forward strictly beyond the final historical timestamp:
$$T_{\text{forecast}, step} = T_{\text{last\_closed}} + step \times \Delta t_{\text{timeframe}}$$
For example, for a 1h timeframe terminating at `2026-01-01T23:00:00.000Z`, step 1 is strictly `2026-01-02T00:00:00.000Z`. Tested by `test_kronos_forecaster_end_to_end_contract`.

---

## 2. Cryptographic Input Fingerprinting

To ensure complete immutability and verifiable provenance for every forecast, `ForecastInput.compute_input_fingerprint()` produces a canonical SHA-256 hash across:
- `dataset_id`
- `symbol`
- `timeframe`
- Semicolon-delimited sequence of `timestamp:open:high:low:close:volume` for all input bars

This fingerprint is:
1. Computed immediately upon receiving the input payload.
2. Embedded directly into `ForecastOutput.input_dataset_fingerprint`.
3. Stored alongside every prediction record in `storage/exports/milestone_4_5/forecast_predictions.parquet`.

Unit test `test_forecast_input_fingerprint_tamper_sensitivity` confirms that altering even a single price by 1 cent produces a completely different 64-character SHA-256 fingerprint.

---

## 3. Partition Boundary Isolation

Per Milestone 4.4 and ADR-021:
- Historical candles are strictly partitioned into `TRAIN`, `VALIDATION`, `OOS_HISTORICAL_REF`, and `OOS_PRISTINE`.
- Warmup bars provided for context (64 bars) are drawn strictly from $t \le T_{\text{start}}$, never from $t > T_{\text{start}}$.
- Trades cannot span across partition boundaries; all open positions are force-closed at the final millisecond of the evaluation window.

