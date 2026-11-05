# NEPTUNE — Milestone 4.6.3.0
# News-Gated Experiment Protocol, Baseline Freeze & Research Design

**Milestone:** 4.6.3.0  
**Status:** COMPLETE (FROZEN)  
**Date:** 2026-11-06  
**Author:** Quantitative Research & Architecture Team  
**Governing Rules:** Rule S-01, Rule S-04, Rule S-05, Rule S-06, ADR-028, ADR-029  
**Branch:** `quant-expectancy-validation`  
**Execution Baseline Commit:** `514726f` (Milestone 4.6.2.5.1 merge on `main`: `b2295bb`)  
**Historical Market Dataset:** `v2.0.0` (Composite SHA-256: `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`)  
**Historical News Dataset:** `v2.0.0-news-historical` (Manifest SHA-256: `6b7bb69c841ec9a5e1774b6f369c0d9c113df066d80357521ac92b937490f4ec`)  

---

## 1. Executive Summary & Research Mission

Milestone 4.6.3.0 establishes an immutable, statistically defensible, point-in-time compliant research protocol for answering NEPTUNE's fundamental empirical question:

> **Primary Research Question:**  
> *Does adding historically available, asset-relevant news intelligence improve the net trading expectancy of NEPTUNE's deterministic technical strategy after realistic execution costs, compared with an otherwise equivalent technical-only strategy and frequency/exposure-matched controls?*

This milestone explicitly **does not**:
1. Optimize trading strategies or filter thresholds for historical P&L.
2. Connect news intelligence to live market data feeds or paper execution orders.
3. Introduce real-money exchange capability or bypass the Risk Manager (Rule S-01, Rule S-04).
4. Introduce distributed infrastructure (PostgreSQL, Redis, Kafka, Kubernetes, cloud microservices).

Instead, this milestone formally freezes the deterministic technical baseline, defines the four-group experimental architecture, establishes the news-veto input contract, specifies the 13-category event taxonomy, defines the 3-way chronological partitioning of the 35-month dataset, details the statistical evaluation methodology, and computes master reproducibility fingerprints.

---

## 2. Repository & Frozen Baseline Verification

Pre-implementation forensic inspection confirmed:
- **Git Branch Synchronization:** `quant-expectancy-validation` and `main` are 100% synchronized at baseline commit `514726f` / merge commit `b2295bb`.
- **Working Tree Cleanliness:** Clean working tree prior to milestone implementation.
- **Historical Market Dataset `v2.0.0`:** 420 Parquet files across `BTCUSDT`, `ETHUSDT`, `BNBUSDT` and timeframes `15m`, `1h`, `4h`, `1d` verified bit-for-bit against manifest tree SHA-256:
  $$\text{SHA-256} = \texttt{b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c}$$
- **Historical News Dataset `v2.0.0-news-historical`:** 1,499 total records (1,365 Binance announcements, 66 GDELT articles, 68 authoritative macro events, 1,421 event clusters) verified against manifest SHA-256:
  $$\text{SHA-256} = \texttt{6b7bb69c841ec9a5e1774b6f369c0d9c113df066d80357521ac92b937490f4ec}$$

---

## 3. Four-Group Experimental Architecture

To disentangle genuine informational alpha from simple trade-frequency reduction and market exposure differences, the research protocol evaluates four parallel experimental groups subjected to identical market conditions, capital, risk limits, and transaction frictions:

