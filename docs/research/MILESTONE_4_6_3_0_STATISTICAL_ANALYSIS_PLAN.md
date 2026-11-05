# NEPTUNE — Milestone 4.6.3.0
# Statistical Analysis Plan & Quantitative Evaluation Framework

**Milestone:** 4.6.3.0  
**Status:** FROZEN  
**Date:** 2026-11-06  
**Document Type:** Statistical Analysis Plan (SAP) & Inference Methodology  
**Significance Threshold ($\alpha$):** 0.05  
**Multiple Comparisons Correction:** Benjamini-Hochberg False Discovery Rate ($q = 0.05$)  
**Economic Significance Hurdle:** $+\$0.50\text{ USDT}$ / trade net outperformance after 0.32% friction  

---

## 1. Research Objectives & Hypotheses

The statistical analysis plan establishes formal hypothesis testing standards before running experimental backtests. It prevents p-hacking, multiple-comparison snooping, and the misinterpretation of trade-frequency reduction as predictive alpha.

### Primary Research Hypotheses
- **Hypothesis 1 ($H_1$):** Group B (News Veto) achieves a statistically significant, economically meaningful higher net expectancy per executed trade than Group A (Technical Baseline) after realistic transaction frictions (0.32% round trip):
  $$H_0^{(1)}: E[\text{Net PnL}_B] \le E[\text{Net PnL}_A] \quad \text{vs.} \quad H_A^{(1)}: E[\text{Net PnL}_B] > E[\text{Net PnL}_A]$$
- **Hypothesis 2 ($H_2$):** Group B achieves higher net expectancy per executed trade than Group C (Frequency-Matched Control):
  $$H_0^{(2)}: E[\text{Net PnL}_B] \le E[\text{Net PnL}_C] \quad \text{vs.} \quad H_A^{(2)}: E[\text{Net PnL}_B] > E[\text{Net PnL}_C]$$
  *(Rejection of $H_0^{(2)}$ proves that outperformance is not an artifact of simply taking fewer trades.)*
- **Hypothesis 3 ($H_3$):** Group B achieves higher net expectancy per executed trade than Group D (Exposure-Matched Control):
  $$H_0^{(3)}: E[\text{Net PnL}_B] \le E[\text{Net PnL}_D] \quad \text{vs.} \quad H_A^{(3)}: E[\text{Net PnL}_B] > E[\text{Net PnL}_D]$$
  *(Rejection of $H_0^{(3)}$ proves that outperformance is not an artifact of reduced market exposure duration.)*

---

## 2. Evaluation Metrics Hierarchy

### 2.1 Primary Quantitative Metrics
1. **Net Expectancy Per Executed Trade ($E$):**
   $$E = \frac{1}{N} \sum_{i=1}^N \text{Net PnL}_i$$
   where $\text{Net PnL}_i = \text{Gross PnL}_i - \text{Total Fees}_i - \text{Total Slippage}_i - \text{Total Spread}_i$.
2. **Net Portfolio Return After Costs ($R_{\text{net}}$):**
   $$R_{\text{net}} = \frac{\text{Final Equity} - \text{Initial Capital}}{\text{Initial Capital}} \times 100\%$$
3. **Maximum Portfolio Drawdown ($\text{MDD}$):**
   $$\text{MDD} = \max_{t \in [0, T]} \left( \frac{\text{Peak Equity}_t - \text{Current Equity}_t}{\text{Peak Equity}_t} \right) \times 100\%$$
4. **Profit Factor ($\text{PF}$):**
   $$\text{PF} = \frac{\sum_{i: \text{Net PnL}_i > 0} \text{Net PnL}_i}{\sum_{j: \text{Net PnL}_j < 0} |\text{Net PnL}_j|}$$

