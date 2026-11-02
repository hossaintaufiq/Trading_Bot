# NEPTUNE — Milestone 4.5: Forecasting Methodology & Evaluation Design

> **Audit Identifier**: `AUDIT-M4.5-METHODOLOGY`  
> **Date**: 2026-11-02  
> **Status**: COMPLETED & VERIFIED  

---

## 1. Experimental Objectives

The purpose of Milestone 4.5 is to conduct an evidence-driven, out-of-sample evaluation of whether deep-learning financial time-series forecasting (specifically Kronos-mini) provides genuine incremental value beyond NEPTUNE's deterministic analysis engine.

To eliminate hindsight optimization and confirmation bias, the experimental protocol defines three distinct experimental groups:
- **Group A (Deterministic Baseline)**: NEPTUNE's existing deterministic analysis and signal pipeline (`StrategyAnalyst` + `H7_CONFLUENCE` filter + `RiskManager`).
- **Group B (Pure Kronos-mini Strategy)**: Direct trading decisions driven purely by Kronos forward directional forecasts ($|\hat{r}| \ge 0.35\%$).
- **Group C (Hybrid NEPTUNE + Kronos)**: Deterministic signals gated by Kronos directional confirmation (`predicted_direction == signal.direction`).

---

## 2. Statistical Metric Definitions

Let $P_t$ denote the closing price at time $t$, and let $\hat{P}_{t+h}$ denote the predicted closing price for horizon step $h \in \{1, 4, 12\}$.  
Let $P_{t+h}$ denote the actual ground truth closing price at step $h$.

### 2.1 Price Forecast Errors

- **Mean Absolute Error (MAE)**:
  $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N \left| \hat{P}_{t+h}^{(i)} - P_{t+h}^{(i)} \right|$$

- **Root Mean Squared Error (RMSE)**:
  $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N \left( \hat{P}_{t+h}^{(i)} - P_{t+h}^{(i)} \right)^2}$$

- **Mean Absolute Percentage Error (MAPE)**:
  $$\text{MAPE} = \frac{1}{N} \sum_{i=1}^N \frac{\left| \hat{P}_{t+h}^{(i)} - P_{t+h}^{(i)} \right|}{P_{t+h}^{(i)}} \times 100\%$$

- **Mean Forecast Error (MFE / Forecast Bias)**:
  $$\text{MFE} = \frac{1}{N} \sum_{i=1}^N \left( \hat{P}_{t+h}^{(i)} - P_{t+h}^{(i)} \right)$$
  - $\text{MFE} > 0 \implies$ systematic over-estimation (bullish bias).
  - $\text{MFE} < 0 \implies$ systematic under-estimation (bearish bias).

### 2.2 Return & Directional Classification Metrics

- **Predicted and Realized Returns**:
  $$\hat{r}_{t+h} = \frac{\hat{P}_{t+h} - P_t}{P_t} \times 100\%, \quad r_{t+h} = \frac{P_{t+h} - P_t}{P_t} \times 100\%$$

- **Directional Accuracy**:
  $$\text{DA} = \frac{1}{N_{\text{active}}} \sum_{i=1}^{N_{\text{active}}} \mathbb{I}\left( \text{sign}\left(\hat{r}_{t+h}^{(i)}\right) = \text{sign}\left(r_{t+h}^{(i)}\right) \right) \times 100\%$$

- **Directional Precision, Recall, and F1 (UP / LONG)**:
  $$\text{Precision}_{\text{UP}} = \frac{TP_{\text{UP}}}{TP_{\text{UP}} + FP_{\text{UP}}}, \quad \text{Recall}_{\text{UP}} = \frac{TP_{\text{UP}}}{TP_{\text{UP}} + FN_{\text{UP}}}$$
  $$F_{1, \text{UP}} = 2 \times \frac{\text{Precision}_{\text{UP}} \times \text{Recall}_{\text{UP}}}{\text{Precision}_{\text{UP}} + \text{Recall}_{\text{UP}}}$$

- **Directional Precision, Recall, and F1 (DOWN / SHORT)**:
  $$\text{Precision}_{\text{DOWN}} = \frac{TP_{\text{DOWN}}}{TP_{\text{DOWN}} + FP_{\text{DOWN}}}, \quad \text{Recall}_{\text{DOWN}} = \frac{TP_{\text{DOWN}}}{TP_{\text{DOWN}} + FN_{\text{DOWN}}}$$
  $$F_{1, \text{DOWN}} = 2 \times \frac{\text{Precision}_{\text{DOWN}} \times \text{Recall}_{\text{DOWN}}}{\text{Precision}_{\text{DOWN}} + \text{Recall}_{\text{DOWN}}}$$

---

## 3. Economic Simulation Metrics & Friction Modeling

All trade simulations are conducted under realistic cryptocurrency market assumptions:

| Parameter | Value | Rationale |
|:---|:---|:---|
| **Initial Capital** | \$1,000 USDT | Standard NEPTUNE experimental allocation |
| **Maker Fee** | 0.10% | Binance VIP 0 spot rate approximation |
| **Taker Fee** | 0.10% | Binance VIP 0 spot rate approximation |
| **Slippage** | 0.05% per side | Conservative execution penalty |
| **Total Round-Trip Friction** | **0.30%** | Minimum required edge to break even |
| **Max Concurrent Positions** | 2 | Risk Manager portfolio constraint |
| **Risk per Trade** | 0.50% of equity | Dynamic volatility-adjusted sizing |
| **Circuit Breaker** | 5.0% Drawdown | Automatic portfolio halts upon 5% equity loss |

---

## 4. Chronological Sampling & Lookback Protocol

1. **Evaluation Partitions**: Evaluated strictly across `OOS_HISTORICAL_REF` (2026-01-01 to 2026-07-31) and `OOS_PRISTINE` (2026-08-01 to 2026-11-01).
2. **Context Window**: 64 closed bars prior to evaluation bar $T$ ($T-63$ to $T$).
3. **Target Horizons**:
   - $H=1$: 1-step ahead (immediate momentum).
   - $H=4$: 4-steps ahead (intraday swing).
   - $H=12$: 12-steps ahead (multi-period trajectory).
4. **Sampling Stride**: Uniformly distributed chronological strides across each partition to prevent over-representation of specific sub-periods while preserving sequence diversity.

