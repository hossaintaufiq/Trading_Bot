# NEPTUNE — Milestone 4.4: Kronos Compatibility & Foundation Forecasting Architecture

## 1. Executive Summary

Milestone 4.4 establishes the architectural foundation for evaluating foundation financial forecasting models (such as Kronos, Chronos, and TimesFM) within NEPTUNE's quantitative research environment.

In strict adherence to Project Rules `S-01`, `S-04`, `E-08`, and ADR-021:
1. **Model Independence**: The forecasting contract is completely decoupled from any specific machine learning framework, PyTorch runtime, or model architecture.
2. **Zero Look-Ahead Bias**: Inputs require explicit past closed candles, dataset provenance IDs, and compute cryptographic input fingerprints to prevent data leakage.
3. **Research Isolation**: Forecasts are strictly analytical signals. They are **never permitted to directly authorize paper orders**, enter positions, or bypass the Central Brain and Risk Manager.
4. **Deferred Inference**: Model weights (~hundreds of megabytes to gigabytes) and GPU inference runtimes are deferred to future milestones. A deterministic `MockAgnosticForecaster` is provided for testing contracts, pipeline integration, and validation interfaces.

---

## 2. Model-Independent Forecasting Interface Contract

The forecasting interface is implemented in `backend/app/analytics/forecasting.py` using typed Pydantic models.

### Input Contract (`ForecastInput`)

```python
class ForecastInput(BaseModel):
    symbol: str
    timeframe: str
    historical_sequence: List[ValidatedCandle]
    sequence_length: int = Field(ge=10)
    dataset_id: str
    forecast_horizon: int = Field(ge=1, le=100)
    model_identifier: str
    model_version: str

    def compute_input_fingerprint(self) -> str:
        """Cryptographic SHA256 hash of the input sequence to guarantee no look-ahead tampering."""
        ...
```

### Output Contract (`ForecastOutput`)

```python
class ForecastCandle(BaseModel):
    step: int = Field(ge=1)
    timestamp: str
    open: float = Field(gt=0.0)
    high: float = Field(gt=0.0)
    low: float = Field(gt=0.0)
    close: float = Field(gt=0.0)
    volume: float = Field(ge=0.0)
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None

class ForecastOutput(BaseModel):
    symbol: str
    timeframe: str
    forecasted_sequence: List[ForecastCandle]
    forecast_horizon: int
    model_identifier: str
    model_version: str
    input_dataset_fingerprint: str
    generation_timestamp: str
    uncertainty_distribution: Optional[Dict[str, Any]] = None
    validation_metadata: Dict[str, Any] = Field(default_factory=dict)
```

### Interface Protocol (`IForecaster`)

```python
class IForecaster(Protocol):
    async def forecast(self, input_payload: ForecastInput) -> ForecastOutput:
        """Generate forward forecast for the given historical sequence."""
        ...
```

---

## 3. Zero-Lookahead & Tamper-Evident Fingerprinting

To ensure that future evaluations of Kronos or other models cannot cheat by observing future prices:
1. `ForecastInput.compute_input_fingerprint()` hashes the input candle sequence:
   $$H_{\text{input}} = \text{SHA256}\Big(\text{dataset\_id} \parallel \text{symbol} \parallel \text{timeframe} \parallel \bigoplus_{t=0}^{T} (t_i, o_i, h_i, l_i, c_i, v_i)\Big)$$
2. The forecaster embeds $H_{\text{input}}$ directly into `ForecastOutput.input_dataset_fingerprint`.
3. Audit pipelines verify that $H_{\text{input}}$ matches the known past state of the candle repository at time $T$.

---

## 4. Future Experimental Design: Measuring Marginal Value

When foundation model inference is integrated in subsequent milestones, the research harness will evaluate incremental economic utility across three distinct configurations:

```
[Configuration A: Deterministic Baseline]
   Candles ──► Market Scanner / Trend / Momentum ──► Strategy Analyst ──► Risk Manager

[Configuration B: Forecasting Alone]
   Candles ──► Foundation Model (Kronos) ──────────► Strategy Analyst ──► Risk Manager

[Configuration C: Hybrid Model]
   Candles ──► Deterministic Agents + Kronos Forecast ──► Strategy Analyst ──► Risk Manager
```

### Key Research Questions
1. **Directional Accuracy**: Does Kronos forecast bar $T+1 \dots T+H$ direction better than simple momentum?
2. **Economic Viability**: Does trading Kronos forecasts cover transaction friction (0.30% round-trip)?
3. **Confluence Filter**: Can Kronos volatility or directional uncertainty serve as a pre-trade filter to reduce false breakouts in the deterministic baseline?

---

## 5. Architectural Decision Summary (ADR-021)

- **Status**: Accepted (documented in `docs/ARCHITECTURE_DECISIONS.md`).
- **Deferred Implementation**: External model inference and dependency weight packages are deferred until the backtesting simulation harness establishes baseline forecasting metrics.
- **Verification**: `test_forecasting_interface_contract_and_lookahead_prevention` in `backend/tests/unit/test_milestone_4_4_research_foundation.py` validates that `MockAgnosticForecaster` complies 100% with all input and output schemas.

