# NEPTUNE — Candidate A: Dual-Timeframe Feasibility Review
## Higher-Timeframe Trend Following (`SHR-001` / `htf_trend_following_v1`)

> **Document ID:** `docs/research/NEPTUNE_SHR001_DUAL_TIMEFRAME_FEASIBILITY.md`  
> **Repository:** Project NEPTUNE Research Governance  
> **Classification:** Strategy Feasibility & Architectural Specification  
> **Status:** Completed Research Feasibility Study  
> **Date:** 2026-11-07  
> **Governing Rules:** Rule S-01, Rule S-04, Rule S-05, Rule S-06, Rule S-07, Rule A-09, Rule A-10  
> **Related Documents:**  
> - [`docs/research/NEPTUNE_STRATEGY_RESEARCH_RESET.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_STRATEGY_RESEARCH_RESET.md)  
> - [`docs/research/NEPTUNE_STRATEGY_HYPOTHESIS_REGISTER.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_STRATEGY_HYPOTHESIS_REGISTER.md)  
> - [`docs/research/NEPTUNE_EXPERIMENT_SELECTION_GATES.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_EXPERIMENT_SELECTION_GATES.md)  
> - [`docs/research/NEPTUNE_SHR001_STATISTICAL_POWER_PLAN.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_SHR001_STATISTICAL_POWER_PLAN.md)  
> - [`docs/research/NEPTUNE_SHR001_EXECUTION_AND_RISK_REQUIREMENTS.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_SHR001_EXECUTION_AND_RISK_REQUIREMENTS.md)  

---

## 1. Executive Summary & Review Verdict

This feasibility review evaluates whether transitioning `SHR-001` (Higher-Timeframe Trend Following) from a monolithic 4h cadence to a **Dual-Timeframe Architecture (4h regime conditioning + 1h swing-structure entry)** resolves the sample-size feasibility blocker identified in Gate 5 without destroying the economic rationale or violating portfolio risk constraints.

```
+=======================================================================================+
|                              FORMAL FEASIBILITY VERDICT                               |
|                                                                                       |
|                       FEASIBLE WITH UNRESOLVED REQUIREMENTS                           |
|                                                                                       |
|  Summary: The dual-timeframe architecture is conceptually sound, substantially         |
|  improves risk-to-reward geometry, and eliminates high-frequency frictional attrition. |
|  However, effective sample size, cross-asset correlation clustering, and dynamic      |
|  execution gap modeling remain unresolved prerequisites prior to experiment           |
|  authorization. No historical simulation or backtest is authorized.                 |
+=======================================================================================+
```

---

## 2. Phase 1 — Verification of the Economic Hypothesis

### 2.1 Market Behavior Generating Return
The economic driver of trend following is **delayed information diffusion and persistent multi-day capital reallocation** across crypto-asset markets. When institutional flows, macroeconomic liquidity shifts (e.g., policy rate pivots, ETF accumulation), or sustained network adoption enter crypto assets, the capital deployment cannot occur in a single trading session without causing catastrophic market impact. 

Consequently, large participants accumulate or distribute inventory algorithmically over days or weeks. This generates serially correlated directional price movement on multi-day horizons. The strategy captures a fraction of this persistent momentum.

### 2.2 Why the 4h Timeframe Identifies a Persistent Directional Regime
The 15m timeframe is dominated by microstructural noise, high-frequency liquidity sweeps, Asian/London/NY session handover volatility, and intraday funding rate settlement oscillations. 

A single 4h candle aggregates 16 discrete 15m intervals (or 240 minutes of continuous trading). This aggregation acts as a physical low-pass frequency filter:
1. Microstructural order-book imbalances and stop-run wicks are absorbed inside the candle body.
2. The 4h trend vectors represent accumulated net capital commitment across multiple regional trading sessions.
3. Directional regime indicators computed on 4h (e.g., EMA 50 / EMA 200 relationships and ADX) measure multi-day drift rather than intra-session mean reversion.

### 2.3 Why 1h Swing-Structure Entries Improve Execution Rather Than Merely Increasing Turnover
A pure 4h entry operates with significant execution coarseness. Entering on a 4h candle close requires placing the protective stop loss beyond a 4h swing low ($3.5\% - 6.0\%$ price distance). Under NEPTUNE's fixed $0.5\%$ risk-per-trade rule, this wide stop forces position sizes down to small fractions of equity and results in poor reward-to-risk geometry.

By nesting a 1h execution timeframe within the 4h directional regime:
- **Structural Stop Compression:** The entry triggers strictly upon a confirmed 1h break of local swing structure (e.g., higher high following a pullback). The stop is placed beyond the 1h structural swing pivot ($1.2\% - 2.2\%$ distance).
- **Asymmetric Payoff Amplification:** Compressing the initial risk distance while targeting a 4h macro expansion ($6.0\% - 12.0\%$) expands the theoretical Risk/Reward ratio from $\approx 1.5:1$ to $\ge 3.0:1$.
- **Turnover Guardrail:** To prevent this design from degenerating into high-frequency churn, **the strategy must enforce a Strict Single-Active-Order Rule per 4h regime wave**. Repeated 1h entries within the same 4h trend impulse are strictly forbidden.

### 2.4 Invalidation Conditions
The economic hypothesis is invalidated when:
1. **Prolonged Range-Bound Grinds (Macro Consolidation):** The market enters horizontal trading ranges where 4h trend filters generate lagging bullish signals near range resistance, followed immediately by mean reversion.
2. **V-Shaped Structural Reversals:** Sudden macroeconomic or regulatory news shocks that reverse trends without forming a topping consolidation, trapping trend positions at local extremes.
3. **Volatility Contraction / Attrition:** ATR collapses below transaction friction thresholds, causing stop distances to become narrower than market noise, resulting in sequential whipsaw stop-outs.

### 2.5 Outperformance Mechanism Over a 4h-Only Approach
| Metric / Attribute | Pure 4h Trend Following (A1) | Dual-Timeframe 4h/1h (A2) | Advantage Mechanism |
|---|---|---|---|
| **Stop Distance** | $3.5\% - 6.0\%$ | $1.2\% - 2.2\%$ | 60% tighter risk bracket |
| **Capital Allocation** | $\$80 - \$140$ notional | $\$220 - \$410$ notional | Higher position sizing per $0.5\%$ risk budget |
| **Gross Profit on 6% Move** | $+\$4.80 - +\$8.40$ USDT | $+\$13.20 - +\$24.60$ USDT | $\approx 2.8\times$ higher gross dollar gain |
| **Entry Timing** | Bar close every 4 hours | Hourly close after pullback shift | Avoids buying 4h breakout climax |
| **Trade Opportunity Rate** | $5 - 8$ per symbol/year | $14 - 24$ per symbol/year | Reduces sample starvation |

### 2.6 Expected Source of Edge Beyond Indicator Confluence
The edge does **not** arise from moving average line crosses. The source of edge is twofold:
1. **Liquidity Asymmetry:** Entering at the precise location where counter-trend intraday sellers are forced to cover their positions (market structure break on 1h), creating forced buying momentum.
2. **Mathematical Asymmetry:** Achieving a structural win rate of $38\% - 45\%$ with a realized payoff ratio $\ge 2.5:1$ creates robust positive net expectancy:
   $$E_{\text{net}} = (0.40 \times 2.5\text{R}) - (0.60 \times 1.0\text{R}) - \text{Friction} = 1.00\text{R} - 0.60\text{R} - 0.15\text{R} = +0.25\text{R} > 0$$

---

## 3. Phase 2 — Sample-Size Feasibility & Statistical Power

### 3.1 Forensic Analysis of the "15–25 Trades/Year" Estimate
The previous estimate of $15 - 25$ trades per year was derived from a **single-symbol pure 4h trend model** (Candidate A1):
- A 1-year partition contains 2,196 4h candles per symbol.
- High-conviction 4h trend regimes (ADX $> 25$, EMA stack aligned, multi-day expansion) occur only $4 - 7$ times per calendar year on Bitcoin.
- Across a single asset, a selective 4h system yields at most $6 - 9$ trades. 
- Across three symbols (`BTCUSDT`, `ETHUSDT`, `BNBUSDT`), unconstrained raw signals sum to $\approx 18 - 27$ setups.

### 3.2 The Pseudo-Replication Hazard: Cross-Asset Correlation
Treating signals across BTC, ETH, and BNB as independent observations is statistically fraudulent:
- In crypto spot markets, cross-asset return correlation during macro trends frequently exceeds $\rho = 0.80$.
- When a market-wide liquidity wave hits, BTC, ETH, and BNB generate simultaneous buy signals.
- If these 3 trades are executed simultaneously, they represent **a single correlated market bet**, not 3 independent tests of the hypothesis.
- **Effective Sample Size ($N_{\text{eff}}$):** Under strong cross-correlation ($\bar{\rho} \approx 0.75$), the effective sample size for 3 concurrent trades is:
  $$N_{\text{eff}} = \frac{N}{1 + (N - 1)\bar{\rho}} = \frac{3}{1 + 2(0.75)} = \frac{3}{2.5} = 1.20$$
  Three concurrent trades provide the statistical information of only $1.2$ independent trades!

### 3.3 Serial Dependence of 1h Entries Within a 4h Wave
If a 4h trend continues for 3 weeks, a 1h system might generate 5 consecutive pullback entries. These 5 trades are **serially dependent**:
- If the 4h trend is genuine, all 5 trades may win.
- If the 4h trend is a bull trap, all 5 trades will lose.
- **Rule:** Repeated entries inside a single 4h wave must be modeled as a dependent cluster.

### 3.4 Distinct Macro Regimes in 2024 Development Data
In 1 calendar year (2024), the crypto market experienced only **5 to 7 distinct macro structural regimes** (e.g., Pre-ETF anticipation, Post-ETF selloff, Q1 Spring expansion, Q2–Q3 Summer consolidation range, August unwind, Q4 election rally).
The true macro degrees of freedom in 2024 is bounded by $K \approx 6$, regardless of whether the execution model takes 15 trades or 150 trades.

### 3.5 Statistical Power Conclusion
As formally documented in [`docs/research/NEPTUNE_SHR001_STATISTICAL_POWER_PLAN.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_SHR001_STATISTICAL_POWER_PLAN.md):
Because true population variance, trade covariance, and realized payoff distributions cannot be empirically measured without loading historical market observations (which is strictly forbidden), **statistical power cannot yet be formally certified**. 

