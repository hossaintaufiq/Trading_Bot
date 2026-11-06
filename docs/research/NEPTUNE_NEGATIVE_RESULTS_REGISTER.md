# NEPTUNE — Negative Results Register

> **Document ID:** `docs/research/NEPTUNE_NEGATIVE_RESULTS_REGISTER.md`  
> **Repository:** Project NEPTUNE Research Archive  
> **Status:** Active & Append-Only  
> **Last Updated:** 2026-11-07  
> **Classification:** Research Integrity Record (Rule S-06 & Rule S-07)  

---

## 1. Purpose & Scientific Rationale

In quantitative finance, negative findings are as scientifically valuable as positive discoveries. Suppressing or silently altering unsuccessful experiments introduces publication bias, encourages data mining, and leads to recurring capital destruction.

In strict compliance with **Rule S-06** ("Never fabricate market data, agent decisions, or performance metrics") and **Rule S-07** ("Never claim profitability without validated, reproducible evidence"), this Negative Results Register serves as the authoritative, permanent ledger of:
1. Hypotheses evaluated and found to have negative net expectancy.
2. Market regimes and configurations where specific trading rules failed.
3. Quantified performance drag from transaction costs and slippage.
4. Methodological and computational pitfalls identified during empirical testing.

---

## 2. Register of Negative Findings

### Entry NRR-001: 15-Minute Technical Trend Continuation (`trend_continuation_v1`)

```yaml
hypothesis_id: "HYP-TECH-001"
strategy_name: "trend_continuation_v1"
milestone_tested: "Milestone 4.6.3.1 - 4.6.3.1.3"
timeframe: "15m"
partition: "2024 Development (105,408 candles across BTC, ETH, BNB)"
execution_policy: "NEXT_ELIGIBLE_PRICE (Bar T+1 Open)"
cost_model: "0.10% taker fee, 0.05% slippage, 0.01% spread (0.32% round trip)"
status: "UNSUCCESSFUL UNDER TESTED 2024 DEVELOPMENT CONDITIONS"
```

- **Observed Metrics:**
  - Net Realized PnL: $-\$23.57$ USDT ($-2.36\%$ portfolio return).
  - Executed Trades: 12 trades (3 wins, 9 losses).
  - Win Rate: $25.0\%$ (95% Wilson CI: $[8.9\%, 53.2\%]$).
  - Net Expectancy per Trade: $-\$1.964$ USDT.
  - Gross Profit: $\$37.98$ USDT | Gross Loss: $\$40.25$ USDT.
  - Frictional Costs Paid: $\$21.29$ USDT (56.1% of gross profit absorbed by fees/slippage).
  - Maximum Drawdown: $5.55\%$.
  - Circuit Breaker Activation: Tripped at 2024-01-05 16:00:00Z (Day 5 of simulation).
- **Primary Failure Mechanisms:**
  1. *Sub-Timeframe Whipsaws:* 15-minute moving average stacks (EMA 9/21/50) generated frequent trend confirmation signals during the late stages of intra-day thrusts, immediately prior to mean-reverting pullbacks.
  2. *Severe Cost Asymmetry:* Across 12 trades, each trade required approximately $0.32\%$ round-trip friction. On a $1.5:1$ reward-risk bracket, friction consumed more than half of all gross gains.
  3. *Unhedged Short Exposure in Bull Regimes:* 6 out of 12 trades were SHORT positions during the early January 2024 Bitcoin ETF anticipation rally, incurring 5 stop-outs out of 6 attempts.
- **Scientific Conclusion:**
  The `trend_continuation_v1` specification is not viable for 15-minute crypto spot trading after accounting for realistic exchange friction.

---

### Entry NRR-002: Point-in-Time Adverse News-Veto Gating (`GROUP_B`)

```yaml
hypothesis_id: "HYP-NEWS-VETO-001"
strategy_name: "news_gated_trend_continuation_v1"
milestone_tested: "Milestone 4.6.3.1 - 4.6.3.1.3"
comparison_baseline: "Group A (Technical Baseline)"
economic_hurdle_target: "+$0.50 USDT net improvement per trade"
status: "FAILURE TO REJECT NULL HYPOTHESIS; ECONOMIC HURDLE NOT MET"
```

- **Observed Metrics:**
  - Net Realized PnL: $-\$23.56$ USDT ($-2.36\%$ return).
  - Delta over Baseline: $+\$0.01$ USDT total across 12 trades ($+\$0.0009$ USDT per trade).
  - Win Rate: $25.0\%$ (3 wins, 9 losses).
  - Maximum Drawdown: $5.55\%$.
  - Circuit Breaker Activation: Tripped at 2024-01-05 23:30:00Z.
  - Candidate Signals Vetoed: 24 candidates vetoed by news engine out of 3,678 setups.
  - Empirical Bootstrap p-value: $p = 0.174$ (continuous market-time grid).
  - Benjamini-Hochberg FDR Assessment: Non-significant at $\alpha_{\text{FDR}} = 0.0167$.
  - Economic Hurdle Ratio: $\frac{\text{Observed Delta}}{\text{Target Delta}} = \frac{+0.0009}{+0.50} = 0.0018$ ($0.18\%$ of hurdle).
