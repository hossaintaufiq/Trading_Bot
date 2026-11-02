# NEPTUNE — Milestone 4.5: Kronos Foundation Model Experimental Integration

> **Audit Identifier**: `AUDIT-M4.5-KRONOS-INTEGRATION`  
> **Date**: 2026-11-02  
> **Status**: COMPLETED & VERIFIED  
> **Model Checkpoint**: `NeoQuasar/Kronos-mini` (~4.1M parameters)  
> **Tokenizer Checkpoint**: `NeoQuasar/Kronos-Tokenizer-2k` (20-bit BSQ Codebook)  
> **Upstream Repository**: `shiyu-coder/Kronos` (MIT License)  
> **Target Dataset**: Frozen Historical Dataset `v2.0.0` (SHA256: `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`)  
> **Target Assets**: `BTCUSDT`, `ETHUSDT`, `BNBUSDT` across `1h`, `4h`, `1d`  

---

## 1. Executive Summary

Milestone 4.5 integrates **Kronos**—a pretrained autoregressive financial time-series foundation model—into NEPTUNE's quantitative research architecture.

Per **ADR-021** (Model-Agnostic Forecasting Interface) and Rules `S-01`, `S-04`, `S-05`, and `S-08` through `S-10`, Kronos is integrated strictly in a **research-isolated, read-only advisory capacity**. Kronos is completely decoupled from order execution, cannot authorize paper orders, and cannot override Risk Manager constraints.

All inference runs locally on **Windows 11 x86_64 CPU** without requiring CUDA or external GPU runtimes. The model exhibits a minimal memory footprint (+39.5 MB RAM) and exceptional inference throughput (11.2 req/s at horizon $H=4$), enabling rapid evaluation across large historical partitions.

---

## 2. Model Architecture & Checkpoint Specifications

### 2.1 Kronos-mini Foundation Model

The model checkpoint used is `NeoQuasar/Kronos-mini` with exact parameter count verified by unit tests:

| Component | Specification | Description |
|:---|:---|:---|
| **Model Type** | Autoregressive Decoder Transformer | Predicts forward price tokens conditioned on past token sequences |
| **Parameters** | **4,108,032** (~4.1M) | Verified via `sum(p.numel() for p in model.parameters())` |
| **Model Dimension ($d_{model}$)** | 256 | Hidden state embedding size |
| **Transformer Layers ($n_{layers}$)** | 4 | Decoder blocks with causal self-attention |
| **Attention Heads ($n_{heads}$)** | 4 | Multi-head attention with RoPE |
| **Feed-Forward Dimension ($ff_{dim}$)** | 512 | SwiGLU-style feed-forward network |
| **Positional Embedding** | Rotary Positional Embedding (RoPE) | Applied directly to Query and Key states |
| **Temporal Embedding** | Multi-Scale Sinusoidal Embedding | Minute, Hour, Weekday, Day, Month |
| **Normalization** | RMSNorm ($\epsilon = 10^{-5}$) | Pre-normalization across all blocks |
| **Dual Head** | Hierarchical Classification Heads | Decodes coarse ($s_1$) and fine ($s_2$) token logits |
| **Weight Footprint** | ~15.7 MB (`model.safetensors`) | Stored in local Hugging Face Hub cache |

### 2.2 Kronos-Tokenizer-2k

Discrete tokenization is achieved via Binary Spherical Quantization (BSQ):

| Component | Specification | Description |
|:---|:---|:---|
| **Input Channels ($d_{in}$)** | 6 | `open`, `high`, `low`, `close`, `volume`, `amount` |
| **Encoder / Decoder Layers** | 4 / 4 | 3 TransformerBlocks + Linear projections |
| **Quantization Scheme** | Binary Spherical Quantization (BSQ) | Normalizes hidden states to unit hypersphere; applies sign quantization |
| **Codebook Bits** | 20 bits total ($s_1=10, s_2=10$) | $2^{10} = 1024$ coarse tokens, $2^{10} = 1024$ fine tokens |
| **Vocabulary Size** | $2^{20} = 1,048,576$ states | Decomposed into hierarchical two-stage token prediction |
| **Tokenizer Footprint** | ~17.1 MB (`model.safetensors`) | Stored in local Hugging Face Hub cache |

---

## 3. Architecture & Interface Implementation

The integration adheres strictly to the model-agnostic `IForecaster` protocol defined in `backend/app/analytics/forecasting.py`:

```
┌─────────────────────────────────────────────────────────────┐
│                     ForecastInput                           │
│  - symbol: str                                              │
│  - timeframe: str                                           │
│  - historical_sequence: List[ValidatedCandle] (closed only) │
│  - forecast_horizon: int (1, 4, 12, ...)                     │
│  - compute_input_fingerprint() -> SHA-256                   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    KronosForecaster                         │
│  - Look-ahead bias verification (is_closed == True)         │
│  - Chronological ordering verification                       │
│  - Robust timestamp projection (T + k * timeframe)          │
│  - BSQ Tokenization & Autoregressive Decoding               │
│  - Uncertainty distribution & confidence estimation         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    ForecastOutput                           │
│  - symbol: str, timeframe: str                              │
│  - forecasted_sequence: List[ForecastCandle]                │
│  - input_dataset_fingerprint: str (SHA-256)                 │
│  - uncertainty_distribution: Dict[str, Any]                 │
│  - validation_metadata: Dict[str, Any]                      │
└─────────────────────────────────────────────────────────────┘
```

### Module Structure:
- `backend/app/analytics/forecasters/quantizer.py`: `BinarySphericalQuantizer`, `BSQuantizer`, differentiable entropy functions.
- `backend/app/analytics/forecasters/transformer_layers.py`: `RMSNorm`, `FeedForward`, `RotaryPositionalEmbedding`, `MultiHeadAttentionWithRoPE`, `HierarchicalEmbedding`, `DependencyAwareLayer`, `DualHead`, `TemporalEmbedding`.
- `backend/app/analytics/forecasters/kronos_model.py`: `KronosTokenizer`, `Kronos`, `KronosPredictor`, autoregressive sampling with nucleus filtering.
- `backend/app/analytics/forecasters/kronos_forecaster.py`: `KronosForecaster` implementing `IForecaster`.
- `backend/app/analytics/forecasters/experiment_runner.py`: Orchestrator for Group A, Group B, and Group C evaluations.

---

## 4. Safety & Invariant Compliance

1. **Rule S-01 (Paper Simulation Only)**: Kronos has no connection to exchange APIs, private keys, or execution routers.
2. **Rule S-04 (Risk Manager Exclusivity)**: Forecasts can never authorize paper orders or override risk constraints. All paper trades are mediated by `RiskManager`.
3. **Rule S-05 (Zero Look-Ahead Bias)**: Evaluated candles must be strictly closed (`is_closed == True`). Forecast horizons strictly project forward into $T > T_{eval}$.
4. **Rule A-01 (Decimal Precision)**: All monetary metrics, execution prices, and fees are calculated using Python `Decimal`.
5. **Rule A-02 (Canonical UTC)**: All timestamps are normalized to UTC ISO 8601 strings ending in `Z`.
6. **Rules S-08 to S-10 (Monolith Preservation)**: Implemented as clean native Python modules within the existing monolith without introducing microservices, Redis, Kafka, or external RPCs.