---

## 4. Phase 3 — Cost & Execution Feasibility

### 4.1 Frictional Cost Baseline
NEPTUNE maintains a frozen round-trip transaction friction of **0.32%**:
- Taker Fee: $0.10\%$ entry $+ 0.10\%$ exit $= 0.20\%$
- Slippage: $0.05\%$ entry $+ 0.05\%$ exit $= 0.10\%$
- Half-Spread: $0.01\%$ entry $+ 0.01\%$ exit $= 0.02\%$
- **Total Round-Trip Friction:** $0.32\%$ of trade notional.

### 4.2 Frictional Resistance Comparison: 15m vs. 1h vs. 4h
| Dimension | Baseline 15m (`trend_v1`) | Dual-Timeframe 1h/4h (A2) | Pure 4h Trend (A1) |
|---|---|---|---|
| **Average Stop Distance** | $0.60\% - 0.90\%$ | $1.50\% - 2.20\%$ | $4.00\% - 6.00\%$ |
| **Target Profit Distance** | $1.20\% - 1.50\%$ | $4.50\% - 7.50\%$ | $8.00\% - 15.00\%$ |
| **Round-Trip Friction** | $0.32\%$ | $0.32\%$ | $0.32\%$ |
| **Friction / Stop Ratio** | **$35.5\% - 53.3\%$** | **$14.5\% - 21.3\%$** | **$5.3\% - 8.0\%$** |
| **Friction / Target Ratio** | **$21.3\% - 26.7\%$** | **$4.3\% - 7.1\%$** | **$2.1\% - 4.0\%$** |

