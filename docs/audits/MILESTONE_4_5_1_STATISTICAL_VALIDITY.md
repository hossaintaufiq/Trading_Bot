# NEPTUNE Milestone 4.5.1 — Audit C: Statistical Forecasting Validity & Baseline Benchmarks

**Audit Date:** 2026-11-02  
**Baseline Commit:** `f0957a0` / `22ab286`  
**Dataset Version:** `v2.0.0`  
**Evaluation Origins:** 450 Unique Origin Points ($N=450$ per horizon, 1,350 total predictions)  
**Audit Scope:** Independent recomputation of MAE, RMSE, MAPE, Directional Accuracy, Precision, Recall, F1; benchmark comparison against 4 naive baselines; hypothesis testing and confidence intervals.

---

## 1. Executive Summary & Verdict

* **Audit Verdict:** **PASS WITH CRITICAL STATISTICAL LIMITATIONS**
* **Recomputation Parity:** All MAE, RMSE, MAPE, and directional accuracy metrics published in Milestone 4.5 were independently verified and recomputed with 100% numerical parity.
* **Statistical Significance Test ($H_0: p = 0.50$):**
  - **Horizon $H=1$:** Directional accuracy of **52.44%** ($k=236, N=450$) yields a two-sided binomial test p-value of **$p = 0.3222$**. It is **NOT statistically significant** ($\alpha = 0.05$). The 95% Wilson confidence interval is **[47.83%, 57.02%]**, which comfortably spans the 50.0% null hypothesis.
  - **Horizon $H=4$:** Directional accuracy degrades to **48.44%** ($p = 0.5400$). Indistinguishable from random guessing.
  - **Horizon $H=12$:** Directional accuracy collapses to **42.67%** ($p = 0.0021$). The model is **statistically significantly worse than a coin flip** ($p < 0.01$).
* **Naive Baseline Comparison:** A simple **Previous-Close Persistence Baseline** (predicting zero price change) achieves **52.00%** directional accuracy at $H=1$ while yielding a **lower forecast error** (MAPE 0.89% vs Kronos 1.10%; MAE 213.70 vs Kronos 268.53).
* **Core Quantitative Finding:** Kronos-mini demonstrates no statistically defensible predictive edge over persistence on out-of-sample crypto data. The 52.44% accuracy at $H=1$ is within expected sampling noise of an unbiased coin toss ($Z = 1.037, p = 0.32$).

---

## 2. Recomputed Performance Across Forecast Horizons ($N=450$ Each)

All predictions from `storage/exports/milestone_4_5/forecast_predictions.parquet` were audited:

| Horizon | Sample Size ($N$) | Price MAE | Price RMSE | Price MAPE | Directional Hits ($k$) | Directional Acc | 95% Confidence Interval | Two-Sided $p$-value | Significant ($\alpha=0.05$)? |
|---|---:|---:|---:|---:|---:|---:|:---:|---:|:---:|
| **$H=1$** | 450 | 268.53 | 738.25 | **1.10%** | 236 | **52.44%** | [47.83%, 57.02%] | $p = 0.3222$ | **No (Fail)** |
| **$H=4$** | 450 | 507.79 | 1,414.28 | **2.17%** | 218 | **48.44%** | [43.86%, 53.06%] | $p = 0.5400$ | **No (Fail)** |
| **$H=12$** | 450 | 1,049.17 | 2,723.07 | **4.41%** | 192 | **42.67%** | [38.18%, 47.28%] | $p = 0.0021$ | **Significant (Worse)** |
| **AGGREGATE** | 1,350 | 608.50 | 1,822.12 | **2.56%** | 646 | **47.85%** | [45.19%, 50.53%] | $p = 0.1208$ | **No (Fail)** |

### Classification Quality Metrics (Long Class)

| Horizon | Directional Precision | Directional Recall | $F_1$ Score | MFE (Forecast Bias) |
|---|---:|---:|---:|---:|
| **$H=1$** | 51.22% | 57.53% | 54.19 | -5.67 |
| **$H=4$** | 50.00% | 51.29% | 50.64 | -81.18 |
| **$H=12$** | 43.87% | 52.44% | 47.77 | -51.82 |
| **OVERALL** | 48.21% | 53.70% | 50.80 | -46.22 |

The negative Mean Forecast Error (MFE = -46.22) reveals a persistent downward forecast bias (underpredicting prices during bullish regimes).

---

## 3. Four-Baseline Benchmark Comparison

To rigorously determine whether Kronos provides any incremental informational edge, four deterministic benchmarks were executed on the exact same 450 origins:

1. **Baseline 1 & 2 (Persistence / Random Walk without Drift):**
   $$\hat{y}_{T+k} = y_T$$
   Direction benchmarked against fair coin / random walk.
