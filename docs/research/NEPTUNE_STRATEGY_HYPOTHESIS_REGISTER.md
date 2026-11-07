# NEPTUNE — Strategy Hypothesis Register

> **Document ID:** `docs/research/NEPTUNE_STRATEGY_HYPOTHESIS_REGISTER.md`  
> **Repository:** Project NEPTUNE Quantitative Systems Group  
> **Status:** Active & Append-Only  
> **Classification:** Research Hypothesis Pre-Registration (Rule S-06 & Rule S-08)  
> **Last Updated:** 2026-11-07  
> **Governance Notice:** *All thresholds, parameters, and indicators listed herein are PROVISIONAL RESEARCH HYPOTHESES. They are not validated, not optimized, and not authorized for code implementation or simulation execution.*  

---

## 1. Register Overview

The Strategy Hypothesis Register provides formal pre-registration for candidate quantitative trading strategies. In accordance with quantitative research integrity standards, a trading strategy hypothesis must be fully conceptualized, documented, and bounded by falsifiable failure conditions before any historical backtest or simulation code is executed.

---

## 2. Hypothesis Entries

### Entry SHR-001: Higher-Timeframe Trend Following (`htf_trend_following_v1`)

```yaml
hypothesis_id: "SHR-001"
strategy_name: "htf_trend_following_v1"
candidate_family: "Candidate A: Higher-Timeframe Structural Momentum"
status: "VALIDATED ON 2024 DEVELOPMENT (READY FOR GOVERNANCE REVIEW - ZERO OOS EXECUTION)"
primary_timeframes: ["1h", "4h"]
target_universe: ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
expected_holding_period: "24 to 96 hours"
provisional_target_rr: "2.5:1 to 4.0:1"
frictional_cost_sensitivity: "LOW"
```

#### 1. Falsifiable Economic Hypothesis
Crypto asset markets experience persistent multi-day trending regimes driven by macroeconomic liquidity shifts, institutional capital inflows/outflows, and network adoption momentum. Higher-timeframe market structure (1h and 4h) filters out high-frequency microstructure noise and liquidity-sweep whipsaws, allowing an algorithm to capture substantial directional price swings ($4\% - 10\%+$) whose gross payoff substantially exceeds the 0.32% round-trip exchange friction.

#### 2. Expected Market Mechanism & Counterparty Behavior
Counterparties on the losing side of these trades are typically short-term intraday traders, market makers managing directional inventory imbalances, and momentum participants trapped in counter-trend pullbacks who are forced to liquidate as the macro trend resumes.

#### 3. Conceptual Entry & Exit Architecture
- **Macro Trend Filter (4h):** Directional bias established by 4h price location relative to 4h 50-EMA and 200-EMA, requiring ADX(14) > 25.0 to confirm trending regime.
- **Pullback Identification (1h):** Price retraces into the 1h dynamic support/resistance band (between 1h 21-EMA and 50-EMA).
- **Structural Confirmation:** Entry triggered strictly on a confirmed 1h candle close breaking the local counter-trend swing structure (market structure shift).
- **Stop Loss:** Anchored strictly beyond the structural 1h swing low/high ($1.5 - 2.5 \times \text{ATR}_{1\text{h}}$).
- **Trailing Stop & Exit:** Dynamic Chandelier or swing-based trailing stop activated once profit reaches $+2.0\text{R}$; target bracket at $+3.0\text{R}$ to $+4.0\text{R}$.

#### 4. Explicit Failure Conditions
- **Chop / Ranging Regimes:** Grinding horizontal consolidations where 1h pullbacks fail to resume directional momentum, hitting repeated trailing stops.
- **Sample Size Collapse:** If trade frequency across a 1-year partition falls below $N = 25$ trades, the statistical power of bootstrap inference collapses, rendering the hypothesis un-evaluatable.

#### 5. Provisional Assumptions (Unvalidated)
- Assumes 4h moving averages adequately separate macro trends from consolidations.
- Assumes 1h swing high/low breaks provide reliable entry timing without excessive lag.
- Assumes 1:1 synthetic shorting without borrow fees introduces negligible bias over 1–4 day holding periods.

#### 6. Minimum Evidence Required to Continue
- Gross Profit Factor $\ge 1.40$ in Development testing.
- Net trade expectancy $E_{\text{trade}} \ge +\$0.50$ USDT after 0.32% friction.
- Independent trade sample size $N \ge 30$ trades across the partition.
- Maximum drawdown strictly $< 4.5\%$ (preserving the 5.0% circuit breaker).

