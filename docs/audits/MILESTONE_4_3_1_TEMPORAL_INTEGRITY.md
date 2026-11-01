# NEPTUNE — Milestone 4.3.1: Temporal Integrity & Look-Ahead Audit

**Document Version**: 1.0.0  
**Audit Target**: Milestone 4.3 Baseline & Entry Filters (Commit `17cd092`)  
**Auditor**: Independent Quantitative System Auditor  
**Date**: 2026-11-02  
**Governing Rules**: `AGENTS.md` (S-05 Look-Ahead Bias Prevention, A-02 UTC Timestamps, A-09 Closed Candles Only)  

---

## 1. Executive Summary

This audit assesses the temporal integrity, look-ahead bias resistance, and dataset partitioning methodology employed in **Milestone 4.3 (Entry Strategy Diagnosis & Regime-Aware Filtering)**.

### Primary Audit Findings:
1. **Analytical Invariance & Indicator Look-Ahead (VERIFIED SOUND)**:
   - All indicator implementations (`calculate_ema`, `calculate_atr`, `calculate_adx`, `calculate_rsi`, `calculate_macd`, `calculate_rvol`, `calculate_candle_volatility`) strictly operate on causal, historical series $[C_0, C_1, \dots, C_T]$.
   - No backward indexing, shifting, or future-candle peeking occurs.
   - Indicators consume strictly closed candles (Rule A-09).
2. **Multi-Timeframe Look-Ahead Prevention (VERIFIED SOUND)**:
   - In `filter_higher_timeframe_alignment`, the HTF series is filtered via `valid_htf = [c for c in htf_candles if c.timestamp <= current_ts and c.is_closed]`.
   - In-progress HTF bars are strictly rejected, preventing information leakage from future HTF closes into LTF decisions.
3. **Chronological Partitioning Defect: Severe Timeframe Clustering (CRITICAL LIMITATION)**:
   - Milestone 4.3 partitioned trades by sorting the aggregate pool of 277 trades chronologically and splitting them into 50% Train (138), 25% Validation (69), and 25% Out-of-Sample (70).
   - Because historical data lengths were asymmetric across timeframes (500 days for 4h, 208 days for 1h, and 52 days for 15m), **the Out-of-Sample (OOS) partition is 100.0% composed of 15m trades from a single 23-day period (Sept 19 to Oct 12, 2026)**.
   - The 4h and 1h timeframes have **0.0% representation in OOS**.
   - Consequently, the reported OOS result does NOT validate multi-timeframe generalizability; it only measures the behavior of 15m candles during an isolated 23-day low-volatility regime.

---

## 2. Invariant Verification: Analytical Indicators

Every indicator used in the analysis engine, baseline strategy, and entry filters was audited for causal boundaries.

| Indicator | Function | Inputs | Look-Ahead Protection Mechanism | Audit Finding |
| :--- | :--- | :--- | :--- | :---: |
| **EMA** | `calculate_ema` | `closes: Sequence[float], period: int` | Seeded with SMA of first $N$ bars; iterative recurrence $EMA_t = \alpha P_t + (1-\alpha)EMA_{t-1}$. Only references past values. | **PASS** |
| **ATR** | `calculate_atr` | `highs, lows, closes, period` | True Range computed from $C_t, H_t, L_t, C_{t-1}$. Smoothed using Wilder's RMA over historical bars. | **PASS** |
| **ADX / DMI** | `calculate_adx` | `highs, lows, closes, period` | $+DM, -DM$ computed from $(H_t - H_{t-1})$ and $(L_{t-1} - L_t)$. Smoothed via Wilder's RMA. No future bar lookups. | **PASS** |
| **RSI** | `calculate_rsi` | `closes, period` | Price changes $\Delta_t = C_t - C_{t-1}$; average gains and losses computed forward. Strictly causal. | **PASS** |
| **MACD** | `calculate_macd` | `closes, fast, slow, signal` | $EMA_{12} - EMA_{26}$, signal line is $EMA_9$ of MACD line. Causal recurrence. | **PASS** |
| **RVOL** | `calculate_rvol` | `volumes, period=20` | $V_T / \text{SMA}_{20}(V_{T-19:T})$. Strictly references current and preceding 19 volume observations. | **PASS** |
| **Volatility Bounds** | `calculate_candle_volatility` | `highs, lows, closes, period=14` | $ATR_{14}(T) / Close(T)$. Evaluates normalized volatility at bar $T$ close. | **PASS** |

### Mathematical Proof of Causal Boundary
Let $X = (x_0, x_1, \dots, x_T)$ be a sequence of closed candle observations up to time $T$. For any indicator $\mathcal{I}$:
$$\mathcal{I}(X)_T = f(x_0, x_1, \dots, x_T)$$
For all indicators evaluated, $\frac{\partial \mathcal{I}_T}{\partial x_{T+k}} = 0$ for all $k \ge 1$. Hence, look-ahead bias is strictly zero.