2. **Baseline 3 (Momentum / Previous-Candle Direction Persistence):**
   $$\hat{\text{dir}}_{T+k} = \text{sign}(y_T - y_{T-1})$$
3. **Baseline 4 (Historical Window Drift):**
   $$\hat{r} = \frac{1}{24}\sum_{i=0}^{23} r_{T-i}, \quad \hat{y}_{T+k} = y_T (1 + \hat{r} \cdot k)$$

### Comparative Benchmark Results Matrix

```
===================================================================================================
HORIZON H=1 (N=450):
  Model / Baseline              Directional Acc   p-value     Price MAPE   Price MAE     F1 Score
---------------------------------------------------------------------------------------------------
  Kronos-mini                   52.44%            p=0.3222    1.10%        $268.53       54.19
  B1/B2 Persistence (RW)        52.00%            p=0.4229    0.89%        $213.70       52.00
  B3 Momentum Persistence       49.33%            p=0.8137    0.89%        $213.70       49.12
  B4 Historical Drift (24-bar)  48.67%            p=0.6041    0.92%        $222.21       48.55
===================================================================================================
HORIZON H=4 (N=450):
  Model / Baseline              Directional Acc   p-value     Price MAPE   Price MAE     F1 Score
---------------------------------------------------------------------------------------------------
  Kronos-mini                   48.44%            p=0.5400    2.17%        $507.79       50.64
  B1/B2 Persistence (RW)        50.44%            p=0.8876    1.77%        $421.62       50.44
  B3 Momentum Persistence       44.67%            p=0.0266    1.77%        $421.62       44.49
  B4 Historical Drift (24-bar)  49.33%            p=0.8137    2.12%        $512.02       49.20
===================================================================================================
HORIZON H=12 (N=450):
  Model / Baseline              Directional Acc   p-value     Price MAPE   Price MAE     F1 Score
---------------------------------------------------------------------------------------------------
  Kronos-mini                   42.67%            p=0.0021    4.41%      $1,049.17       47.77
  B1/B2 Persistence (RW)        51.56%            p=0.5400    3.49%        $837.41       51.56
  B3 Momentum Persistence       48.89%            p=0.6714    3.49%        $837.41       48.77
  B4 Historical Drift (24-bar)  47.78%            p=0.3704    4.50%      $1,096.77       47.62
===================================================================================================
```

### Key Comparative Insights
1. **At $H=1$:** Kronos-mini directional accuracy (52.44%) is virtually indistinguishable from naive persistence (52.00%). Crucially, naive persistence has **19% lower relative price error** (MAPE 0.89% vs 1.10%) because Kronos introduces autoregressive decoding noise that degrades point forecasts relative to the latest close.
2. **At $H=4$ and $H=12$:** Naive persistence outperforms Kronos in both directional accuracy and price error. At $H=12$, naive persistence achieves 51.56% accuracy vs Kronos's 42.67%.

---

## 4. Economic Viability Evaluation: Can 52.44% Overcome 0.30% Friction?

A common question in quantitative trading is whether an accuracy of 52.44% at $H=1$ provides an exploitable edge.

### Mathematical Expectancy Calculation
Under realistic Binance exchange friction:
- Maker fee: 0.10%
- Taker fee: 0.10%
- Slippage: 0.05% entry + 0.05% exit = 0.10%
- **Total round-trip hurdle ($c$):** **0.30%**

Let the average 1-bar price move when correct be $\bar{r}_+ \approx 1.10\%$, and when incorrect be $\bar{r}_- \approx 1.10\%$.
The net trade expectancy $E$ is:
$$E = p \cdot (\bar{r}_+ - c) - (1 - p) \cdot (\bar{r}_- + c) = (2p - 1)\bar{r} - c$$
Substituting $p = 0.5244$:
$$2p - 1 = 2(0.5244) - 1 = 0.0488 \quad (4.88\% \text{ gross edge})$$
$$\text{Gross Return} = 0.0488 \times 1.10\% = +0.0537\%$$
$$\text{Net Return} = +0.0537\% - 0.3000\% = -0.2463\% \text{ per trade}$$

Because the round-trip friction (0.30%) is more than **five times larger** than the marginal directional edge (+0.054%), trading pure 1-bar Kronos signals produces **guaranteed negative expectancy**. Every trade loses approximately 0.25% in expected value to fees and slippage.

---

## 5. Statistical Conclusion

1. Kronos directional forecasts are **not statistically distinguishable from random walk persistence** at $H=1$ or $H=4$.
2. At $H=12$, Kronos exhibits pronounced degradation ($42.67\%, p = 0.0021$), showing systematic lag and failure to capture multi-day trend continuations.
3. The model cannot be used as an autonomous trading signal generator without suffering catastrophic capital erosion from exchange fees.
