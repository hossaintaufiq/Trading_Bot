# NEPTUNE Milestone 4.5.1 — Audit B: Forecast Temporal Integrity

**Audit Date:** 2026-11-02  
**Baseline Commit:** `f0957a0` / `22ab286`  
**Dataset Version:** `v2.0.0` (Tree SHA256: `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`)  
**Target File:** `storage/exports/milestone_4_5/forecast_predictions.parquet`  
**Audit Scope:** Independent forensic audit of prediction timeline, look-ahead bias, closed-candle compliance (Rule A-09, Rule S-05), target alignment ($T + k \cdot \Delta t$), and sample independence.

---

## 1. Executive Summary & Verdict

* **Audit Verdict:** **PASS WITH METHODOLOGICAL QUALIFICATION**
* **Total Prediction Records:** Exactly **1,350 rows** in `forecast_predictions.parquet`.
* **Unique Forecast Origins:** Exactly **450 unique origin points** ($T$) evaluated across three forecast horizons ($H \in \{1, 4, 12\}$).
* **Temporal Ordering:** 100% strictly monotonic non-decreasing origin timestamps within each asset and timeframe partition.
* **Look-Ahead Bias:** **Zero violations**. For every record, $\text{target\_timestamp} > \text{origin\_timestamp}$. The model context buffer only ingested confirmed closed candles up to and including $T$.
* **Target Timestamp Alignment ($T + k \cdot \Delta t$):** **Zero alignment errors**. Every horizon forecast strictly aligns with $T + k \cdot \text{timeframe\_delta}$.
* **Ground-Truth Parity vs Frozen Dataset `v2.0.0`:** A random audit of 100 predictions matched the frozen Parquet candle files in `storage/datasets/v2.0.0/` with **0 price mismatches**.
* **Methodological Qualification (Sample Independence):** The 1,350 rows do NOT represent 1,350 independent trials. Because 3 horizons are evaluated at the exact same 450 origins, observations within each origin are serially and structurally correlated. Statistical hypothesis testing must treat each horizon as an $N=450$ sample, rather than pooling $N=1,350$.

---

## 2. Origin Matrix & Horizon Distribution

The 1,350 predictions are partitioned uniformly across three Tier-1 spot assets and three operational timeframes during the out-of-sample period (`2026-01-01T00:00:00.000Z` to `2026-11-01T23:59:59.000Z`):

| Symbol | Timeframe | Unique Forecast Origins ($T$) | Horizons Evaluated ($k$) | Total Forecast Rows |
|---|---|---:|:---:|---:|
| **BTCUSDT** | `1h` | 50 | [1, 4, 12] | 150 |
| **BTCUSDT** | `4h` | 50 | [1, 4, 12] | 150 |
| **BTCUSDT** | `1d` | 50 | [1, 4, 12] | 150 |
| **ETHUSDT** | `1h` | 50 | [1, 4, 12] | 150 |
| **ETHUSDT** | `4h` | 50 | [1, 4, 12] | 150 |
| **ETHUSDT** | `1d` | 50 | [1, 4, 12] | 150 |
| **BNBUSDT** | `1h` | 50 | [1, 4, 12] | 150 |
| **BNBUSDT** | `4h` | 50 | [1, 4, 12] | 150 |
| **BNBUSDT** | `1d` | 50 | [1, 4, 12] | 150 |
| **TOTAL** | — | **450 Unique Origins** | **3 Horizons** | **1,350 Records** |

Every origin was sampled at regular step intervals across the out-of-sample period, ensuring balanced temporal coverage without clustering around specific market regimes.

---

## 3. Target Alignment & Look-Ahead Verification

For every record $i \in \{1, \dots, 1350\}$:
$$\Delta t_{\text{actual}} = \text{target\_timestamp}_i - \text{timestamp}_i$$
$$\Delta t_{\text{expected}} = H_i \times \text{timeframe\_delta}$$

| Timeframe | Horizon | Expected $\Delta t$ | Records Tested | Alignment Errors | Look-Ahead Violations ($\le 0$) |
|---|---:|---:|---:|---:|---:|
| `1h` | 1 | 1 hour | 150 | 0 | 0 |
| `1h` | 4 | 4 hours | 150 | 0 | 0 |
| `1h` | 12 | 12 hours | 150 | 0 | 0 |
| `4h` | 1 | 4 hours | 150 | 0 | 0 |
| `4h` | 4 | 16 hours | 150 | 0 | 0 |
| `4h` | 12 | 48 hours | 150 | 0 | 0 |
| `1d` | 1 | 1 day | 150 | 0 | 0 |
| `1d` | 4 | 4 days | 150 | 0 | 0 |
| `1d` | 12 | 12 days | 150 | 0 | 0 |
| **TOTAL** | — | — | **1,350** | **0** | **0** |

All records strictly satisfy $\Delta t_{\text{actual}} = \Delta t_{\text{expected}} > 0$. Zero look-ahead bias exists.

---

## 4. Context Buffer & Closed-Candle Compliance (Rules A-09, S-05)

The context buffer ingestion mechanism in [`experiment_runner.py`](file:///d:/Project%202026/Trading_bot/backend/app/analytics/forecasters/experiment_runner.py) was audited:
1. `history = candles[: idx + 1]`: The context window takes candles strictly up to index `idx`.
2. Every candle in `candles` originates from `ParquetMarketDataRepository` and was validated with `is_closed=True`.
3. In-progress / unclosed candles are never present in the frozen dataset `v2.0.0` or active storage.
4. The target candle at `target_timestamp` is strictly withheld from the model input and used exclusively for post-hoc error calculation.

---

## 5. Sample Independence Audit & Methodological Finding

### The Statistical Issue
The Milestone 4.5 report presented aggregate metrics over $N=1,350$ predictions. However:
- A single market event at origin timestamp $T$ impacts the forecasts for $H=1$, $H=4$, and $H=12$ simultaneously.
- Forecast errors across nested horizons at the same origin exhibit strong serial cross-correlation:
  $$\text{Cov}(\epsilon_{T, 1}, \epsilon_{T, 4}) > 0$$
- Treating $N=1,350$ as independent identically distributed (i.i.d.) observations artificially inflates test statistics (e.g., halving the standard error by a factor of $\sqrt{3} \approx 1.732$).

### Audit Mandate
All statistical validity tests (binomial tests, Wilson confidence intervals, Student's t-tests) must be evaluated separately per horizon at $N=450$. Milestone 4.5.1 enforces this standard in Audit C.
