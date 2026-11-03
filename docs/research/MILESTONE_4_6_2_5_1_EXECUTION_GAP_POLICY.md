# NEPTUNE — Milestone 4.6.2.5.1: Execution Gap Semantics & Policy

**Milestone:** 4.6.2.5.1  
**Document:** Execution Gap Semantics, Boundary Mathematics & Timeframe Calibration Policy  
**Status:** COMPLETE & INDEPENDENTLY VERIFIED  
**Baseline Commit:** `6edeb08`  
**Target Module:** `backend/app/simulation/scheduling.py`  

---

## 1. Executive Summary

In Milestone 4.6.2.4, the Point-in-Time Execution Scheduler transitioned from an initial `max_execution_gap_bars = 1` proposal to a default of `max_execution_gap_bars = 3`. This audit investigates the mathematical, operational, and quantitative implications of that transition, documents the exact elapsed time limits across all supported timeframes (`15m`, `1h`, `4h`, `1d`), and establishes a calibrated policy governing execution validity.

---

## 2. Mathematical Definition of Execution Gaps

In NEPTUNE, candle timestamps represent the **interval start** (e.g. `00:00:00Z` for candle $[00:00, 00:15)$ on 15m). A decision candle closes at:

$$t_{\text{close}} = t_{\text{candle\_start}} + \Delta_{\text{timeframe}}$$

The next eligible execution point is the opening of candle $T+1$, occurring at $t_{\text{exec}} \ge t_{\text{close}}$.

### Elapsed Time Calculation
The elapsed time between decision finality and executed fill is:

$$T_{\text{elapsed}} = t_{\text{exec\_candle\_open}} - t_{\text{decision\_close}}$$

### Maximum Permitted Delay
The maximum allowed delay before deterministic order expiration is defined as:

$$T_{\text{max\_allowed}} = \Delta_{\text{timeframe}} \times (\text{max\_execution\_gap\_bars} + 1)$$

$$\text{If } T_{\text{elapsed}} > T_{\text{max\_allowed}} \implies \text{OrderStatus.EXPIRED}$$

---

## 3. Boundary Matrix Across Supported Timeframes

| Timeframe ($\Delta_{\text{tf}}$) | Nominal Duration | Gap Policy | $T_{\text{max\_allowed}}$ | Maximum Missing Bars Tolerated | Economic Validity Assessment |
| :---: | :---: | :---: | :---: | :---: | :--- |
| **`15m`** | 15 minutes | `max_gap = 1` | 30 minutes | 1 missed candle | **STRICT INTRADAY:** Momentum & breakout signals decay rapidly; 30 min delay is the upper economic boundary. |
| **`15m`** | 15 minutes | `max_gap = 3` | 60 minutes | 3 missed candles | **HIGH RISK:** 60 min delay allows entry into exhausted or reversed moves; forbidden for strict intraday research. |
| **`1h`** | 60 minutes | `max_gap = 3` | 4 hours | 3 missed candles | **SWING TREND:** Multi-hour trend structure and EMA alignment remain stable over 4 hours. |
| **`4h`** | 4 hours | `max_gap = 3` | 16 hours | 3 missed candles | **MULTI-DAY SWING:** Structural support/resistance regimes persist across 16-24 hours. |
| **`1d`** | 24 hours | `max_gap = 3` | 4 days (96h) | 3 missed candles | **MACRO POSITIONAL:** Multi-week macroeconomic regimes remain intact over weekend / holiday gaps. |

---

## 4. Edge Case Behaviors

### 1. Missing Intermediate Candles
- If 1 or 2 candles are missing due to historical exchange downtime or WebSocket drops, but the subsequent candle arrives within $T_{\text{max\_allowed}}$, the scheduler fills at the open of the first available candle.
- The order records `raw_fill_price` and `actual_fill_price` incorporating slippage, spread, and fees at that later open.

### 2. Dataset Termination Prior to Fill
- If the simulation dataset reaches its final candle before the next candle open arrives, post-replay cleanup cleanly marks the order as `OrderStatus.CANCELLED` with reason `"Simulation ended before next eligible execution point"`.
- The reserved token is released via `RiskManager.release_token`.

### 3. Irregular or Non-Standard Time Intervals
- Because NEPTUNE evaluates timestamps using true UTC `datetime` differences (`parse_iso_utc`), irregular intervals (e.g., exchange maintenance windows, DST shifts, or leap seconds) are calculated against exact elapsed seconds rather than bar counts alone.

### 4. Opening Gaps Through Stop Loss
- If market opens beyond the protective stop loss (e.g. $c_{\text{open}} \le \text{stop\_loss}$ for LONG):
  - Order is rejected with `OrderStatus.REJECTED` and reason `Market opening gap below stop loss`.
  - Token is released to prevent capital lockup.

---

## 5. Rationale for Transition: 1 Bar vs. 3 Bars

### Why 1 Bar Was Deemed Restrictive
In real-world data collection and backtesting, single missing candles occasionally occur due to API rate limits, network resets, or maintenance windows. With `max_execution_gap_bars = 1`, ANY missing candle resulted in immediate order expiration, creating artificial execution dropouts that biased trade counts and strategy evaluation.

### Risks of 3 Bars & Calibrated Remediation
On high-frequency or short intraday timeframes (`15m`), waiting 3 bars means the price can drift significantly, invalidating the entry rationale.

**Adopted Policy (ADR-028):**
1. **Intraday Default (`15m`):** Calibrated to `max_execution_gap_bars = 1` (max 30m elapsed).
2. **Swing / Macro Default (`1h`, `4h`, `1d`):** Configured to `max_execution_gap_bars = 3`.
3. Parameter is explicitly exposed and configurable via `BacktestConfig` and `PointInTimeExecutionScheduler`.

---

## 6. Audit Conclusion

The execution-gap semantics are mathematically rigorous, deterministic, and fully covered by parametric unit tests in `test_execution_gap_boundary_matrix`.

**Verdict: PASS**