### 2.2 Secondary Quantitative Metrics
- **Win Rate ($\text{WR}$):** Proportion of trades with $\text{Net PnL} > 0$, reported with **95% Wilson Score Confidence Intervals**.
- **Annualized Sharpe Ratio ($\text{SR}$):** Calculated on daily portfolio return series using zero risk-free rate.
- **Sortino Ratio:** Penalizes downside volatility only.
- **Payoff Ratio:** $\text{Average Win} / \text{Average Loss}$.
- **Trade Frequency:** Number of executed trades per calendar month.
- **Market Exposure:** Percentage of total simulation bars where portfolio held $\ge 1$ active position.
- **Capital Utilization:** Average percentage of total equity committed to active margin/notional.
- **Average Holding Duration:** Mean trade duration in bars and hours.
- **Total Transaction Friction Breakdown:** Cumulative USDT consumed by taker fees, slippage, and bid-ask spread.
- **Conditional Stratification:**
  - By Asset: `BTCUSDT`, `ETHUSDT`, `BNBUSDT`.
  - By Timeframe: `15m`, `1h`, `4h`, `1d`.
  - By Market Regime: `TRENDING_BULL`, `TRENDING_BEAR`, `RANGING`, `VOLATILE`.
  - By Event Category: Veto breakdown across all 13 taxonomy categories.

---

## 3. Statistical Testing Methodology

### 3.1 Paired Sample Comparisons
Candidate trade signals are common across Group A and Group B. When Group B vetoes a signal that Group A executes:
- The pair $(X_{A, i}, X_{B, i})$ forms a matched pair where $X_{B, i} = 0$ (unexecuted trade, zero PnL, zero fee).
- **Wilcoxon Signed-Rank Test:** Applied to paired trade outcome differences $(d_i = \text{Net PnL}_{B, i} - \text{Net PnL}_{A, i})$ to evaluate directional dominance without assuming normal distribution.
- **Paired t-Test:** Reported alongside Wilcoxon as a parametric benchmark.

### 3.2 Block-Bootstrap Resampling
Financial returns exhibit volatility clustering and serial autocorrelation. Standard i.i.d. bootstrap resampling underestimates confidence interval width.
- **Method:** Moving Block Bootstrap (MBB).
- **Block Size:** $b = 48\text{ bars}$ (12 hours on $15\text{m}$; preserves intraday volatility dependency).
- **Iterations:** $B = 2,000\text{ resamples}$.
- **Output:** Non-parametric 95% confidence intervals for Net Expectancy, Sharpe Ratio, and Maximum Drawdown.

### 3.3 Multiple Testing Correction
When evaluating secondary hypotheses across multiple assets (3), timeframes (4), and event categories (13):
- **False Discovery Rate (FDR):** Controlled using the **Benjamini-Hochberg (BH) procedure** at target $q = 0.05$.
- P-values are ranked $p_{(1)} \le p_{(2)} \le \dots \le p_{(m)}$, and significance is declared only for $p_{(k)} \le \frac{k}{m} q$.
- Raw p-values must never be interpreted in isolation without FDR adjustment.

---

## 4. Economic Significance & Decision Thresholds

Statistical significance ($p < 0.05$) alone is insufficient to warrant strategy deployment. An outcome is declared **successful** only when it satisfies both statistical and economic hurdles:

$$\Delta E = E_B - E_A \ge \$0.50\text{ USDT per trade}$$
$$\text{Cost Ratio} = \frac{\Delta E}{\text{Round-Trip Friction (0.32\%)}} \ge 1.50$$

### Critical Anti-Patterns Explicitly Prohibited:
1. **Win-Rate Fallacy:** A higher win rate that produces a lower profit factor or larger left-tail losses is a failure.
2. **Trade Reduction Artifact:** Lower total losses resulting purely from fewer trades is not alpha. Performance must exceed Group C (Frequency-Matched) and Group D (Exposure-Matched).
3. **Syndication Overcounting:** Multiple news articles covering the same event cluster must never be treated as independent sample points ($N_{\text{independent}} \ne N_{\text{articles}}$).

---

## 5. Machine-Readable Configuration

The complete statistical configuration is exported to:  
`storage/exports/milestone_4_6_3_0/statistical_evaluation_configuration.json`