```
                  ┌───────────────────────────────────────────────┐
                  │ Technical Strategy Analyst (Closed Candles)   │
                  │   - Regime: TRENDING_BULL / TRENDING_BEAR     │
                  │   - Trend: EMA 20/50/200 Stack (Strength >= 0.40) │
                  │   - Momentum: RSI + MACD Score (|Score| >= 0.15) │
                  │   - Volume: RVOL >= 0.80, OBV Alignment       │
                  └───────────────────────┬───────────────────────┘
                                          │ Raw Candidate Signal
                                          ▼
                ┌───────────────────────────────────────────────────┐
                │        EXPERIMENTAL GROUP ROUTING GATEWAY         │
                └───────┬──────────────┬──────────────┬─────────────┘
                        │              │              │             │
        ┌───────────────┘              │              │             └────────────────┐
        ▼                              ▼              ▼                              ▼
  ┌───────────┐                 ┌───────────┐   ┌───────────┐                 ┌───────────┐
  │  GROUP A  │                 │  GROUP B  │   │  GROUP C  │                 │  GROUP D  │
  │ Technical │                 │ News-Veto │   │ Frequency │                 │ Exposure  │
  │ Baseline  │                 │ Strategy  │   │  Control  │                 │  Control  │
  └─────┬─────┘                 └─────┬─────┘   └─────┬─────┘                 └─────┬─────┘
        │                             │               │                             │
   Direct Pass                   PIT Adverse     Deterministic                 Dynamic Cooldown
   (No Filter)                   News Veto?      Decimation/Seed               Exposure Match
                                 ├─ Yes: VETO    (Target: N_B)                 (Target: Bars_B)
                                 └─ No:  Pass         │                             │
        │                             │               │                             │
        └───────────────────────┬─────┴───────────────┴─────────────────────────────┘
                                │ Filter-Approved Candidate
                                ▼
                  ┌───────────────────────────────────────────────┐
                  │ Risk Manager Sole Authorization (Rule S-04)   │
                  │   1. Daily Loss Limit <= 2.0%                 │
                  │   2. Max Drawdown Circuit Breaker <= 5.0%     │
                  │   3. Max Concurrent Positions <= 2            │
                  │   4. Asset Correlation Limit (1 per symbol)   │
                  │   5. Reward/Risk Ratio >= 1.5:1               │
                  │   -> HMAC-SHA256 Token State: ISSUED          │
                  └───────────────────────┬───────────────────────┘
                                          │ Approved & Sized Order
                                          ▼
                  ┌───────────────────────────────────────────────┐
                  │ Point-in-Time Execution Scheduler             │
                  │   - Policy: NEXT_ELIGIBLE_PRICE (Bar T+1 Open)│
                  │   - Execution Gap Check (1 bar 15m / 3 bars)  │
                  │   - Token Reservation & Single-Use Consume    │
                  │   - Friction: 0.10% Fee + 0.05% Slip + Spread │
                  │   -> Total Round-Trip Friction: 0.32% (32 bps)│
                  └───────────────────────────────────────────────┘
```

### 3.1 Group A — Technical-Only Baseline (Reference Group)
- **Role:** Control reference representing NEPTUNE's existing deterministic strategy.
- **Filtering:** No news intelligence or external filters applied.
- **Signals:** All candidate signals passing technical confluence are routed directly to Risk Manager.

### 3.2 Group B — Technical Strategy with News Veto
- **Role:** Primary treatment group evaluating news intelligence.
- **Filtering:** Candidate signals are evaluated against qualifying adverse news events visible at or before the decision cutoff ($T_{\text{decision}} = \text{candle.close\_timestamp}$).
- **Veto Mechanics:** If a qualifying adverse event exists with sufficient impact weight, the candidate is vetoed (`VETOED_BY_NEWS`).
- **Safety Invariant:** The news layer **cannot generate directional trades** and **cannot override Risk Manager rejections**.

### 3.3 Group C — Frequency-Matched Control
- **Role:** Controls for trade-reduction bias.
- **Purpose:** Determines whether Group B outperforms simply because taking fewer trades saves transaction costs (0.32% per round trip) or avoids choppy regimes.
- **Methodology:** Thins Group A candidate signals to exactly match Group B's sample size $N_B$ using deterministic algorithms (Systematic Decimation, Technical Confidence Priority, and Cryptographic Seed Selection).
- **Look-Ahead Invariant:** Strictly selects candidates using arrival sequence or historical technical scores; **zero future market returns or outcomes are consumed**.

### 3.4 Group D — Exposure-Matched Control
- **Role:** Controls for market exposure and capital utilization.
- **Purpose:** Matches Group B's cumulative time-in-market (active holding bars) and capital utilization without using news intelligence.
- **Methodology:** Applies a dynamic cooldown budget derived from Group B's cumulative exposure curve up to decision time $T$, ensuring Group D spends equivalent duration in the market.

---

## 4. Execution & Risk Parity Matrix

All four experimental groups share identical structural parameters:

| Dimension | Group A | Group B | Group C | Group D | Parity Status |
|:---|:---:|:---:|:---:|:---:|:---:|
| **Initial Capital** | 1,000 USDT | 1,000 USDT | 1,000 USDT | 1,000 USDT | **IDENTICAL** |
| **Spot Leverage** | 1.0x (No Leverage) | 1.0x (No Leverage) | 1.0x (No Leverage) | 1.0x (No Leverage) | **IDENTICAL** |
| **Max Concurrent Positions** | 2 | 2 | 2 | 2 | **IDENTICAL** |
| **Max Risk Per Trade** | 0.5% | 0.5% | 0.5% | 0.5% | **IDENTICAL** |
| **Daily Loss Limit** | 2.0% | 2.0% | 2.0% | 2.0% | **IDENTICAL** |
| **Drawdown Circuit Breaker** | 5.0% | 5.0% | 5.0% | 5.0% | **IDENTICAL** |
| **Min Reward/Risk Ratio** | 1.5:1 | 1.5:1 | 1.5:1 | 1.5:1 | **IDENTICAL** |
| **Execution Policy** | `NEXT_ELIGIBLE_PRICE` | `NEXT_ELIGIBLE_PRICE` | `NEXT_ELIGIBLE_PRICE` | `NEXT_ELIGIBLE_PRICE` | **IDENTICAL** |
| **Taker Fee Per Side** | 0.10% | 0.10% | 0.10% | 0.10% | **IDENTICAL** |
| **Adverse Slippage** | 0.05% | 0.05% | 0.05% | 0.05% | **IDENTICAL** |
| **Half-Spread Cost** | 0.01% (2 bps total) | 0.01% (2 bps total) | 0.01% (2 bps total) | 0.01% (2 bps total) | **IDENTICAL** |
| **Round-Trip Friction** | 0.32% (32 bps) | 0.32% (32 bps) | 0.32% (32 bps) | 0.32% (32 bps) | **IDENTICAL** |
| **Exit Policy** | BALANCED (Ratchet) | BALANCED (Ratchet) | BALANCED (Ratchet) | BALANCED (Ratchet) | **IDENTICAL** |
| **Trailing Stop Multiplier**| 2.0 * ATR | 2.0 * ATR | 2.0 * ATR | 2.0 * ATR | **IDENTICAL** |
| **Trailing Activation** | +1.0 R | +1.0 R | +1.0 R | +1.0 R | **IDENTICAL** |
| **Sole Authorization** | Risk Manager | Risk Manager | Risk Manager | Risk Manager | **IDENTICAL** |

---

## 5. Master Reproducibility Fingerprint

The research protocol state is cryptographically bound into a composite SHA-256 fingerprint:

```json
{
  "protocol_version": "v1.0.0-m4630",
  "git_commit_hash": "514726ff78f48956146013e8c36948db2158574e",
  "git_branch": "quant-expectancy-validation",
  "baseline_market_dataset_sha256": "b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c",
  "news_dataset_manifest_sha256": "6b7bb69c841ec9a5e1774b6f369c0d9c113df066d80357521ac92b937490f4ec",
  "baseline_config_fingerprint": "33a5d9f67052fe25737e8e93011230462ab2250e1984395f2d69214f445f1278",
  "split_manifest_fingerprint": "7538a8813a34a9b6c4b26716ad10e3dfbbbe9d8d69f041ff2f18370757753177",
  "taxonomy_rules_fingerprint": "4ff388e6e87f174aa48589c3628e83f3900d11933ba5e63ea9e4be35987113e6",
  "statistical_plan_fingerprint": "31caef900a0dc35b0d50064f216e9c62391038b368fe0be5508a8a49ae9ea1a7",
  "composite_experiment_fingerprint": "5ffc9b1bed97138db0b8ceab7aab2514116b02c88cdac26f322af2d5f6b18ced"
}
```

---

## 6. Milestone Completion Status & Stopping Protocol

Milestone 4.6.3.0 is **COMPLETE**.  
Per non-negotiable mission constraints:
- **No strategy runs or news-veto experiments have been executed.**
- **No filter parameters have been tuned for profitability.**
- **System is halted awaiting independent protocol sign-off.**