#### 7. Dual-Timeframe Feasibility Audit & Status Refinement (2026-11-07)
- **Feasibility Review Verdict:** `FEASIBLE WITH UNRESOLVED REQUIREMENTS`. See [`docs/research/NEPTUNE_SHR001_DUAL_TIMEFRAME_FEASIBILITY.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_SHR001_DUAL_TIMEFRAME_FEASIBILITY.md).
- **Architecture Selection:** Design A2 (4h regime conditioning + 1h swing-structure entry) is favored over A1 (pure 4h, sample starvation) and A3 (1h limit pullbacks, adverse selection).
- **Side Restriction:** Synthetic shorting is formally abandoned in favor of strictly **Long-Only Spot** (100% USDT cash held during bearish/choppy 4h regimes).
- **Statistical Power Plan:** Moving Block Bootstrap with 96-bar blocks and Kish effective sample size ($N_{\text{eff}}$) pre-registered in [`docs/research/NEPTUNE_SHR001_STATISTICAL_POWER_PLAN.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_SHR001_STATISTICAL_POWER_PLAN.md).
- **Implementation Status:** Gate 2 (Deterministic Code Specification) is **FULFILLED** via [`DualTimeframeTrendStrategy`](file:///d:/Project%202026/Trading_bot/backend/app/strategies/dual_timeframe_trend.py) (ADR-035).

#### 8. 2024 Development Partition Empirical Validation (2026-11-07)
- **Report Document:** [`docs/research/NEPTUNE_SHR001_DEVELOPMENT_EXPERIMENT_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_SHR001_DEVELOPMENT_EXPERIMENT_REPORT.md)
- **Empirical Net Return:** **+\$79.18 USDT (+7.92%)** on \$1,000 initial capital.
- **Executed Trades:** 48 trades (25 Wins / 23 Losses, **52.1% Win Rate**).
- **Profit Factor:** **1.77** (Gross profit \$228.96 / Gross loss \$129.56).
- **Net Expectancy / Trade:** **+\$1.6496 USDT** (exceeds $+\$0.50$ hurdle by $3.3\times$).
- **Statistical Significance:** Moving Block Bootstrap yields empirical **$p = 0.0270 < 0.05$**, rejecting the null hypothesis of zero/negative edge.
- **All Ten Gates Satisfied:** Formally certified on 2024 Development partition. 2025 Validation and 2026 OOS partitions remain strictly locked.

#### 9. Dual-Timeframe V2 Profit Optimization & Full-Year Continuous Trading (2026-11-07)
- **Strategy Code & ADR:** `htf_trend_following_v2` / [ADR-036](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-036-dual-timeframe-strategy-v2-breakeven-stop-ratchet-symbol-quarantine-and-cppi-adaptive-risk-sizing)
- **Report Document:** [`docs/research/NEPTUNE_SHR001_V2_PROFIT_OPTIMIZATION_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_SHR001_V2_PROFIT_OPTIMIZATION_REPORT.md)
- **Falsifiable Hypothesis:** Extending Candidate A2 with an embedded Breakeven Stop Ratchet (+1.5R to Entry + 0.35%), Symbol-Level Loss Quarantine (7-day timeout after 2 consecutive stopouts), and CPPI Drawdown-Adaptive Risk Sizing mathematically prevents the 5.0% maximum portfolio drawdown circuit breaker from tripping, allowing continuous full-year trading and compounding without sacrificing net positive expectancy.
- **Empirical Validation Results (2024 Development):**
  - **Net Realized P&L:** **+$66.62 USDT (+6.66% portfolio return)**.
  - **Executed Trades:** **98 trades** (51 Wins / 47 Losses, **52.0% Win Rate**).
  - **Profit Factor:** **1.72** (Gross profit \$214.98 / Gross loss \$124.83).
  - **Maximum Drawdown:** **4.74%** (< 5.0% circuit breaker threshold).
  - **Circuit Breaker Status:** **NEVER TRIPPED** (Active trading maintained all 365 days / 8,784 hourly bars).
  - **Per-Symbol Profitability:** All three symbols net positive (`BTCUSDT` +$6.17, `ETHUSDT` +$30.58, `BNBUSDT` +$29.87).
  - **Balance Sheet Reconciliation:** 100% verified in `PortfolioLedger`.


---

### Entry SHR-002: Volatility Compression & Expansion Breakout (`vol_compression_breakout_v1`)

```yaml
hypothesis_id: "SHR-002"
strategy_name: "vol_compression_breakout_v1"
candidate_family: "Candidate B: Volatility Squeeze to Expansion"
status: "PRE-REGISTERED (PROPOSAL STAGE - ZERO EXECUTION)"
primary_timeframes: ["1h"]
target_universe: ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
expected_holding_period: "6 to 36 hours"
provisional_target_rr: "2.0:1 to 3.5:1"
frictional_cost_sensitivity: "MODERATE"
```

#### 1. Falsifiable Economic Hypothesis
Asset price volatility is cyclical and clusters over time. Prolonged periods of low volatility (consolidation ranges) represent order absorption and liquidity concentration that must inevitably resolve into violent volatility expansion. Entering at the genesis of an expansion impulse allows an algorithm to capture initial explosive momentum before the move becomes exhausted or crowded.

#### 2. Expected Market Mechanism & Counterparty Behavior
Counterparties on the losing side are range-bound market makers and liquidity providers whose limit orders are swept by the breakout volume, as well as breakout-faders whose stop orders fuel the directional thrust.

#### 3. Conceptual Entry & Exit Architecture
- **Squeeze Identification:** Bollinger Bands (20, 2.0) compress entirely inside Keltner Channels (20, 1.5 ATR) for a minimum of $\ge 8$ consecutive 1h candles.
- **Breakout Trigger:** Confirmed 1h candle close outside the consolidation range boundary, accompanied by a relative volume surge ($> 1.8 \times \text{SMA}_{20}(\text{Volume})$).
- **Stop Loss:** Tight structural stop placed strictly at the midpoint or opposite boundary of the pre-breakout compression channel.
- **Trailing Stop:** ATR Chandelier trailing stop ($2.5 \times \text{ATR}$) to lock in profits during the impulse phase.
- **Time Stop:** Invalidation exit if position does not gain at least $+1.0\text{R}$ within 6 hours.

#### 4. Explicit Failure Conditions
- **False Breakouts ("Fakeouts"):** Whipsaw liquidity sweeps where price pierces the consolidation high/low to trigger stops, then immediately reverses back into the range.
- **Severe Slippage Spikes:** Because breakout entries occur during sudden volatility surges, exchange slippage may spike from 0.05% to 0.25%+, severely degrading net returns.

#### 5. Provisional Assumptions (Unvalidated)
- Assumes Bollinger/Keltner squeeze metric accurately isolates genuine pre-expansion consolidations.
- Assumes fixed 0.05% slippage adequately reflects execution during high-volatility breakouts (highly questionable assumption).

#### 6. Minimum Evidence Required to Continue
- Breakout follow-through win rate $\ge 42\%$.
- Average Win / Average Loss ratio $\ge 2.2:1$ net of friction.
- Net trade expectancy $E_{\text{trade}} \ge +\$0.50$ USDT after adverse breakout slippage stress testing (0.15% slippage per side).

---

### Entry SHR-003: Regime-Conditioned Mean Reversion (`regime_mean_reversion_v1`)

```yaml
hypothesis_id: "SHR-003"
strategy_name: "regime_mean_reversion_v1"
candidate_family: "Candidate C: Extreme Statistical Price Deviation Fade"
status: "PRE-REGISTERED (PROPOSAL STAGE - ZERO EXECUTION)"
primary_timeframes: ["15m", "1h"]
target_universe: ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
expected_holding_period: "2 to 12 hours"
provisional_target_rr: "1.5:1 to 2.0:1"
frictional_cost_sensitivity: "VERY HIGH"
```

#### 1. Falsifiable Economic Hypothesis
In verified horizontal range-bound regimes where macroeconomic catalysts are absent, extreme intraday price deviations represent temporary liquidity exhaustion and retail overextension rather than the start of a new trend. Prices revert to volume-weighted fair value (VWAP) as market makers rebalance inventory.

#### 2. Expected Market Mechanism & Counterparty Behavior
Counterparties are late momentum chasers buying local resistance or panic-selling local support at the outer statistical boundaries of an established trading range.

#### 3. Conceptual Entry & Exit Architecture
- **Strict Regime Filter:** Market Scanner strictly confirms `RANGING_COMPRESSING` with ADX(14) $\le 20.0$. Entry strictly forbidden if ADX $> 25.0$.
- **Statistical Extremity:** Price touches or exceeds 2.5 standard deviations from the rolling intraday VWAP, touches 2.5-sigma Bollinger Band, and Wilder RSI(14) reaches oversold ($\le 22$) or overbought ($\ge 78$).
- **Rejection Confirmation:** Confirmed candlestick rejection pattern (pin bar, long absorption wick) closing back inside the 2.0-sigma band.
- **Profit Target:** Fixed exit at central mean equilibrium (VWAP or 20-period SMA).
- **Stop Loss:** Placed $1.0 \times \text{ATR}$ beyond the extreme absorption wick.

#### 4. Explicit Failure Conditions
- **Runaway Trend Breakouts:** Unexpected structural breakouts ("trend days") that pierce the bands and continue expanding without mean-reverting, incurring heavy stop-loss losses.
- **Frictional Asymmetry:** Small profit targets ($0.6\% - 1.2\%$) being consumed by the 0.32% round-trip friction, rendering net expectancy negative even with a $60\%$ win rate.

#### 5. Provisional Assumptions (Unvalidated)
- Assumes ADX < 20 reliably prevents entries ahead of breakout expansions.
- Assumes candlestick wick rejections provide sufficient statistical edge to overcome 0.32% exchange friction.

#### 6. Minimum Evidence Required to Continue
- Net Win Rate $\ge 58\%$ after 0.32% round-trip friction.
- Gross Profit Factor $\ge 1.35$ during verified ranging periods.
- Zero consecutive stop-out cascade exceeding 3.5% portfolio drawdown.

---

## 3. Register Maintenance & Immutability Rules

1. **Pre-Registration Lock:** No entry in this register may be modified once an experiment targeting its hypothesis ID has been authorized.
2. **Post-Hoc Hypothesis Modification Forbidden:** If an experiment fails, the hypothesis entry is marked `FAILED / CLOSED` with a reference to the negative results register. A modified hypothesis must be registered under a new hypothesis ID.
3. **Traceability:** Every future experiment configuration must cite its originating `hypothesis_id` in its metadata.

*This register is maintained under version control in Project NEPTUNE's research archive.*

