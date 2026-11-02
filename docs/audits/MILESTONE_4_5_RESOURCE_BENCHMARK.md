# NEPTUNE — Milestone 4.5: Resource Consumption & Runtime Benchmark

> **Audit Identifier**: `AUDIT-M4.5-RESOURCE-BENCHMARK`  
> **Date**: 2026-11-02  
> **Status**: EMPIRICALLY BENCHMARKED & VERIFIED  
> **Platform**: Windows 11 (x86_64), Python 3.14  
> **Execution Device**: Intel/AMD CPU (No CUDA/GPU required)  

---

## 1. Executive Summary

Milestone 4.5 conducted empirical benchmarks to measure the memory, latency, and CPU footprint of `Kronos-mini` (`NeoQuasar/Kronos-mini`, ~4.1M parameters) combined with `Kronos-Tokenizer-2k` under native CPU execution.

The results establish that Kronos-mini is exceptionally lightweight, adding only **39.1 MB** of RAM and executing 4-step forward forecasts in **89.2 ms** on consumer CPU hardware.

---

## 2. Memory Footprint

Measured via `psutil.Process().memory_info().rss`:

| Measurement Stage | RSS Memory (MB) | Delta (MB) | Note |
|:---|:---|:---|:---|
| **Raw Python Process** | 271.87 MB | — | Baseline runtime with PyTorch & Pandas imported |
| **Model & Tokenizer Loaded** | 310.98 MB | **+39.11 MB** | Full weights and KV buffers resident in memory |
| **Peak During Inference** | 322.42 MB | **+50.55 MB** | Dynamic activation tensors during autoregressive generation |

**Conclusion**: Memory consumption is trivial (< 350 MB peak), comfortably fitting on memory-constrained systems or low-spec development machines without any swap memory usage.

---

## 3. Inference Latency by Forecast Horizon

Inference was evaluated over multiple runs using 64 past context candles across horizons $H \in \{1, 4, 12\}$:

| Forecast Horizon | Latency (ms) | Time Per Step (ms) | Throughput (req/s) |
|:---:|:---:|:---:|:---:|
| **$H = 1$ (1 step)** | **46.8 ms** | 46.8 ms | **21.35 req/s** |
| **$H = 4$ (4 steps)** | **89.2 ms** | 22.3 ms | **11.21 req/s** |
| **$H = 12$ (12 steps)** | **187.6 ms** | 15.6 ms | **5.33 req/s** |

### Latency Characteristics:
1. **Initial Step Overhead**: Step 1 takes ~46.8 ms due to context encoding and first-token prediction.
2. **Amortized Step Speed**: Subsequent autoregressive steps take ~14 to 16 ms each due to efficient KV-cache rolling in the pre-allocated buffer.
3. **CPU Viability**: At 11.2 requests per second for a 4-hour horizon, generating forecasts for all 3 assets takes less than 300 ms per closed candle.

---

## 4. Hardware Feasibility & Production Readiness

| Criteria | Windows 11 CPU Result | Verdict |
|:---|:---|:---|
| **CUDA / GPU Dependency** | Zero. Runs entirely on PyTorch CPU tensors | **PASSED** |
| **C++ Build Tools Required** | Zero. Pure Python + PyTorch wheel | **PASSED** |
| **Throughput on 1h Candles** | Capacity: 40,000+ forecasts/hour (Demand: 3 forecasts/hour) | **EXCEEDS REQUIREMENTS** |
| **Disk Space** | Model (~15.7 MB) + Tokenizer (~17.1 MB) = ~32.8 MB | **PASSED** |