---

## 3. Multi-Timeframe (HTF) Alignment Integrity

Multi-timeframe analysis introduces the highest risk of look-ahead leakage in quantitative trading if an unfinished higher-timeframe bar is queried.

### Code Implementation in `app/analytics/filters.py`:
```python
def filter_higher_timeframe_alignment(
    current_ts: str,
    direction: str,
    htf_candles: Sequence[ValidatedCandle],
) -> FilterDecision:
    # Rule S-05 & Rule A-09: Filter strictly closed HTF candles up to current timestamp
    valid_htf = [c for c in htf_candles if c.timestamp <= current_ts and c.is_closed]
    if len(valid_htf) < 50:
        return FilterDecision(
            filter_id="H2_HTF_ALIGNMENT",
            passed=False,
            direction=direction,
            rejection_reason=f"Insufficient HTF candle history ({len(valid_htf)}/50).",
        )
    ...
```

### Verification Against Binance UTC Candle Closes:
- In Binance Parquet storage, candle `timestamp` denotes the start timestamp of the candle.
- When candle $T$ of 15m closes at `12:15:00.000Z`, the 1h candle starting at `12:00:00.000Z` is still open and will not close until `13:00:00.000Z`.
- Because the repository only stores closed candles (`is_closed=True`), any 1h candle stamped `12:00:00` would not be considered closed until `13:00:00`.
- Unit test `test_htf_temporal_isolation` explicitly verified that when 10 future HTF crash candles are appended, the filter's output at timestamp $T$ remains completely unaffected.

---

## 4. Chronological Partitioning Defect & Timeframe Distortion

### Empirical Investigation
Milestone 4.3 partitioned the baseline dataset into:
- **Train (50%)**: First 138 trades
- **Validation (25%)**: Next 69 trades
- **Out-of-Sample / OOS (25%)**: Final 70 trades

To audit this partition, an independent reconstruction script (`scratch/analyze_partitions.py`) loaded all 39,000 candles and analyzed the exact composition of each partition:

```
Total Baseline Trades: 277
Train (50%): 138 trades | 2025-07-09T08:00:00.000Z -> 2026-05-28T14:00:00.000Z
Train TF breakdown:
  4h:    86 trades (62.3%)
  1h:    52 trades (37.7%)
  15m:    0 trades (0.0%)

Val (25%): 69 trades | 2026-05-28T16:00:00.000Z -> 2026-09-19T09:30:00.000Z
Val TF breakdown:
  1h:    33 trades (47.8%)
  15m:   29 trades (42.0%)
  4h:     7 trades (10.1%)

OOS (25%): 70 trades | 2026-09-19T13:00:00.000Z -> 2026-10-12T21:45:00.000Z
OOS TF breakdown:
  15m:   70 trades (100.0%)
  1h:     0 trades (0.0%)
  4h:     0 trades (0.0%)
```

### Analysis of the Distortion:
1. **Asymmetric Historical Duration**:
   - 4h candles (3,000 bars) span 500 calendar days (May 31, 2025 to Oct 12, 2026).
   - 1h candles (5,000 bars) span 208 calendar days (March 18, 2026 to Oct 12, 2026).
   - 15m candles (5,000 bars) span only 52 calendar days (August 21, 2026 to Oct 12, 2026).
2. **Chronological Pooling Bias**:
   - Because 15m produces trades at roughly $16\times$ the frequency of 4h, once the 15m window begins in late August 2026, 15m trades overwhelm the chronological stream.
   - The Train partition consists **exclusively of 4h and 1h trades** (500 days of data).
   - The OOS partition consists **exclusively of 15m trades** (23 days of data).
3. **Consequence for OOS Hypothesis Testing**:
   - Milestone 4.3 reported that in OOS, H5 and H7 took 0 trades, "preserving capital against a 20% drawdown".
   - Our audit reveals that this 0-trade result occurred exclusively because the entire OOS partition consisted of 15m trades during a 23-day period in late September to early October 2026 where 15m volatility happened to sit below 0.80%.
   - The OOS partition provided **zero empirical verification for 1h or 4h performance**.
   - Claiming that H7 is "validated out-of-sample across all 9 datasets" is methodologically inaccurate when 6 of the 9 datasets had zero trades in the OOS partition.

---

## 5. Audit Recommendations for Temporal Partitioning

To avoid timeframe distortion in future multi-timeframe research:
1. **Per-Timeframe Partitioning**:
   - Partition each timeframe independently into 50% Train, 25% Validation, and 25% OOS.
   - This guarantees that 4h, 1h, and 15m are all equally represented in each partition.
2. **Calendar-Synchronized Truncation**:
   - If pooling across timeframes is required, synchronize the historical start date so all timeframes cover the exact same calendar period (e.g., Aug 21, 2026 to Oct 12, 2026), rather than allowing longer timeframes to dominate the early sample.