**Crucial Finding:** On the 15m baseline, friction consumed over $35\%$ of the stop distance and $>20\%$ of the target. On the Dual-Timeframe A2 design, friction drops to **$<7\%$ of the target move**, providing massive structural headroom for net positive expectancy.

### 4.3 Theoretical Target vs. Realized Return
A strategy backtest often models a static $+3.0\text{R}$ take-profit. In live execution, realized winning returns are substantially lower due to:
1. **Dynamic Trailing Stops:** Trailing stops lock in profit during trend exhaustion, averaging $1.8\text{R} - 2.4\text{R}$ rather than the full $3.5\text{R}$.
2. **Opening Gap Slippage:** 1h bar openings can gap adversely during high-volatility news releases, filling stop losses below the stop price.
3. **Execution Gap Buffer:** A realistic simulation must penalize stop exits by an extra $0.05\% - 0.10\%$ to account for order-book gapping.

### 4.4 Reconciliation of Historical "56% Cost" Claim
The historical assertion that "costs consumed 56% of gross returns" in Milestone 4.6.3.1 was an artifact of defective trade partitioning. 

In the certified corrected portfolio ledger ([`docs/research/MILESTONE_4_6_3_1_2_HISTORICAL_REPRODUCTION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_2_HISTORICAL_REPRODUCTION.md)):
- Gross Losses: $-\$40.25$ USDT
- Gross Profits: $+\$37.98$ USDT
- Gross P&L: $-\$2.27$ USDT
- Total Transaction Costs: $-\$21.29$ USDT (Fees: $-\$13.31$, Slippage: $-\$6.65$, Spread: $-\$1.33$)
- Realized Net P&L: $-\$23.56$ USDT

**Reconciled Fact:** Transaction costs did not consume a positive return; rather, **costs were $9.4\times$ larger than the gross loss itself**, transforming a marginally flat trading system into a catastrophic drawdown breaker trip within 12 trades. Candidate A2's multi-day holding period directly cures this hyper-turnover pathology.

---

## 5. Phase 4 — Long-Only Spot Portfolio Feasibility

### 5.1 Long-Only Spot Exposure Invariant
NEPTUNE v1 operates strictly under spot paper trading rules without leverage or borrowing (Rule S-01):
1. **Zero Shorting:** Physical short selling is structurally impossible in spot without margin borrowing. Synthetic shorting introduced cash-lockup distortions. Candidate A operates **strictly Long-Only**.
2. **Cash Preservation:** When 4h market regime is BEARISH or RANGING, the portfolio holds **100% liquid cash (USDT)**.

### 5.2 Balance Sheet Accounting & Sizing Policy
- **Cash Reservation:** Long orders debit liquid cash:
  $$\Delta C_{\text{out}} = S \cdot P_{\text{entry}} \times (1 + f_{\text{taker}})$$
- **Position Sizing Equation:**
  $$S = \min\left( \frac{\text{Equity} \times \text{RiskPct}}{P_{\text{entry}} - P_{\text{stop}}}, \frac{\text{Available Cash} \times 0.40}{P_{\text{entry}} \times (1 + f_{\text{taker}})} \right)$$
  Where $\text{RiskPct} = 0.50\%$ of equity (\$5.00 on \$1,000 portfolio).
- **Maximum Concurrent Positions:** $N_{\max} = 2$.
- **Maximum Committed Portfolio Capital:** $\le 80\%$. At least $20\%$ unencumbered cash must remain idle at all times.

### 5.3 Risk-Breaker Integration & In-Flight Position Policy
- **5.0% Drawdown Circuit Breaker:** If marked-to-market equity drops $\ge 5.0\%$ from the high-water mark, the breaker trips immediately.
- **Order Embargo:** No new orders may be evaluated or submitted.
- **In-Flight Position Resolution:** Active positions are **not** market-dumped at breaker trip. They continue to be managed strictly by their pre-registered brackets (stop loss or trailing stop).
- **Buffer Requirement:** Because 2 concurrent positions could simultaneously stop out ($2 \times 0.5\% = 1.0\%$), the strategy must maintain a **1.0% risk headroom buffer** ($MDD_{\text{target}} \le 4.0\%$) to prevent an in-flight stopout from breaching the $5.0\%$ circuit breaker.

---

## 6. Phase 5 — Comparison of Three Conceptual Candidate A Designs

```mermaid
flowchart TD
    subgraph A1 ["Candidate A1: Pure 4h Trend Following"]
        A1_Regime["4h Trend Filter"] --> A1_Entry["4h Candle Close Breakout"]
        A1_Entry --> A1_Stop["4h Structural Stop (3.5% - 6.0%)"]
    end

    subgraph A2 ["Candidate A2: Dual-Timeframe (4h Regime + 1h Swing)"]
        A2_Regime["4h Trend Filter<br>(EMA 50/200 + ADX > 25)"] --> A2_Wait["Wait for 1h Pullback"]
        A2_Wait --> A2_Entry["1h Swing High Break Close"]
        A2_Entry --> A2_Stop["1h Structural Stop (1.5% - 2.2%)"]
    end

    subgraph A3 ["Candidate A3: Dual-Timeframe (4h Regime + 1h Limit Pullback)"]
        A3_Regime["4h Trend Filter<br>(EMA 50/200 + ADX > 25)"] --> A3_Limit["1h Limit Order at 21-EMA"]
        A3_Limit --> A3_Stop["1h Volatility Stop (1.0% - 1.5%)"]
    end
```

### Comprehensive Multi-Dimensional Comparison Matrix

| Evaluation Dimension | Design A1: Pure 4h Trend | Design A2: 4h Regime + 1h Swing Structure | Design A3: 4h Regime + 1h Pullback Limit |
|---|---|---|---|
| **1. Economic Mechanism** | Captures macro breakout impulses on 4h candle closes. | Waits for 4h trend, captures 1h counter-trend seller exhaustion. | Buys falling knife pullbacks into dynamic 1h moving average support. |
| **2. Trade Frequency (Est.)** | $15 - 25$ trades/year (3 symbols combined). | $45 - 75$ trades/year (3 symbols combined). | $60 - 90$ trades/year (3 symbols combined). |
| **3. Expected Holding Period** | $4 - 14$ calendar days. | $1.5 - 4$ calendar days (36 to 96 hours). | $1 - 3$ calendar days (24 to 72 hours). |
| **4. Turnover Implications** | Extremely low ($\approx 0.5$ trades/month/pair). | Moderate ($\approx 1.5$ trades/month/pair). | Moderate-High ($\approx 2.0$ trades/month/pair). |
| **5. Cost Sensitivity** | Minimal ($0.32\%$ is $<3\%$ of target). | Low ($0.32\%$ is $<7\%$ of target). | Moderate ($0.32\%$ is $\approx 10\%$ of target). |
| **6. Correlation Risk** | Severe (BTC, ETH, BNB trigger on same 4h bar). | Moderate (1h swing breaks occur at staggered hours). | Moderate-High (all 3 pairs hit limits together). |
| **7. Primary Failure Mode** | Lag: buying the top of 4h expansion candles. | False structural shift in choppy range. | Limit order filled during severe trend breakdown. |
| **8. Data Requirements** | 4h OHLCV candles only. | Synchronized 4h and 1h closed candle streams. | Synchronized 4h and 1h order book / limit simulation. |
| **9. Statistical Feasibility** | **FAIL** ($N < 25$ causes bootstrap collapse). | **MARGINAL / VIABLE** ($N \approx 45-75$, $N_{\text{eff}} \approx 30$). | **VIABLE** ($N \approx 60-90$). |
| **10. Falsification Criterion** | Net profit factor $< 1.20$ over 2 trending quarters. | $> 4$ consecutive 1h stop-outs within one 4h regime. | Price routinely slices through limit support without bouncing. |

**Evaluation Verdict on A1/A2/A3:**
- **Design A1 is structurally rejected** due to sample-size starvation ($N < 25$).
- **Design A3 is rejected** because limit order pullback fills suffer from adverse selection (limit orders only fill when market is aggressively dropping, causing high stopout rates).
- **Design A2 is the superior architecture:** It combines macro trend discipline with structural micro-confirmation, providing the optimal trade-off between sample adequacy, frictional resistance, and risk-to-reward geometry.

---

## 7. Phase 6 — Experiment Prerequisites

Before any future Development experiment for Candidate A2 can be considered for authorization, the following 13 items must be formally documented and frozen:

1. **Deterministic Strategy Specification:** Complete mathematical definition of 4h EMA 50/200, 4h ADX(14) threshold, 1h swing-pivot detection lookback (e.g., 5-bar fractal), and market-structure-shift confirmation rule.
2. **Entry & Exit Rules:** Strict closed-candle execution at `NEXT_ELIGIBLE_PRICE` (Bar $T+1$ Open). Conservative intra-bar bracket resolution.
3. **Risk & Sizing Policy:** $0.5\%$ risk per trade, strictly long-only, max 2 concurrent positions, max $80\%$ capital commitment.
4. **Execution Policy:** Frozen taker fee ($0.10\%$), slippage ($0.05\%$), and spread ($0.01\%$).
5. **Symbol & Timeframe Selection:** `BTCUSDT`, `ETHUSDT`, `BNBUSDT` on synchronized `4h` and `1h` partitions.
6. **Opportunity Definition:** Pre-registered rule defining when a 1h signal constitutes an independent opportunity vs. a duplicate wave entry.
7. **Statistical Analysis Plan (SAP):** Pre-registered block bootstrap (MBB) with 96-bar (4-day) blocks, null-centered resampling ($H_0: \mu \le 0$), continuous time-grid mapping, and Benjamini-Hochberg FDR control.
8. **Primary & Secondary Metrics:** Net Expectancy ($E_{\text{net}} \ge +\$0.50$ USDT), Profit Factor ($\ge 1.40$), Max Drawdown ($< 4.0\%$).
9. **Economic Hurdle:** Net dollar expectancy hurdle $+\$0.50$ USDT per trade.
10. **Risk-Breaker Success Criteria:** Maximum portfolio drawdown strictly $< 4.50\%$ (zero circuit breaker activations across 2024 Development).
11. **Cryptographic Fingerprint:** Composite SHA-256 hash freezing code, configuration, and data manifests.
12. **Independent Forensic Audit Plan:** Automated balance sheet invariant checks ($\text{tolerance} \le \$0.05$), HMAC token lifecycle verification, and export validation.
13. **Multiple Testing Governance:** Pre-registration of an exploration penalty: any iterative parameter tweak on 2024 Development requires adjusting the significance threshold $\alpha$ via Holm-Bonferroni correction.

---

## 8. Final Decision & Justification

$$\mathbf{FEASIBILITY\ VERDICT:}\quad\mathbf{FEASIBLE\ WITH\ UNRESOLVED\ REQUIREMENTS}$$

### Justification:
1. **Conceptual Soundness:** The dual-timeframe architecture (A2) successfully resolves the frictional and payoff limitations of the baseline 15m strategy while avoiding the execution coarseness of pure 4h trend following.
2. **Remaining Unresolved Blockers:**
   - **Gate 2 (Deterministic Spec):** The strategy rules remain in conceptual proposal form. Complete mathematical code has not been implemented or frozen.
   - **Gate 5 (Empirical Sample Adequacy):** While the dual-timeframe structure plausibly increases trade count to $45 - 75$ trades, the true cross-asset correlation and effective sample size ($N_{\text{eff}}$) cannot be verified without historical execution.
   - **Gate 8 (Risk Breaker Headroom):** The strategy must demonstrate that a 2-asset correlated stopout during a market-wide reversal will not breach the $5.0\%$ circuit breaker.
3. **Governance Stance:** This feasibility study does **NOT** authorize a backtest or simulation. It establishes the quantitative prerequisites that must be met before an experimental proposal can be submitted to the Governance Committee.
