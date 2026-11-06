# NEPTUNE — Milestone 4.6.3.1.2: Historical Reproduction

**Report ID:** `NEP-REP-4.6.3.1.2-REP`  
**Date:** 2026-11-07  
**Status:** Reproduction Complete & Verified  
**Governing Documents:** Rule S-01, Rule S-04, Rule S-05, Rule S-06, Rule S-07, Rule A-01, ADR-028, ADR-031, ADR-033  
**Data Partition:** 2024 Development (`2024-01-01T00:00:00Z` to `2024-12-31T23:59:59Z`, 105,408 candles)  
**Artifact Directory:** [`storage/exports/milestone_4_6_3_1_2/`](file:///d:/Project%202026/Trading_bot/storage/exports/milestone_4_6_3_1_2/)

---

## 1. Executive Summary

Following the remediation of the portfolio accounting defect and revalidation of the Risk Manager's 5.0% maximum drawdown circuit breaker, the complete Milestone 4.6.3.1 four-group experiment was re-run from scratch across the 2024 Development partition.

All experiment inputs, strategy configurations, risk parameters, execution policies, transaction friction models, and dataset fingerprints were preserved with zero modification.

### Core Reproduction Finding
Under mathematically correct accounting and active risk circuit breaker enforcement, **all four experimental groups (A, B, C, D) tripped their 5.0% portfolio drawdown circuit breaker during the first week of January 2024 (January 5–6)**.

Consequently:
- Total executed trade count collapsed from the unhalted 73 trades (Group A) and 57 trades (Group B) down to **12 trades** (Group A, B, D) and **11 trades** (Group C).
- Portfolio losses were capped near the 5.0% threshold: ending equity stabilized at **\$976.44 USDT (-2.36%)**, preventing the unhalted portfolio drawdown of **-21.47%** (\$785.28 USDT).
- Over **3,100 to 3,666 subsequent candidate orders were rejected** by the Risk Manager across the remaining 51 weeks of 2024.
- News-gated filtering (Group B) produced virtually identical trading outcomes to the technical baseline (Group A), confirming that news intelligence does not salvage the underlying technical strategy.

---

## 2. Quantitative Comparison: Defective vs. Corrected Reproduction

| Metric | Group A (Defective 4.6.3.1) | Group A (Corrected 4.6.3.1.2) | Group B (Defective 4.6.3.1) | Group B (Corrected 4.6.3.1.2) | Delta / Remediation Impact |
|---|---|---|---|---|---|
| **Executed Trades** | 73 | **12** | 57 | **12** | -61 trades (breaker halt) |
| **Winning Trades** | 24 | **3** | 20 | **3** | Aligned (25.0% win rate) |
| **Losing Trades** | 49 | **9** | 37 | **9** | Aligned (75.0% loss rate) |
| **Win Rate** | 32.88% | **25.00%** | 35.09% | **25.00%** | Baseline performance |
| **Gross Profit** | \$238.41 | **\$37.98** | \$205.65 | **\$37.99** | Partitioning defect fixed |
| **Gross Loss** | \$323.00 | **\$40.25** | \$249.77 | **\$40.44** | True gross losses |
| **Total Fees** | \$75.52 | **\$13.31** | \$62.47 | **\$13.20** | Friction strictly charged |
| **Total Slippage** | \$37.76 | **\$6.65** | \$31.23 | **\$6.60** | Adverse execution applied |
| **Total Spread** | \$7.55 | **\$1.33** | \$6.25 | **\$1.32** | Half-spread accounted |
| **Realized Net P&L** | -\$205.42 | **-\$23.57** | -\$144.07 | **-\$23.56** | True realized net P&L |
| **Reported Ending Equity** | \$984.56 *(flawed)* | **\$976.44** | \$1013.29 *(flawed)* | **\$976.44** | Phantom cash eliminated |
| **Net Portfolio Return** | -1.54% *(flawed)* | **-2.36%** | +1.33% *(flawed)* | **-2.36%** | Breaker capped loss |
| **Maximum Drawdown** | 2.92% *(flawed)* | **5.55%** | 2.87% *(flawed)* | **5.55%** | True drawdown recognized |
| **Circuit Breaker Tripped** | FALSE *(concealed)* | **TRUE (Jan 5 16:00)** | FALSE *(concealed)* | **TRUE (Jan 5 23:30)** | Enforced |
| **Orders Rejected by Risk** | 0 | **3,666** | 0 | **3,483** | Post-breaker protection |

---

## 3. Four-Group Experimental Reproduction Results

All four groups were replayed across the identical candidate stream under the corrected [`PortfolioLedger`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/portfolio_ledger.py):

| Group ID | Role / Gate Policy | Trades | Net P&L (USDT) | Ending Equity | Max Drawdown | Breaker Trip Timestamp | Orders Rejected |
|---|---|---|---|---|---|---|---|
| **GROUP_A** | Deterministic Baseline (No News) | 12 | -\$23.57 | \$976.44 | 5.55% | 2024-01-05T16:00:00Z | 3,666 |
| **GROUP_B** | Point-in-Time News Veto | 12 | -\$23.56 | \$976.44 | 5.55% | 2024-01-05T23:30:00Z | 3,483 |
| **GROUP_C** | Online Frequency Thinning (Match B) | 11 | -\$23.13 | \$976.87 | 5.55% | 2024-01-05T23:30:00Z | 3,130 |
| **GROUP_D** | Online Exposure Cooldown (Match B) | 12 | -\$23.21 | \$976.79 | 5.51% | 2024-01-06T00:15:00Z | 3,665 |

### Key Observations:
1. **Uniform Breaker Activation:** All 4 groups crossed the 5.0% drawdown limit within a 8-hour window on January 5–6, 2024.
2. **Equity Convergence:** Ending equity across all 4 groups is virtually indistinguishable (\$976.44 to \$976.87 USDT).
3. **No Alpha from News Intelligence:** Group B (with news vetoes active) took 12 trades and lost -\$23.56 USDT, compared to Group A taking 12 trades and losing -\$23.57 USDT. The net expectancy difference is a negligible $+\$0.0009$ USDT per trade, which fails the pre-registered economic hurdle ($+\$0.50$ USDT) by orders of magnitude.

---

## 4. Breaker Activation and Post-Breaker Order Rejection

### 4.1 Chronology of Group A Circuit Breaker
- **2024-01-01 to 2024-01-04:** Initial trades open across BTC, ETH, and BNB.
- **2024-01-05 12:45 UTC:** Trade 7 exits with a loss; equity drops to \$951.20 USDT (drawdown 4.88%).
- **2024-01-05 16:00 UTC:** Trade 8 and Trade 9 experience adverse price movements. Mark-to-market equity reaches \$944.54 USDT (drawdown **5.55%**).
- **Circuit Breaker Fires:** `RiskManager.evaluate_signal` flags `MAX_DRAWDOWN_EXCEEDED` (`current_drawdown=0.0555 >= max_drawdown_pct=0.0500`).
- **Post-Breaker Operation:** Existing open positions exit on their pre-defined stop-loss brackets. No new orders are permitted. Over the remaining 34,672 bars (January 6 to December 31), **all 3,666 candidate signals are rejected**.

### 4.2 Capital Preservation Proof
In the defective 4.6.3.1 execution, trading was allowed to run unchecked, ultimately accumulating **-\$205.42 USDT in net losses** and driving true equity down to **\$785.28 USDT (-21.47% drawdown)**.
Under corrected Risk Manager enforcement:
- Trading was halted at **-\$23.57 USDT**.
- **\$181.85 USDT of capital was preserved**.
- Drawdown was capped at **5.55%**, proving the effectiveness of the Risk Manager as a capital preservation shield.

---

## 5. Artifact Preservation and Manifest Checksums

The original Milestone 4.6.3.1 deliverables in `storage/exports/milestone_4_6_3_1/` remain bit-for-bit unmodified.
New machine-readable artifacts have been exported to [`storage/exports/milestone_4_6_3_1_2/`](file:///d:/Project%202026/Trading_bot/storage/exports/milestone_4_6_3_1_2/):

| Artifact File | Description | SHA-256 Checksum |
|---|---|---|
| `group_metrics.json` | Corrected 4-group performance metrics | `101b3f29caad6f3dba3dbadeaa3a5af47a49de0910dd984c898ff6dda4b7e088` |
| `trade_ledger_reproduction.json` | 12-trade complete executed ledger | `e361ea907f5f1e553fe5cb6b793acda0668516c82482685e75a960764f0a8206` |
| `cash_collateral_ledger.json` | Transaction-by-transaction cash/collateral log | `b34a22a4b615f9296bae7bcd9fc9d13f441ea8b2e54c2e872d0d3901567366c7` |
| `equity_curves.json` | 35,136-bar mark-to-market equity curves | `3e15a26efc282621e1cfaad2a45e949975a9adf94c5a75c6544f302fab191f65` |
| `risk_breaker_events.json` | Exact timestamps and audit counts of breaker events | `08985dfa287efcf5c8daad8dc12c0b1432492fc4793761c0d9b7aa2b3f49cbcf` |
| `statistical_revalidation.json` | Null-centered market-time bootstrap results | `5d772ea6b9a82c64c0cc0d672189fea35d0e1a8ad0512d8651ee27153bebb705` |
| `candidate_veto_reconciliation.json` | Full candidate-to-veto mapping | `b64c16f022065609329a0c99ba44d755bcee7d31b0b5bf4d747f7282635a9d0b` |
| `reproduction_audit_manifest.json` | Master audit manifest linking original & corrected hashes | `839fd4f228b3ee1243dc2a7bb84e1b7c02b28c21a4e12e1ec10d86018302f0e0` |