- **Primary Failure Mechanisms:**
  1. *News Latency & Lagging Signals:* Editorial news and exchange announcements in January 2024 predominantly lagged price action by 30 to 120 minutes. Volatility spikes occurred prior to editorial publication, rendering post-hoc news vetoes ineffective at preventing stop-loss breaches.
  2. *Low Signal Overlap:* Out of the 9 losing technical trades that caused the drawdown, zero trades had active adverse news vetoes within their entry lookback window. The adverse events in the dataset (security exploits, regulatory actions) occurred on days when the technical strategy generated no signals.
  3. *Zero Gross Alpha Generation:* News vetoing acted purely as an intermittent trade silencer rather than a predictive alpha source.
- **Scientific Conclusion:**
  Point-in-time news intelligence does not provide statistically significant or economically meaningful improvement over a technical trend baseline in the 2024 Development partition.

---

### Entry NRR-003: Non-News Frequency Thinning Control (`GROUP_C`)

```yaml
hypothesis_id: "HYP-CTRL-FREQ-001"
control_type: "Online Pseudo-Random Frequency Thinning (Method C-Online)"
milestone_tested: "Milestone 4.6.3.1 - 4.6.3.1.3"
status: "HYPOTHESIS H2 REJECTED (CONTROL OUTPERFORMED NEWS VETO)"
```

- **Observed Metrics:**
  - Net Realized PnL: $-\$23.13$ USDT ($-2.31\%$ return).
  - Executed Trades: 11 trades (3 wins, 8 losses).
  - Outperformance over Group B: $+\$0.43$ USDT.
  - Bootstrap p-value (H2: $B > C$): $p = 0.980$ (one-sided).
- **Scientific Conclusion:**
  Randomly skipping trades via calibrated pseudo-random thinning produced slightly better net equity than filtering with point-in-time news, proving that Group B's slight variance was an artifact of trade count reduction rather than genuine informational alpha.

---

### Entry NRR-004: Online Dynamic Exposure Cooldown Control (`GROUP_D`)

```yaml
hypothesis_id: "HYP-CTRL-EXPO-001"
control_type: "Dynamic Post-Trade Exposure Cooldown (Method D-Online)"
milestone_tested: "Milestone 4.6.3.1 - 4.6.3.1.3"
status: "HYPOTHESIS H3 REJECTED (CONTROL OUTPERFORMED NEWS VETO)"
```

- **Observed Metrics:**
  - Net Realized PnL: $-\$23.21$ USDT ($-2.32\%$ return).
  - Executed Trades: 12 trades.
  - Maximum Drawdown: $5.51\%$ (lowest drawdown across all four groups).
  - Outperformance over Group B: $+\$0.35$ USDT.
  - Bootstrap p-value (H3: $B > D$): $p = 0.960$ (one-sided).
- **Scientific Conclusion:**
  Enforcing post-trade volatility cooldowns was more effective at mitigating peak drawdown (5.51% vs 5.55%) than news vetoing, further refuting the hypothesis that news adds unique protective value.

---

## 3. Methodological & Computational Negative Findings

### MNF-001: Sparse Candidate Streams in Moving Block Bootstraps
- **Issue:** Applying a standard Moving Block Bootstrap (MBB) directly to an irregularly spaced event stream where $98.5\%$ of points are empty causes the bootstrap resample distribution to collapse onto a point mass at zero ($0.0000$).
- **Resolution:** Returns must be mapped onto a continuous, regular market-time grid (e.g., 15-minute continuous bars), and resamples must be null-centered to yield valid empirical p-values.

### MNF-002: Inactive Period Dominance under Circuit Breakers
- **Issue:** When a portfolio circuit breaker trips early in a simulation (e.g., Day 6 of 366), 98.6% of the chronological time series contains $\$0.00$ returns. Full-period metrics dilute the true economic impact of active trading.
- **Resolution:** Statistical analysis must partition reporting into both an **Active Trading Window** and a **Full Calendar Year** to provide complete transparency.

---

## 4. Preservation & Verification Fingerprints

All data and execution outputs corresponding to these negative findings are permanently preserved:

| Dataset / Run | Description | SHA-256 Fingerprint |
|---|---|---|
| `candidate_cache_2024.json` | 3,678 candidate setups across 2024 | `964c4ba8a6b12a83ad336a19f6a6f6ee05fc3be70ebc0ebdb4435b62b17042a9` |
| `milestone_4_6_3_1_2` | Remediated 4-group reproduction | Manifest: `storage/exports/milestone_4_6_3_1_2/reproduction_audit_manifest.json` |
| `milestone_4_6_3_1_3` | Independent audit exports | Manifest: `storage/exports/milestone_4_6_3_1_3/audit_manifest_4_6_3_1_3.json` |

*This register is maintained under git revision control and may not be edited to alter past outcomes.*
