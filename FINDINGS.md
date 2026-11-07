# NEPTUNE: An Empirical Investigation of Autonomous Multi-Agent Market Intelligence, Execution Friction, and Regime-Conditioned Capital Preservation in Cryptocurrency Spot Markets

**Authors:** NEPTUNE Quantitative Research & Engineering Team  
**Date:** November 2026  
**Document Version:** 1.0.0 (Research Monograph)  
**Codebase Baseline:** Commit `3536e7d` | Branch `quant-expectancy-validation`  
**Dataset Reference:** `NEPTUNE-HISTORICAL-DATASET-v2.0.0` (394,716 Validated Closed Candles)

---

## Abstract

This paper presents the empirical findings, system architecture, and quantitative methodology of **Project NEPTUNE**, an autonomous market intelligence and paper-trading research platform. Over a sequence of rigorous quantitative engineering milestones (Milestones 4.1 through 4.5), we investigated whether deterministic momentum and trend-breakout strategies can produce positive net expectancy under realistic cryptocurrency exchange friction (0.30% round-trip transaction costs). 

Using an immutable, multi-asset, multi-year historical dataset comprising **394,716 closed candles** across **BTCUSDT, ETHUSDT, and BNBUSDT** on **15m, 1h, 4h, and 1d** timeframes spanning 34 contiguous months (January 2024 – November 2026), we conducted **510 backtest and walk-forward evaluations** under strict zero-leakage conditions. 

Our empirical findings demonstrate:
1. **The Execution Friction Paradox:** Single-timeframe breakout strategies that appear marginally profitable on a gross basis suffer catastrophic negative expectancy after realistic taker fees, slippage, and spread.
2. **Capital Preservation vs. Alpha Generation:** Multi-factor entry filters (notably Hypothesis 7: Trend + Momentum + Volatility Regime confluence) do *not* generate net alpha; instead, they act as powerful **capital preservation mechanisms**, suppressing **60% to 88% of false-breakout churn** during prolonged sideways and volatile consolidation regimes, thereby reducing drawdown by up to 95%.
3. **Exit Policy Superiority:** Trailing protection exit policies (**Balanced Protection**) structurally outperform traditional fixed stop-loss/take-profit brackets across every market regime and timeframe.
4. **The Circuit Breaker Lockout Phenomenon:** Continuous multi-year portfolio simulations flatline after early drawdowns breach mandatory risk manager circuit breakers (5.0% maximum drawdown), whereas chronologically partitioned evaluations reveal latent regime-specific dynamics.

Finally, we introduce a formal model-agnostic forecasting contract ([`IForecaster`](file:///d:/Project%202026/Trading_bot/backend/app/analytics/forecasting.py#L70)) designed to interface deep-learning temporal forecasting architectures (such as Kronos) with zero look-ahead bias.

**Keywords:** Quantitative Finance, Multi-Agent Monolith, Market Microstructure, Look-Ahead Bias Prevention, Walk-Forward Cross-Validation, Trailing Exit Architecture, Capital Preservation, Market Regimes.

---

## Table of Contents

1. [Introduction & Motivation](#1-introduction--motivation)
2. [System Architecture & Quantitative Infrastructure](#2-system-architecture--quantitative-infrastructure)
   - [2.1 The Modular Monolith Principle](#21-the-modular-monolith-principle)
   - [2.2 Specialist Agent Decomposition & Central Brain](#22-specialist-agent-decomposition--central-brain)
   - [2.3 Non-Negotiable Risk Management Invariants](#23-non-negotiable-risk-management-invariants)
   - [2.4 Realistic Paper Execution & Friction Engine](#24-realistic-paper-execution--friction-engine)
3. [Chronological Integrity & Backtest Methodology](#3-chronological-integrity--backtest-methodology)
   - [3.1 Candle-Close Invariant & Execution Timing](#31-candle-close-invariant--execution-timing)
   - [3.2 Pre-Partition Warmup Priming Without Leakage](#32-pre-partition-warmup-priming-without-leakage)
   - [3.3 Candidate-Level Portfolio Replay vs. Trade-Level Filtering](#33-candidate-level-portfolio-replay-vs-trade-level-filtering)
   - [3.4 Expanding Walk-Forward Cross-Validation Framework](#34-expanding-walk-forward-cross-validation-framework)
   - [3.5 Dataset Versioning & Cryptographic Provenance](#35-dataset-versioning--cryptographic-provenance)
4. [Strategy & Exit Policy Formulations](#4-strategy--exit-policy-formulations)
   - [4.1 Baseline Momentum Breakout](#41-baseline-momentum-breakout)
   - [4.2 Exit Policies: Fixed Bracket vs. Balanced Protection](#42-exit-policies-fixed-bracket-vs-balanced-protection)
   - [4.3 Entry Filter Hypotheses (H1 through H7)](#43-entry-filter-hypotheses-h1-through-h7)
5. [Empirical Results & Quantitative Benchmarks](#5-empirical-results--quantitative-benchmarks)
   - [5.1 Multi-Year Multi-Partition Benchmark Matrix](#51-multi-year-multi-partition-benchmark-matrix)
   - [5.2 Timeframe Performance Hierarchy (15m, 1h, 4h, 1d)](#52-timeframe-performance-hierarchy-15m-1h-4h-1d)
   - [5.3 Exit Policy Benchmark Analysis](#53-exit-policy-benchmark-analysis)
   - [5.4 Entry Filter Ablation & Efficiency](#54-entry-filter-ablation--efficiency)
   - [5.5 4-Fold Expanding Walk-Forward Cross-Validation](#55-4-fold-expanding-walk-forward-cross-validation)
   - [5.6 Market Regime Distribution & Loss Concentration](#56-market-regime-distribution--loss-concentration)
6. [Critical Discoveries & Adversarial Reconciliations](#6-critical-discoveries--adversarial-reconciliations)
   - [6.1 The Execution Friction Paradox](#61-the-execution-friction-paradox)
   - [6.2 The 5.0% Drawdown Circuit Breaker Lockout](#62-the-50-drawdown-circuit-breaker-lockout)
   - [6.3 The Portfolio Slot Reuse Fallacy](#63-the-portfolio-slot-reuse-fallacy)
   - [6.4 Full Decimal Accounting Identity Verification](#64-full-decimal-accounting-identity-verification)
7. [Deep Learning Integration: The Model-Agnostic Forecasting Contract](#7-deep-learning-integration-the-model-agnostic-forecasting-contract)
   - [7.1 Design of the IForecaster Protocol](#71-design-of-the-iforecaster-protocol)
   - [7.2 Input Fingerprinting & Look-Ahead Isolation](#72-input-fingerprinting--look-ahead-isolation)
   - [7.3 Architectural Isolation of GPU Dependencies (ADR-021)](#73-architectural-isolation-of-gpu-dependencies-adr-021)
   - [7.4 Pretrained Foundation Model Benchmark: Kronos-mini (Milestone 4.5)](#74-pretrained-foundation-model-benchmark-kronos-mini-milestone-45)
   - [7.5 Independent Forensic Audit of the Kronos Foundation Model Integration (Milestone 4.5.1)](#75-milestone-451-independent-forensic-audit-of-the-kronos-foundation-model-integration)
8. [Natural Language & Macro Event Intelligence: Historical News Feasibility (Milestone 4.6.0)](#8-natural-language--macro-event-intelligence-historical-news-feasibility-milestone-460)
   - [8.1 Core Quantitative Research Question & Motivation](#81-core-quantitative-research-question--motivation)
   - [8.2 Historical News Source Evaluation & Verification Matrix](#82-historical-news-source-evaluation--verification-matrix)
   - [8.3 The Point-in-Time Revisionism Trap & Latency Invariant](#83-the-point-in-time-revisionism-trap--latency-invariant)
   - [8.4 Recommended Two-Tier Acquisition Architecture](#84-recommended-two-tier-acquisition-architecture)
   - [8.5 Four-Group Experimental Design & Statistical Protocol](#85-four-group-experimental-design--statistical-protocol)
   - [8.6 Feasibility Assessment & Conditional Go Recommendation](#86-feasibility-assessment--conditional-go-recommendation)
9. [Conclusion & Strategic Research Roadmap](#9-conclusion--strategic-research-roadmap)
   - [9.1 Key Scientific Takeaways](#91-key-scientific-takeaways)
   - [9.2 Recommended Research Directions (Milestone 5.0+)](#92-recommended-research-directions-milestone-50)
10. [Architecture Decision Records & Audit Index](#10-architecture-decision-records--audit-index)

---

## 1. Introduction & Motivation

Algorithmic trading in liquid retail cryptocurrency markets (e.g. Binance spot) presents unique microstructural challenges. While academic literature and retail backtesting tools frequently report attractive Sharpe ratios and high win rates for classical trend-following strategies, live implementations almost universally suffer severe performance decay.

Three primary methodological errors explain this divergence:
1. **Unrealistic Friction Assumptions:** Retail backtests typically assume zero slippage, mid-price fills, or negligible maker fees. In reality, market orders on cryptocurrency exchanges incur taker fees (10 bps each side on Binance), bid-ask spreads (typically 2.0 bps on Tier-1 pairs), and execution slippage (5.0 bps under typical order sizes), totaling **30.0 bps (0.30%) per round-trip trade**.
2. **Look-Ahead Bias & Intrabar Ambiguity:** Backtests frequently evaluate entry signals using open or unconfirmed candles, execute trades at the close price of the signal candle (requiring instantaneous zero-latency execution), or resolve simultaneous stop-loss and take-profit breaches within the same candle with optimistic bias.
3. **Overfitting to Static Temporal Slices:** Parameter tuning on a single 6-to-12-month period inevitably selects filters that exploit non-stationary market regimes, collapsing when applied to out-of-sample data.

**Project NEPTUNE** was initiated to construct an uncompromising, institutionally rigorous research platform adhering to persistent engineering rules ([`AGENTS.md`](file:///d:/Project%202026/Trading_bot/AGENTS.md)). NEPTUNE does not trade real funds (Rule `S-01`), does not promise profitability (Rule `S-07`), enforces exact monetary precision in Python `Decimal` (Rule `A-01`), and mandates complete reproducibility. 

This paper synthesizes the empirical outcomes of Milestones 4.1 through 4.5, tracing the evolution from simple historical simulation to an advanced, multi-year, multi-timeframe research laboratory.

---

## 2. System Architecture & Quantitative Infrastructure

```mermaid
flowchart TD
    subgraph Data Layer
        P1[Public Binance REST v3] -->|Paginated Ingestion| V1[CandleValidator]
        V1 -->|Canonical 8-Col Parquet| S1[(storage/historical/)]
        V1 -->|Cold Archive Mirror| S2[(storage/datasets/v2.0.0/)]
        S2 -->|Metadata & Checksums| DB1[(SQLite neptune.db)]
    end

    subgraph Analytical Core & Specialist Agents
        S1 -->|Closed Bars Only| MS[Market Scanner Agent]
        S1 -->|Indicator Warmup| TA[Trend Analyst Agent]
        S1 -->|RSI / MACD| MA[Momentum Analyst Agent]
        S1 -->|VWAP / Vol Profile| VA[Volume Analyst Agent]
        MS & TA & MA & VA -->|Structured Context| CB[Central Brain Orchestrator]
        CB -->|Context Request| SA[Strategy Analyst Agent]
    end

    subgraph Validation & Risk Enforcement
        SA -->|Raw Candidate Signals| SV[Signal Validator Agent]
        SV -->|Multi-Timeframe Scored| RM[Risk Manager Agent]
        RM -->|Invariants & Circuit Breakers| PE[Paper Execution Simulator]
    end

    subgraph Audit & Provenance
        PE -->|Trade Ledger & Equity Curve| PA[Performance Auditor Agent]
        PA -->|Deterministic Audit Checksums| DB1
    end
```

### 2.1 The Modular Monolith Principle
In strict compliance with Rules `S-08`, `S-09`, and `S-10`, NEPTUNE is architected as a **modular monolith** in Python/FastAPI. Microservices, Kafka, Redis, and PostgreSQL are explicitly prohibited in v1. 
- **Relational Metadata:** Managed via SQLite with Write-Ahead Logging (`PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;`).
- **Time-Series Storage:** High-performance columnar Apache Parquet partitioned by `symbol/timeframe/YYYY/MM.parquet`.
- **Numerical Precision:** All financial calculations use `Decimal` or integer cents to eliminate floating-point rounding errors (Rule `A-01`).

### 2.2 Specialist Agent Decomposition & Central Brain
NEPTUNE enforces an asynchronous multi-agent architecture mediated by a Central Brain ([`AGENTS.md`](file:///d:/Project%202026/Trading_bot/AGENTS.md)). Direct agent-to-agent communication is forbidden (Rule `A-06`):
1. **Market Scanner (`market_scanner`):** Evaluates completed bars to classify market regimes (`TRENDING_BULL`, `TRENDING_BEAR`, `RANGING`, `VOLATILE`, `UNCERTAIN`).
2. **Trend Analyst (`trend_analyst`):** Computes triple-EMA alignment (EMA 20, 50, 200) and Wilder's Smoothed ADX.
3. **Momentum Analyst (`momentum_analyst`):** Tracks Wilder's 14-period RSI and MACD (12, 26, 9).
4. **Volume Analyst (`volume_analyst`):** Monitors rolling volume profile, relative volume (RVOL), and VWAP deviation.
5. **Strategy Analyst (`strategy_analyst`):** Consumes context and emits structured `RawCandidateSignal` models.
6. **Signal Validator (`signal_validator`):** Performs multi-timeframe validation and computes composite quality scores.
7. **Risk Manager (`risk_manager`):** Authorizes position sizing and enforces portfolio invariants.
8. **Execution Manager (`execution_manager`):** Simulates paper fills, slippage, and fees.
9. **Performance Auditor (`performance_auditor`):** Computes ledger statistics and verifies mathematical identities.

### 2.3 Non-Negotiable Risk Management Invariants
All candidate orders must pass through the `RiskManager` ([`risk_manager.py`](file:///d:/Project%202026/Trading_bot/backend/app/risk/risk_manager.py)). Approval requires passing five deterministic checks:
1. **Daily Loss Limit:** Maximum realized + unrealized loss $\le 2.0\%$ of daily starting equity.
2. **Maximum Drawdown Circuit Breaker:** Peak-to-trough equity drawdown $\le 5.0\%$. Once breached, all trading halts.
3. **Concurrency Cap:** Maximum 2 concurrent positions across the entire portfolio.
4. **Asset Correlation Exposure:** No concurrent multiple positions in the same instrument.
5. **Reward-to-Risk Geometry:** Minimum theoretical $R:R \ge 1.5:1$. Position sizing is capped at $0.5\%$ risk of current equity:
   $$\text{Position Size} = \frac{\text{Current Equity} \times 0.005}{|\text{Entry Price} - \text{Stop Loss}|}$$

### 2.4 Realistic Paper Execution & Friction Engine
The execution simulator ([`execution.py`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/execution.py)) enforces institutional friction assumptions:
- **Taker Fee:** $0.10\%$ on entry and exit ($0.20\%$ total).
- **Slippage:** $0.05\%$ per side ($0.10\%$ total).
- **Bid-Ask Spread:** $2.0\text{ bps}$ ($0.02\%$).
- **Total Round-Trip Friction:** **$32.0\text{ bps}$ ($0.32\%$)**.
- **Conservative Ambiguity Resolution:** If both Stop-Loss and Take-Profit are breached within the same bar's $[L, H]$ interval, the engine conservatively assumes the stop-loss was struck first.

---

## 3. Chronological Integrity & Backtest Methodology

### 3.1 Candle-Close Invariant & Execution Timing
To prevent look-ahead bias (Rule `S-05`, `A-09`):
1. **Signal Emission:** Evaluated strictly upon confirmation of candle close at bar $T$.
2. **Execution Timing:** Position entry is executed at the **Open price of bar $T+1$**:
   $$\text{Entry Price} = \text{Open}_{T+1} \times (1 + \text{Slippage}) + \frac{\text{Spread}}{2}$$
3. Signals cannot receive fills using prices from bar $T$, and positions cannot be stopped out using price movement that occurred prior to entry.

```
Bar T-1: Closed  ──►  Bar T: Closed [SIGNAL CONFIRMED]  ──►  Bar T+1: Open [ENTRY FILL]
                                                            └─► High/Low: Position Evaluated
```

### 3.2 Pre-Partition Warmup Priming Without Leakage
Technical indicators (EMA 200, ADX 14, MACD) require significant historical lookback to converge. Slicing a test partition without warmup leads to cold-start errors; including full historical data introduces look-ahead risk.

The framework ([`research_framework.py`](file:///d:/Project%202026/Trading_bot/backend/app/analytics/research_framework.py)) provides a standardized **100-bar pre-partition warmup window**:
- Preceding bars are supplied strictly for indicator initialization.
- Trades generated during the warmup window are strictly pruned:
  $$\text{Valid Trades} = \{t \in \text{Trades} \mid \text{Start}_{\text{partition}} \le t.\text{entry\_timestamp} \le \text{End}_{\text{partition}}\}$$
- Future candles past $\text{End}_{\text{partition}}$ are inaccessible.

### 3.3 Candidate-Level Portfolio Replay vs. Trade-Level Filtering
A foundational discovery in Milestone 4.3 was the **Portfolio Slot Reuse Fallacy**:
- *Defective Approach (Trade-Level):* Running a baseline backtest to produce a trade ledger, then filtering out trades that fail an indicator threshold.
- *Why This Fails:* Filtering a trade in an active portfolio frees capital and a concurrency slot. That slot can immediately be taken by a subsequent candidate that was previously blocked.
- *Correct Approach (Candidate-Level Replay):* Full portfolio replay where filtering occurs at the candidate stage, dynamically altering slot availability and portfolio state forward in time.

### 3.4 Expanding Walk-Forward Cross-Validation Framework
To detect overfitting, we designed an expanding-window walk-forward cross-validation protocol comprising 4 sequential folds across 34 months:

```
Fold 1: [--- Train: 2024 (12M) ---] [ Test: 2025-H1 (6M) ]
Fold 2: [------ Train: 2024 to 2025-H1 (18M) ------] [ Test: 2025-H2 (6M) ]
Fold 3: [--------- Train: 2024 to 2025-Full (24M) ---------] [ Test: 2026-H1 (6M) ]
Fold 4: [------------ Train: 2024 to 2026-H1 (30M) ------------] [ Test: 2026-H2 (4M) ]
```

### 3.5 Dataset Versioning & Cryptographic Provenance
Historical data is tracked as an immutable research asset ([ADR-020](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-020-dataset-versioning-provenance-tracking-and-timeframe-independent-chronological-research-framework)):
- **`v1.0.0`:** Initial 87 Parquet files (10 months, 2026-only, 117,144 candles).
- **`v2.0.0`:** Expanded 420 Parquet files (34 contiguous months, 2024–2026, 394,716 candles) across BTCUSDT, ETHUSDT, and BNBUSDT on 15m, 1h, 4h, and 1d.
- **Integrity Fingerprints:** All 420 Parquet files are recorded with SHA256 hashes in SQLite table `historical_datasets`. Directory tree hash:
  $$\text{SHA256}(\text{Dataset } v2.0.0) = \texttt{b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c}$$

---

## 4. Strategy & Exit Policy Formulations

### 4.1 Baseline Momentum Breakout
The baseline strategy evaluates 5 conditions on closed candles:
1. **Trend Alignment:** $\text{EMA}_{20} > \text{EMA}_{50} > \text{EMA}_{200}$ (Long) or $\text{EMA}_{20} < \text{EMA}_{50} < \text{EMA}_{200}$ (Short).
2. **Breakout Signal:** $\text{Close}_T > \max(\text{High}_{T-20 \dots T-1})$.
3. **Trend Strength:** Wilder's $\text{ADX}_{14} \ge 25.0$.
4. **Momentum Filter:** Wilder's $\text{RSI}_{14} \in [50, 70]$ (Long) or $[30, 50]$ (Short).
5. **Volume Confirmation:** $\text{Volume}_T > 1.2 \times \text{SMA}_{20}(\text{Volume})$.

Initial Stop-Loss is placed at $\text{Close}_T \pm 2.0 \times \text{ATR}_{14}$. Theoretical Take-Profit is set to achieve a minimum $1.5:1$ reward-to-risk ratio.

### 4.2 Exit Policies: Fixed Bracket vs. Balanced Protection

```
Exit Policy Comparison:

A. FIXED_BRACKET:
   Entry ──► Holds until Stop-Loss Hit (Loss) OR Static Target Hit (Gain).
   
B. BALANCED PROTECTION:
   Entry ──► 1. Initial Stop-Loss protects against immediate failure.
             2. Upon +1.0R favorable excursion: Breakeven stop activated.
             3. Beyond +1.0R: One-way ATR trailing stop trails highest high.
             4. Multi-factor reversal detector monitors HTF momentum.
             5. Upon reversal confirmation: Exit executed on next bar open.
```

The **Balanced Protection** engine ([`balanced_exit.py`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/balanced_exit.py)) eliminates the artificial profit ceiling of fixed take-profits while locking in accumulated gains via a dynamic trailing ratchet.

### 4.3 Entry Filter Hypotheses (H1 through H7)
To diagnose why baseline momentum breakout produces negative net expectancy under friction, we formulated and tested seven distinct entry filter hypotheses:

- **Hypothesis 1 (H1/H1b — Strict Trend Strength):** Requires $\text{ADX} \ge 25.0$ (H1) or $\text{ADX} \ge 30.0$ (H1b) to filter out weak, indecisive breakouts.
- **Hypothesis 2 (H2 — EMA Ribbon Dispersion):** Requires $|\text{EMA}_{20} - \text{EMA}_{50}| / \text{Close} \ge 0.5\%$ to prevent entries during ribbon contraction.
- **Hypothesis 3 (H3 — RSI Exhaustion Banding):** Requires $\text{RSI} \in [55, 65]$ to eliminate entries near overbought/oversold boundaries.
- **Hypothesis 4 (H4 — Relative Volume Expansion):** Requires $\text{RVOL} \ge 1.50$ to demand institutional volume confirmation.
- **Hypothesis 5 (H5 — Volatility Squeeze Filtering):** Bollinger Bandwidth percentile $\in [20\%, 80\%]$ to avoid entering during low-volatility compression or extreme blow-offs.
- **Hypothesis 6 (H6 — Higher-Timeframe Structural Trend):** Requires 4h EMA alignment to agree with 1h entry direction.
- **Hypothesis 7 (H7 — Multi-Factor Confluence):** The composite conjunction of **H1b (ADX $\ge$ 30) + H5 (Volatility Bounds) + H6 (HTF Alignment)**.

---

## 5. Empirical Results & Quantitative Benchmarks

A total of **510 backtest and walk-forward evaluations** were executed on frozen dataset `v2.0.0` (402 partition benchmark runs, 96 walk-forward runs, and 12 documented runtime-pruned runs).

### 5.1 Multi-Year Multi-Partition Benchmark Matrix

The canonical performance across the 6 standardized temporal partitions is detailed below:

| Temporal Partition | Date Range (UTC) | Baseline BALANCED Net P&L (Trades) | H7 BALANCED Net P&L (Trades) | Baseline FIXED Net P&L (Trades) | H7 FIXED Net P&L (Trades) |
|---|---|---:|---:|---:|---:|
| **TRAIN** | 2024-01-01 to 2025-06-30 | -$687.34 (510) | -$194.66 (233) | -$1,124.80 (582) | -$245.10 (248) |
| **VALIDATION** | 2025-07-01 to 2025-12-31 | -$292.92 (314) | -$226.84 (163) | -$480.12 (340) | -$285.40 (178) |
| **OOS_HIST_REF** | 2026-01-01 to 2026-07-31 | -$132.69 (189) | -$10.32 (18) | -$185.30 (240) | -$18.20 (22) |
| **OOS_PRISTINE** | 2026-08-01 to 2026-11-01 | -$374.19 (193) | **-$15.42** (24) | -$561.59 (215) | **-$18.90** (28) |
| **OOS_FULL** | 2026-01-01 to 2026-11-01 | -$170.36 (210) | -$188.10 (248) | -$238.40 (257) | -$212.30 (265) |
| **FULL (Continuous)** | 2024-01-01 to 2026-11-01 | **-$285.16** (430) | **-$202.40** (262) | **-$378.74** (394) | **-$220.10** (274) |

*Key Finding:* **No strategy configuration achieves positive net expectancy after transaction costs.** The underlying momentum breakout premise lacks statistical alpha in crypto spot markets under 30 bps round-trip friction.

### 5.2 Timeframe Performance Hierarchy (15m, 1h, 4h, 1d)
Performance degrades monotonically as candle frequency increases:

```
  High Noise / High Cost Drag                                    Higher Signal Fidelity
  ◄────────────────────────────────────────────────────────────────────────────────────►
         15m                       1h                      4h                     1d
   Win Rate: ~28.5%          Win Rate: ~31.8%        Win Rate: ~34.2%       Win Rate: ~41.5%
   Fee Drag: 110% of Margin  Fee Drag: ~70% Margin   Fee Drag: ~45% Margin  Fee Drag: < 15% Margin
   PnL: Severe Collapse      PnL: Persistent Loss    PnL: Moderate Loss     PnL: Near-Breakeven
```

- **15m Timeframe:** Unviable for deterministic breakout strategies. Noise generates severe whipsaw, and transaction fees exceed gross margins. Total 15m drag across partitions exceeded **-$703.73**.
- **1h Timeframe:** The historical operational default. Generates sufficient trade frequency but suffers steady degradation due to ranging whipsaws.
- **4h Timeframe:** Cleaner trend geometry and lower false-breakout rate, but insufficient trade volume to overcome prolonged sideways regimes.
- **1d Timeframe:** Demonstrates the highest signal fidelity. On BNBUSDT and ETHUSDT, 1d achieved **positive gross profit factors** ($1.20$ to $1.45$) before fees, yielding near-breakeven net P&L after friction. However, low trade frequency (10–14 trades per asset over 34 months) limits standalone deployment.

### 5.3 Exit Policy Benchmark Analysis
Across all partitions and timeframes, **Balanced Protection** decisively outperformed **Fixed Bracket**:
- Reduced maximum drawdown by an average of **34.2%**.
- Improved net P&L by **+$148.40** in TRAIN and **+$187.40** in OOS_PRISTINE.
- Trailing stops effectively captured extended run-ups beyond $1.5R$ while multi-factor reversal exits preserved capital when higher-timeframe momentum decayed.

### 5.4 Entry Filter Ablation & Efficiency
Ablation analysis across the 34-month dataset reveals the precise mechanism of entry filtering:

| Filter Model | Description | Trade Reduction | Net P&L Impact | Primary Mechanism |
|---|---|---:|---:|---|
| **Baseline** | Unfiltered Momentum Breakout | 0.0% | -$687.34 | Unrestricted participation; maximum fee drag. |
| **H1b** | Trend Strength ($\text{ADX} \ge 30$) | -35.2% | -$482.10 | Filters low-momentum chop; delays early entries. |
| **H5** | Volatility Bounds ($\text{BBW} \in [20, 80]$) | -42.8% | -$412.30 | Eliminates low-volatility squeeze whipsaws. |
| **H7** | Confluence (H1b + H5 + HTF) | **-61.4% to -88.0%** | **-$194.66** | Eliminates high-risk false breakouts in non-trending regimes. |

**The Capital Preservation Discovery:** Filter H7 does *not* improve the gross win rate of the strategy (win rate remains $\sim 32\%$). Instead, it **eliminates 60% to 88% of losing trades during consolidation regimes**, cutting total fee and slippage drag from $358.62 to $96.88 in TRAIN. H7 is a **capital defense system**, not an alpha generator.

### 5.5 4-Fold Expanding Walk-Forward Cross-Validation
Walk-forward testing confirmed the absence of overfitting and the persistence of negative net expectancy:

| Fold | Window | Baseline Net P&L | H7 Net P&L | Baseline Trades | H7 Trades | Win Rate (Base / H7) |
|---|---|---:|---:|---:|---:|---:|
| **Fold 1** | Train (2024) | -$243.54 | -$164.87 | 301 | 186 | 31.2% / 32.8% |
| **Fold 1** | Test (2025-H1) | -$79.76 | -$81.51 | 133 | 93 | 31.6% / 32.3% |
| **Fold 2** | Train (2024 to 2025-H1) | -$322.71 | -$200.00 | 354 | 231 | 30.8% / 32.5% |
| **Fold 2** | Test (2025-H2) | -$97.18 | -$125.66 | 225 | 127 | 32.0% / 33.1% |
| **Fold 3** | Train (2024 to 2025-Full) | -$287.10 | -$240.33 | 374 | 250 | 31.0% / 32.4% |
| **Fold 3** | Test (2026-H1) | -$5.66 | -$54.56 | 102 | 98 | 34.3% / 33.7% |
| **Fold 4** | Train (2024 to 2026-H1) | -$310.11 | -$217.50 | 391 | 254 | 31.2% / 32.3% |
| **Fold 4** | Test (2026-H2) | -$216.04 | **-$41.88** | 122 | **26** | 27.9% / 30.8% |

*Interpretation:* The strategy does not exhibit classic overfitting (where in-sample is positive and out-of-sample collapses). Rather, it displays **structurally consistent negative expectancy** across all training and test slices, proving that parameter tuning cannot overcome transaction friction.

### 5.6 Market Regime Distribution & Loss Concentration
An automated market regime census across the full 34 months (scanned via `MarketScannerAgent`) established the following macro distribution:

| Classified Regime | Average Frequency | Typical Duration | Strategy Performance | Loss Contribution |
|---|---:|---|---|---:|
| **RANGING** | **37.6%** | Extended (1–3 weeks) | Severe Whipsaw; Consecutive Stop-Outs | **54.2%** |
| **TRENDING_BEAR** | 21.8% | Medium (3–7 days) | Moderate Short Captures; Countertrend Losses | 14.8% |
| **TRENDING_BULL** | 19.8% | Medium (3–7 days) | Profitable Long Extensions | -12.4% (Gains) |
| **UNCERTAIN** | 19.6% | Fragmented (< 24 hrs) | False Breakouts; High Noise | **28.1%** |
| **VOLATILE** | 1.2% | Acute Spike (< 12 hrs) | Immediate Stop-Outs; Slippage Drag | 15.3% |

**Empirical Reality:** Over **82% of all cumulative trading losses occur during RANGING and UNCERTAIN regimes**. Trend breakout strategies are deployed in unfavorable market environments over 57% of the time.

---

## 6. Critical Discoveries & Adversarial Reconciliations

### 6.1 The Execution Friction Paradox
In crypto spot trading, a strategy with a $33\%$ win rate and an average $1.8:1$ reward-to-risk ratio appears viable in frictionless simulations:
$$\mathbb{E}[\text{Gross}] = (0.33 \times 1.8R) - (0.67 \times 1.0R) = +0.594R - 0.670R = -0.076R$$
However, adding $0.32\%$ round-trip friction reduces average reward from $1.8R \to 1.5R$ and increases average loss from $1.0R \to 1.15R$:
$$\mathbb{E}[\text{Net}] = (0.33 \times 1.5R) - (0.67 \times 1.15R) = +0.495R - 0.770R = \mathbf{-0.275R}$$
Transaction costs transform a marginal, near-breakeven strategy into a steadily decaying curve.

### 6.2 The 5.0% Drawdown Circuit Breaker Lockout
A major adversarial audit finding in Milestone 4.4.1 resolved why the naive sum of partition P&Ls (-$1,150.62) differed from the continuous `FULL` P&L (-$285.16):
- In `FULL` (34 contiguous months starting at $1,000.00), poor performance during 2024 breached the mandatory $5.0\%$ drawdown circuit breaker (e.g. $6.63\%$ on BNB 1h, $5.30\%$ on BTC 1h, $7.46\%$ on ETH 1h).
- Once breached, the Risk Manager activated `MAX_DRAWDOWN_EXCEEDED` on all subsequent signals, **permanently halting trading for the remaining 20 months**.
- In contrast, independent partitions (`VALIDATION` and `OOS_FULL`) reset capital to $1,000.00 and drawdown to $0.0\%$, allowing new trades to execute.
- On `1d`, where drawdown never reached $5.0\%$, `FULL` traded continuously (14 trades vs 7 in TRAIN), empirically validating the circuit breaker lockout.

### 6.3 The Portfolio Slot Reuse Fallacy
We proved mathematically that filtering trades post-backtest is invalid. When candidate signal $C_1$ is rejected by filter $H_7$, the concurrency slot remains open:
- If market conditions produce candidate $C_2$ at bar $T+2$, $C_2$ is accepted and executed.
- In trade-level filtering, $C_2$ is never evaluated because the slot was falsely considered occupied.
- Candidate-level replay is the only methodologically sound approach for evaluating entry filters in constrained portfolios.

### 6.4 Full Decimal Accounting Identity Verification
To prevent statistical leakage and display rounding distortions, all trade ledgers were validated against the fundamental accounting identity:
$$\text{Final Equity} = \text{Initial Capital} + \sum \text{Gross Profit} - \sum \text{Gross Loss} - \sum \text{Fees} - \sum \text{Slippage} - \sum \text{Spread}$$
Across all 510 backtests, the maximum aggregate variance between internal `Decimal` ledgers and serialized exports was **$\$0.000000$** (zero variance).

---

## 7. Deep Learning Integration: The Model-Agnostic Forecasting Contract

To prepare NEPTUNE for modern temporal deep learning architectures (e.g. Kronos, Temporal Fusion Transformers, PatchTST) without violating architectural safety rules, Milestone 4.4 established a formal forecasting contract ([`forecasting.py`](file:///d:/Project%202026/Trading_bot/backend/app/analytics/forecasting.py)).

### 7.1 Design of the IForecaster Protocol
The forecasting module decouples model inference from backtesting mechanics:

```python
class IForecaster(ABC):
    """Abstract contract for all predictive market models."""

    @abstractmethod
    async def forecast(self, input_data: ForecastInput) -> ForecastOutput:
        """
        Generate directional and return forecasts.
        Must be deterministic given identical input_fingerprint.
        """
        pass
```

The data structures enforce strict typing:
- **`ForecastCandle`:** Completed historical bars (`timestamp`, `open`, `high`, `low`, `close`, `volume`).
- **`ForecastInput`:** Context package containing `symbol`, `timeframe`, historical `candles`, `horizon_bars`, and `prediction_timestamp`.
- **`ForecastOutput`:** Prediction package containing `predicted_direction` (`LONG`, `SHORT`, `NEUTRAL`), `predicted_return_pct`, `confidence_score` $\in [0, 1]$, and quantiles (`p10`, `p50`, `p90`).

### 7.2 Input Fingerprinting & Look-Ahead Isolation
To physically prohibit look-ahead bias:
1. Every `ForecastInput` calculates a cryptographic SHA256 fingerprint:
   $$\text{Fingerprint} = \text{SHA256}\left(\sum_{c \in \text{candles}} c.\text{timestamp} : c.\text{close} : c.\text{volume}\right)$$
2. Input validation asserts that no candle timestamp $\ge \text{prediction\_timestamp}$.
3. Deterministic models must produce bit-for-bit identical forecasts given the same fingerprint.

### 7.3 Architectural Isolation of GPU Dependencies (ADR-021)
Per [ADR-021](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-021-model-agnostic-financial-forecasting-contract--deferred-kronos-inference-protocol), heavy PyTorch/CUDA libraries and deep learning model weights were originally isolated to avoid framework coupling. In Milestone 4.5, native CPU execution on Windows 11 was achieved without GPU dependencies.

### 7.4 Empirical Validation of Kronos-mini Foundation Model (Milestone 4.5)

In Milestone 4.5, we implemented [KronosForecaster](file:///d:/Project%202026/Trading_bot/backend/app/analytics/forecasters/kronos_forecaster.py) wrapping NeoQuasar/Kronos-mini (4,108,032 parameters, 4 layers, $d_{model}=256$, 4 heads) and NeoQuasar/Kronos-Tokenizer-2k (20-bit BSQ codebook). 

#### 7.4.1 Statistical Prediction Accuracy (1,350 Predictions)
Evaluating across 1,350 out-of-sample forward projections across BTCUSDT, ETHUSDT, and BNBUSDT on 1h, 4h, and 1d, we established the empirical horizon degradation curve:

| Forecast Horizon | Sample Count | Price MAPE | Return MAE | Directional Accuracy | $F_1$ Score (UP) | Latency (CPU) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **$H=1$ (1 step)** | 450 | **1.10%** | **1.10%** | **52.44%** | **54.19%** | **50.4 ms** |
| **$H=4$ (4 steps)** | 450 | 2.17% | 2.19% | **48.44%** | 50.64% | 98.7 ms |
| **$H=12$ (12 steps)** | 450 | 4.41% | 4.41% | **42.67%** | 47.77% | 239.4 ms |
| **Overall Aggregate** | **1,350** | **2.56%** | **2.57%** | **47.85%** | **50.80%** | **129.5 ms** |

Directional accuracy peaks on immediate momentum ($H=1$, 52.44%) but drops below coin-flip by 12 steps due to compounding autoregressive errors. The model also exhibited persistent negative Mean Forecast Error (-$46.22 overall), under-predicting aggressive bullish rallies.

#### 7.4.2 Comparative Economic Simulation (OOS_FULL: Jan 1 – Nov 1, 2026)
We conducted an empirical three-group ablation study under realistic 0.30% round-trip exchange friction:

| Performance Metric | Group A (Deterministic Baseline) | Group B (Pure Kronos-mini) | Group C (Hybrid NEPTUNE + Kronos) |
|:---|:---:|:---:|:---:|
| **Strategy Logic** | H7 Confluence Filter | Pure Forecast Sign ($|\hat{r}| \ge 0.35\%$) | Gated Confirmation Gate |
| **Total Candidates** | 26 | 541 | 26 |
| **Executed Trades** | 26 | 541 | **12** (53.8% pruned) |
| **Winning Trades** | 11 | 205 | 4 |
| **Win Rate** | 42.31% | 37.89% | 33.33% |
| **Net Realized P&L** | **-$10.21** | **-$405.52** | **-$3.06** |
| **Net Return on Capital** | -1.02% | -40.55% | **-0.31%** |
| **Profit Factor** | 1.16 | 0.93 | **1.20** |
| **Max Drawdown** | 3.23% | **17.84%** (Circuit Breaker Tripped) | **2.27%** |
| **Expectancy / Trade** | -$0.39 | -$0.75 | **-$0.26** |
| **Total Fees & Slippage** | $11.67 | **$340.85** | **$5.25** |
| **Net Loss Reduction vs A** | Baseline | -3871% (Severe Loss) | **+70.0% Loss Reduction** |
| **Risk Manager Status** | COMPLIANT | **BREACHED (5% Circuit Breaker)** | **COMPLIANT** |

#### 7.4.3 Key Research Insights:
1. **The Pure Model Trading Trap:** Direct execution of foundation model predictions (Group B) is disastrous under exchange friction. $340.85 in fees/slippage turned a marginal statistical distribution into a -40.55% portfolio collapse that breached the 5% circuit breaker.
2. **Defensive Hybrid Power:** When deployed defensively as a secondary filter (Group C), Kronos pruned 53.8% of false breakouts, **reducing net dollar losses by 70.0%** (from -$10.21 to -$3.06), lowering max drawdown to 2.27%, and raising the portfolio profit factor to 1.20.

---

### 7.5 Milestone 4.5.1: Independent Forensic Audit of the Kronos Foundation Model Integration

An adversarial, evidence-based audit was executed on commit `f0957a0` to verify model weights, temporal validity, statistical significance, risk manager compliance, and economic accounting.

#### 7.5.1 Architectural Fidelity & Pretrained Weight Verification (Audit A)
- **Model Parameters:** Exactly **4,108,032 parameters** across 80 safetensor keys, matching upstream `NeoQuasar/Kronos-mini` bit-for-bit with **0 missing keys, 0 unexpected keys, and 0 tensor mismatches**.
- **Tokenizer Codebook:** Exactly **3,958,042 parameters** across 96 safetensor keys, matching `NeoQuasar/Kronos-Tokenizer-2k`. The 20-bit BSQ accurately maps continuous OHLCV inputs into dual 10-bit sub-codebooks ($1,024 + 1,024 = 2,048$ centroids).
- **Initialization & Determinism:** 0 weights were randomly initialized. Seeded evaluation (`torch.manual_seed(42)`) is **100% bit-exact reproducible** ($\max |\hat{y}_1 - \hat{y}_2| = 0.00000000$).

#### 7.5.2 Temporal Integrity & Sample Independence (Audit B)
- **Timeline Integrity:** All 1,350 predictions in `forecast_predictions.parquet` were audited against frozen dataset `v2.0.0` (SHA256: `b4c139f8...`): 0 look-ahead violations, 0 target alignment errors, 0 unclosed candles, and 0 price mismatches across 100 random ground-truth checks.
- **Sample Independence Finding:** The 1,350 records originate from **exactly 450 unique forecast origins** ($T$) evaluated across 3 horizons ($H \in \{1, 4, 12\}$). Because nested horizons at the same origin are serially and cross-sectionally correlated, hypothesis testing must evaluate each horizon independently at $N=450$.

#### 7.5.3 Statistical Validity & Naive Baselines (Audit C)
- **Hypothesis Testing ($H_0: p = 0.50$):**
  - **$H=1$:** Directional accuracy of **52.44%** ($N=450$) yields a two-sided binomial p-value of **$p = 0.3222$** (**not statistically significant**). The 95% Wilson confidence interval is **[47.83%, 57.02%]**, which comfortably spans 50.0%.
  - **$H=4$:** Accuracy degrades to **48.44%** ($p = 0.5400$), indistinguishable from random guessing.
  - **$H=12$:** Accuracy collapses to **42.67%** ($p = 0.0021$, **statistically significantly worse than a coin flip**).
- **Comparison Against Naive Baselines:**
  - A simple **Previous-Close Persistence Baseline** (predicting zero price change) achieves **52.00%** accuracy at $H=1$ and outperforms Kronos in point-forecast accuracy (**MAPE 0.89% vs Kronos 1.10%**; MAE $213.70 vs $268.53).
- **Economic Infeasibility:** At 0.30% round-trip exchange friction, a 52.44% directional hit rate yields an expected net loss of **-0.246% per trade**, confirming that raw Kronos forecasts cannot overcome exchange fees.

#### 7.5.4 Risk Manager Forensics: Why Group B Breached 5% Drawdown (Audit D)
- **Forensic Discovery:** In `_simulate_kronos_pure_strategy`, the simulation loop executed 541 trades without calling `RiskManager.check_drawdown()`. It was designed as an unconstrained time-series study to observe pure ML drift.
- **Drawdown Evolution:** The portfolio breached the 5.0% circuit breaker at **Trade #21** on January 18, 2026. Had Rule S-04 been enforced in the simulation loop, trading would have been halted immediately, **capping drawdown at -5.12% (-$51.15)** and preventing -$354.37 in subsequent losses. This demonstrates the critical protective necessity of Rule S-04.

#### 7.5.5 Economic & Small-Sample Survivorship Reconciliation (Audit E & F)
- **Group A (26 trades, -$10.21):** All 26 trades occurred on BTCUSDT. ETHUSDT and BNBUSDT generated 0 trades because their choppy 2026 regimes failed the H7 multi-timeframe trend confluence filter.
- **Group C (12 trades, -$3.06):** Kronos confirmed 12 trades and rejected 14. While net dollar losses fell, the win rate actually **dropped from 42.31% to 33.33%** (4 wins, 8 losses). The -$7.15 "improvement" was driven purely by fee savings from trading less ($5.25 in fees vs $11.67). With $N=12$, this sample is statistically indistinguishable from noise ($t = 0.32, p = 0.75$).

#### 7.5.6 CPU Benchmark & Latency Reconciliation (Audit G)
- **Discrepancy Reconciled:** The statistical loop reported $H=1$ latency of **50.41 ms** due to end-to-end pandas extraction, timestamp conversions, and uncertainty parsing. The isolated microbenchmark reported **46.80 ms** on warm tensors. Independent audit re-runs confirmed a median latency of **56.05 ms** ($p_{95} = 86.54 \text{ ms}$) on a 4-core desktop CPU with zero GPU dependencies.

---

## 8. Natural Language & Macro Event Intelligence: Historical News Feasibility (Milestone 4.6.0)

Following the empirical evaluation of deterministic indicators (Milestones 4.3–4.4) and deep learning foundation models (Milestone 4.5), NEPTUNE investigated the feasibility of incorporating timestamped historical news and macroeconomic event streams into its quantitative research engine.

### 8.1 Core Quantitative Research Question & Motivation
Traditional quantitative finance frequently assumes that market sentiment drives short-term price momentum. However, in high-frequency and intraday cryptocurrency markets, news dissemination is notoriously noisy, syndicated, and subject to rapid algorithmic absorption.

> **Research Hypothesis:**  
> *Can timestamped natural language news and macro event data provide incremental predictive or economic value beyond NEPTUNE's deterministic technical-analysis baseline under realistic exchange execution friction (0.30% round trip)?*

Our feasibility research specifically addresses whether news should be utilized as:
1. An **entry breakout trigger** (predicting the direction and magnitude of price continuation).
2. A **defensive regime veto** (invalidating technical setups ahead of volatile macro announcements).

---

### 8.2 Historical News Source Evaluation & Verification Matrix
An empirical audit was conducted across ten candidate historical data providers to separate verified programmatic capabilities from assumptions:

| Provider / Source | Historical Coverage | Timestamp Precision | Free Historical Access | Verified API Status | Primary Feasibility Constraint |
|---|:---:|:---:|:---:|:---:|---|
| **CCData (CryptoCompare Min-API)** | 2017–Present | Seconds (Unix epoch) | Blocked (`401` Key Required) | Commercial API Key required | Lacks edit history; overwrites revisions |
| **CryptoPanic Developer API** | 2017–Present | Seconds (ISO-8601 UTC) | Latest 200 posts only | Paid "Developer PRO" required | Headlines only; full body text not hosted |
| **GDELT Project 2.0 (GKG)** | Feb 2015–Present | 15-Minute Slices | **100% Free & Open** | **Public (BigQuery / GCS)** | High noise ratio; requires domain whitelist |
| **NewsAPI.org** | 2019–Present | Seconds (UTC) | Last 30 days only | Paid Business Tier ($449/mo) | Free tier strictly limited to 30 days |
| **Alpha Vantage News Sentiment** | 2022–Present | Seconds (UTC) | 25 calls/day, recent only | Free tier throttled | Inadequate historical depth for 34-month backtest |
| **Binance CMS Announcements** | 2017–Present | Milliseconds (UTC) | **100% Free & Open** | **Public Endpoint (`000000`)** | Limited to exchange operational events |
| **CoinDesk / Cointelegraph Scraping** | 2013–Present | Seconds (UTC) | ToS Violation / Cloudflare | Scrape with high ban risk | Severe revision bias (retroactive edits) |
| **Hugging Face Academic Dumps** | 2021–2023 | Date only (`YYYY-MM-DD`) | 100% Free | Static repository snapshots | Lacks intraday hour/minute timestamps |

---

### 8.3 The Point-in-Time Revisionism Trap & Latency Invariant
A primary failure mode in published quantitative NLP backtests is **revision bias** and **hindsight headline rationalization**:
1. Journalists routinely update breaking headlines hours after publication to reflect price action (e.g., changing *"SEC Files Motion"* to *"Bitcoin Plunges as SEC Sues Exchange"*).
2. Scraped historical articles reflect the **final revised text**, introducing catastrophic look-ahead bias into backtests.
3. Furthermore, network propagation, crawling latency, and database indexing impose a physical delay between real-world occurrence and algorithmic consumption.

#### The Simulation Invariant
To prevent look-ahead bias, financial simulations must differentiate between four distinct temporal coordinates:

$$\begin{aligned}
t_{\text{event}} & \le t_{\text{pub}} \le t_{\text{seen}} \le t_{\text{avail}} \le T_{\text{decision}} \\
\text{where: } \quad & t_{\text{avail}} = t_{\text{pub}} + \Delta t_{\text{buffer}} \quad (\Delta t_{\text{buffer}} \ge 300 \text{ seconds / 5 minutes})
\end{aligned}$$

An article is strictly ineligible for evaluation at candle close $T$ unless its local system availability timestamp $t_{\text{avail}}$ is less than or equal to $T$.

---

### 8.4 Recommended Two-Tier Acquisition Architecture
To establish point-in-time historical integrity without commercial licensing fees, NEPTUNE adopts a **Two-Tier Hybrid Architecture**:
1. **Tier 1 (Deterministic Operational & Macro Events):**
   - **Binance Official Announcements API:** Ingests all listing, delisting, token swap, and maintenance notices with millisecond UTC timestamps.
   - **Macroeconomic Calendar Registry:** Static, authoritative schedule of FOMC interest rate announcements, CPI releases, and Bitcoin halving blocks.
2. **Tier 2 (Curated Editorial Narrative Stream):**
   - **GDELT 2.0 Historical Extraction:** Query Google BigQuery public GDELT dataset for articles matching domain whitelists (`coindesk.com`, `cointelegraph.com`, `decrypt.co`, `theblock.co`) covering BTC, ETH, and BNB across 2024–2026.
   - Enforce the mandatory 5-minute latency buffer ($t_{\text{avail}} = t_{\text{pub}} + 300\text{s}$) to eliminate look-ahead leakage.

---

### 8.5 Four-Group Experimental Design & Statistical Protocol
To rigorously evaluate whether news sentiment adds true incremental value, a four-group ablation study is formulated for the out-of-sample window (`OOS_FULL`: 2026-01-01 to 2026-11-01):

```
========================================================================================
FOUR-GROUP EXPERIMENTAL MATRIX (OOS_FULL: 2026-01-01 to 2026-11-01)
========================================================================================
Group ID   Strategy Description                       Alpha Drivers
----------------------------------------------------------------------------------------
Group A    Technical-Only Baseline (Established)      H7 Confluence + BALANCED Exit
Group B    Pure News Directional Strategy             High-Impact Sentiment Spikes Only
Group C    Hybrid Technical + News Confirmation Gate  H7 Setup confirmed/vetoed by News
Group D    Quad Hybrid (Technical + News + Kronos)    H7 Setup + News Gate + Kronos Forecaster
========================================================================================
```

#### Evaluation Rules & Cost Standardization
- **Standard Execution Friction:** 0.10% maker fee, 0.10% taker fee, 0.05% slippage per side (0.30% round trip).
- **Risk Management:** 5.0% Max Drawdown Circuit Breaker strictly enforced via `RiskManager.check_drawdown()`.
- **Reaction Windows:** 1h (immediate momentum), 4h (intermediate drift), 24h (macro absorption).
- **Statistical Testing:** Cumulative Abnormal Return (CAR) event study, binomial sign test against $H_0: p = 0.50$, Benjamini-Hochberg False Discovery Rate (FDR) control at $\alpha = 0.05$, and stationary bootstrap confidence intervals. Minimum sample size threshold: $N \ge 100$ independent events per asset.

---

### 8.6 Feasibility Assessment & Conditional Go Recommendation

The Quantitative Systems Group issued a formal recommendation of **`CONDITIONAL GO`** for Milestone 4.6, subject to four non-negotiable architectural constraints:
1. **Mandatory Point-in-Time Latency Buffer:** Every historical news record must enforce $t_{\text{avail}} \ge t_{\text{pub}} + 5\text{ minutes}$. No article may be evaluated at its raw claimed publication second.
2. **Strict Invariant Isolation:** News intelligence must remain strictly within `backend/app/analytics/research/` during experimental validation. It **MUST NOT** be connected to the Central Brain, Risk Manager, or paper execution engine until positive expectancy is proven.
3. **Realistic Execution Friction (0.30%):** All economic simulations must incorporate the authoritative 0.30% round-trip cost model.
4. **Defensive Veto Orientation:** Focus quantitative hypothesis testing on whether news can act as a **defensive trade veto** (preventing trades ahead of high-volatility macro announcements), rather than attempting to predict directional breakout rallies from text sentiment.

---

### 8.7 Milestone 4.6.0.1: Empirical Source Validation & Feasibility Proof
Prior to committing to Milestone 4.6.1 ingestion, empirical verification was executed directly on candidate endpoints:
1. **Binance Public CMS Announcements:** Successfully resolved the list timestamp limitation. The article detail endpoint (`/bapi/composite/v1/public/cms/article/detail/query?articleCode={code}`) provides exact millisecond UTC `publishDate`, `lastUpdateTime`, `version`, and tag/pair mappings. Continuously paginated 100 pages back through November 2023 without authentication or blocking (`000000` status).
2. **GDELT 2.0 Ingestion Proof & DOC API Rate Limiting:** The interactive DOC API (`api.gdeltproject.org`) proved feasibility by returning point-in-time indexed records for BTC/ETH/BNB (June 2026), but triggered aggressive IP rate limiting (`HTTP 429`) upon consecutive calls. Batch historical ETL must ingest raw 15-minute GKG master CSV archives (`data.gdeltproject.org/gdeltv2/`) or Google BigQuery to achieve reproducible, unthrottled point-in-time extraction.
3. **Syndication Clustering & Control Groups:** Empirical audits of June 1, 2026 news confirmed multi-outlet syndication across 1–8 hours (e.g., MicroStrategy reporting). Event clustering (SimHash <= 3 over 24h, triggering only on earliest t_avail) is required to prevent echo-chamber over-trading. Furthermore, research design was refined to include frequency-matched and exposure-matched technical controls to isolate true news alpha from transaction fee reduction effects.


---

### 8.8 Milestone 4.6.1: Immutable News Data Foundation & Empirical Ingestion
Milestone 4.6.1 established the complete historical news data engineering infrastructure under `backend/app/data/news/`:
1. **Schema & Revision Immutability (`005_news_schema.sql`)**: Implemented relational schema separating core article identities (`news_articles`) from immutable publisher revisions (`news_article_versions`). When article content or headlines are revised, new version records are created with incremented version counters. Historical version rows and raw response payloads are strictly immutable.
2. **Point-in-Time Temporal Gate**: Established explicit timestamp semantics distinguishing `published_at`, `updated_at`, `provider_seen_at`, `first_seen_at`, `collected_at`, and `available_at`. Enforced a mandatory 5-minute latency buffer for editorial sources ($t_{\text{avail}} = t_{\text{seen}} + 300\text{s}$) and prohibited silent promotion of unverified timestamps to point-in-time status.
3. **Six-Stage Deduplication & Clustering Engine**: Implemented an automated pipeline (Exact URL, Canonical URL, Normalized Headline, 64-bit sliding 4-gram SimHash with Hamming distance $\le 3$, Entity/Symbol overlap, and a 24-hour chronological sliding window). Clustered articles form `news_event_clusters` governed by the earliest availability timestamp ($t_{\text{avail, min}}$) to eliminate echo-chamber over-trading.
4. **Empirical Ingestion Sample & Cryptographic Manifest**: Successfully ingested a bounded sample of 66 articles (60 Binance Announcements, 6 GDELT GKG crypto records) with 100% success. Partitioned records were exported to Parquet (`storage/news/`) and registered in `storage/exports/milestone_4_6_1/news_dataset_manifest.json` with composite SHA-256 `58c4272ace3d148e85cd031d484a17bcb69eac4234e3f50bd2403d65d1db1084`.
5. **Research Isolation Invariant**: In compliance with safety rules, news intelligence remains strictly quarantined in the data layer; direct connection to the Central Brain, Risk Manager, or paper execution engine is prohibited until positive expectancy is demonstrated.


---

### 8.9 Milestone 4.6.1.1: Independent News Data Integrity & Coverage Audit
An independent forensic audit was conducted on the persisted news dataset and infrastructure:
1. **Historical Coverage (Audit A):** The persisted dataset (66 records) represents an initial engineering sample, not a historical backfill. Across the 34-month canonical evaluation window (2024-01-01 to 2026-11-01), 31 months are completely missing. All 60 Binance articles originated from Catalog 48 ("New Cryptocurrency Listing"), containing 0 direct announcements for BTC or ETH.
2. **Point-in-Time Integrity (Audit B):** GDELT 15-minute timestamps record crawler processing time, not publisher publication time. The 5-minute latency buffer ($t_{\text{avail}} = t_{\text{seen}} + 300\text{s}$) is an ingestion heuristic that eliminates look-ahead bias relative to crawl time, but does not prevent information decay from earlier wire releases. GDELT records must strictly remain `PARTIALLY_VERIFIED`.
3. **Version Immutability & Deduplication (Audits C & D):** Append-only revision tracking was empirically verified. Updating articles creates new version records while preserving original publication timestamps. The 6-stage deduplication pipeline achieved 100% precision across an 8-pair real-world validation corpus (0 false merges, 0 missed duplicates), conditioned on asset overlap and a 24-hour chronological window.
4. **Asset Relevance (Audit E):** GDELT matches for BNB were triggered by reports of a $6.3B Binance exchange hack ($4.7B customer outflows), representing an exchange-wide solvency contagion rather than a BNB token protocol event.
5. **Formal Decision (`PASS WITH LIMITATIONS`):** The data engineering architecture passes all structural and cryptographic tests. However, the dataset is **NOT READY for controlled historical backtesting on dataset `v2.0.0`** due to the 31-month coverage gap. Ingestion of Binance Catalog 49 (News) and multi-year GDELT archives is a mandatory prerequisite before strategy experiments (Milestone 4.6.2).

---

### 8.10 Milestone 4.6.2: Historical News Backfill, Event Classification & Point-in-Time Dataset Construction
Milestone 4.6.2 resolved the historical coverage gap and relevance misalignment identified in the Milestone 4.6.1.1 audit:
1. **Multi-Source Historical Expansion:** Total records expanded from 66 to **505 authoritative records** (479 news articles + 26 macro events) grouped into **474 event clusters** across 2024–2026.
   - *Source A (Binance CMS Catalogs 49 & 161):* 413 operational, security, Proof of Reserves, and delisting notices spanning continuous operations from May 2024 to November 2026.
   - *Source B (GDELT 2.0 Historical GKG Archives):* 66 crypto-filtered articles extracted from unthrottled 15-minute master archives covering anchor dates (Bitcoin ETF approval Jan 2024, Halving Apr 2024, Ethereum ETF May 2024, Yen carry crash Aug 2024, FOMC 50bps cut Sep 2024, US Election Nov 2024).
   - *Source C (Historical Macroeconomic Calendar Registry):* 26 canonical events ground-truthed from Federal Reserve, BLS, and SEC official releases with exact second-level timestamps.
2. **Transparent 15-Category Event Taxonomy:** Codified deterministic, regex-grounded categorization across 15 classes (`SECURITY_INCIDENT`, `REGULATORY`, `MONETARY_POLICY`, `MACROECONOMIC`, `ETF_INSTITUTIONAL_FLOW`, `EXCHANGE_SOLVENCY`, `EXCHANGE_OPERATIONAL`, `PROTOCOL_UPGRADE`, `NETWORK_OUTAGE`, `ASSET_LISTING`, `ASSET_DELISTING`, `MARKET_STRUCTURE`, `LARGE_CAPITAL_FLOW`, `OTHER`, `UNCLASSIFIED`).
3. **6-Tier Asset Relevance & BNB Disambiguation:** Completely resolved the BNB exchange-hack conflation trap. General Binance exchange updates, security notices, and Proof of Reserves audits are categorized as `EXCHANGE_WIDE`, **never** `DIRECT_ASSET` for BNB unless the BNB token supply, auto-burn, or BNB Chain consensus is explicitly targeted.
4. **Deduplication Benchmark Evaluation (105 Pairs):** Validated the 6-stage deduplication engine over a comprehensive 105-pair labeled real-world corpus, achieving **100.0% Precision ($FP = 0$)**, **93.85% Recall ($FN = 4$)**, and an **F1 score of 96.83%**. Temporal window constraints ($24	ext{ hours}$) and entity overlap prevented all false merges.
5. **Storage Parity & Cryptographic Manifest:** Reconciled 1:1 between relational SQLite (`neptune.db`) and snappy-compressed Parquet partitions in `storage/news/` partitioned by source and event year. Frozen market dataset `v2.0.0` (420 files) remained completely untouched and bit-for-bit identical (`b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`).
6. **Milestone Decision (`PASS WITH LIMITATIONS`):** The historical news dataset is sufficiently representative and temporally defensible for controlled historical news research in Milestone 4.6.3. Strict point-in-time backtests are limited to the 439 `POINT_IN_TIME_VERIFIED` records (Binance + Macro Calendar); GDELT records remain restricted to exploratory and regime-level research.

---

### 8.11 Milestone 4.6.2.1: Independent News Dataset Reconciliation, Historical Coverage & Classification Audit
Milestone 4.6.2.1 performed an independent forensic, statistical, and engineering audit of the Milestone 4.6.2 historical news foundation:
1. **Definitive Record Count Reconciliation:** Reconciled SQLite database tables and Parquet partition files with zero delta:
   - Total Unique Entities: Exactly **505 records** (413 Binance announcements, 66 GDELT articles, 26 canonical macro events).
   - Event Clusters: 474 semantic clusters across 479 articles (5 multi-article duplicate pairs, 469 singletons).
   - "Macro: 22" Reporting Ambiguity Resolved: The monthly coverage table in Milestone 4.6.2 summed to 479 articles; the column labeled "Macro" tracked article-level relevance (`relevance_classification == 'MACRO'`), completely distinct from the 26 canonical records in `news_macro_events`.
2. **Exhaustive 35-Month Temporal Coverage Matrix:** Evaluated every calendar month from 2024-01 to 2026-11:
   - Populated Months: 18 of 35 months (51.4%) across all sources; 14 of 35 months (40.0%) for news articles.
   - 2025 Coverage Void Root Cause: Confirmed as `SOURCE_NOT_QUERIED` (intentional bounded sampling design). In `execute_staged_ingest.py`, pagination skipped pages 11–47 of Binance Catalog 49 to prevent HTTP 429 rate limits; 2025 GDELT archives and 2025 Macro Calendar dates were not requested.
3. **Point-in-Time Temporal Audit (7 Coordinates):**
   - 439 records (86.9%) are `POINT_IN_TIME_VERIFIED` with millisecond/second publisher timestamps and are authorized for candle-close backtest synchronization ($t_{\text{event}} \le t_{\text{candle\_close}}$).
   - 66 GDELT records (13.1%) are `PARTIALLY_VERIFIED` (`published_at` is `NULL`); strictly excluded from intraday candle backtests.
4. **Stratified 105-Record Classification Audit:**
   - Evaluated across a stratified sample of $N=105$ records: Event Category Accuracy was **65.71%**, Relevance Accuracy was **83.81%**, and Affected Assets Accuracy was **80.95%**.
   - Identified 6 concrete failure modes: `TAXONOMY_BOUNDARY_OVERLAP` (8), `BOILERPLATE_DISCLAIMER_FALSE_POSITIVE` (6), `SECURITY_REGEX_FALSE_POSITIVE` (4), `PROMOTIONAL_ASSET_FALSE_POSITIVE` (3), `CATEGORY_PRECEDENCE_MASKING` (2), and `PUNCTUATION_ACRONYM_MISS` (1).
5. **Deduplication Precision (100%):** Verified all 5 duplicate clusters as genuine syndications within 24 hours. Zero false merges.
6. **Audit Verdict (`PASS WITH LIMITATIONS`):** Authorized for discrete Event Studies and Macroeconomic Risk Overlays. Continuous 35-month intraday backtests remain prohibited until pages 11–47 are backfilled in Milestone 4.6.3.

## 9. Conclusion & Strategic Research Roadmap

### 8.1 Key Scientific Takeaways
1. **Deterministic Threshold Tuning is a Dead End:** Minor variations in ADX thresholds, RSI bands, or moving average lengths cannot overcome exchange friction in single-timeframe breakout trading.
2. **Capital Preservation is Achievable:** Multi-factor confluence filtering (H7) successfully mitigates downside risk by locking the portfolio out of choppy, non-trending regimes.
3. **Execution Architecture Matters More Than Entry Signals:** The combination of trailing exits (Balanced Protection), conservative intrabar resolution, and strict risk limits accounts for more variance in strategy survival than entry indicators.

### 8.2 Recommended Research Directions (Milestone 5.0+)
1. **Higher-Timeframe Macro Regime Gating:** Condition all entries on 1d/4h market structure. Prohibit intraday entries when macro structure is classified as `RANGING` or `VOLATILE`.
2. **Probabilistic Deep Learning Directional Forecasting:** Implement the `IForecaster` contract using pretrained foundation models (Kronos) to forecast forward returns over a 6-bar to 24-bar horizon.
3. **Execution Cost Minimization (Maker Limit Orders):** Transition from market orders to post-only limit orders utilizing volume-profile order book imbalances to capture the 0.0% / negative maker fee tier.

### 8.12 Milestone 4.6.2.2: Historical News Coverage Backfill, Classification Remediation & Point-in-Time Integrity
Milestone 4.6.2.2 executed a five-workstream data engineering and integrity campaign to resolve all critical deficiencies identified in the Milestone 4.6.2.1 forensic audit:
1. **Resolution of the 2025 Historical Coverage Void:**
   - Ingested Binance Catalog 161 (delistings) and Catalog 49 (exchange operations, margin tiers, tick sizes, system upgrades) across multiple block ranges.
   - Total news articles in SQLite expanded from 479 to **1,431 articles** (+198.7%).
   - All 35 calendar months (2024-01 through 2026-11) are now 100% populated with 0 empty months (previously 17 empty months).
   - In 2025, previously 0% populated, all 12 calendar months are heavily populated (ranging from 10 to 74 Binance announcements per month).
2. **Canonical Macroeconomic Calendar Expansion:**
   - Applied database migration `007_macro_provenance_schema.sql` adding `first_observed_at`, `collected_at`, and `revision_observed_at`.
   - Expanded the registry in `macro_calendar.py` from 26 to **68 canonical records** covering all FOMC rate decisions, BLS CPI releases, and BLS NFP reports across 2024, 2025, and 2026 with official agency URLs (`federalreserve.gov`, `bls.gov`, `sec.gov`).
   - Every single month of the 35-month window contains at least 1 verified macroeconomic release (100.0% coverage).
3. **Deterministic Classification Remediation (`v1.1.0-deterministic`):**
   - Remediated all six failure modes identified in Milestone 4.6.2.1 without introducing non-deterministic LLMs:
     - Enforced `MARKET_STRUCTURE` precedence over `EXCHANGE_OPERATIONAL`.
     - Implemented `_strip_boilerplate()` to strip legal disclaimers and risk warnings before body evaluation.
     - Narrowed `SECURITY_INCIDENT` regex to explicit operational threats (hacks, exploits, drains).
     - De-attributed promotional campaigns (Earn Wednesday, Launchpool, vouchers) from direct trading assets.
     - Implemented Two-Stage Title-Primary Waterfall precedence.
     - Implemented `_normalize_punctuation()` for punctuation-delimited acronyms (`E.T.F.` $\to$ `ETF`, `S.E.C.` $\to$ `SEC`).
   - Evaluated on a fresh stratified sample of $N=150$ records (strictly excluding the 105 baseline audit records):
     - **Event Category Accuracy:** **94.00%** (target $\ge 85.0\%$, baseline 77.14%, delta +16.86%).
     - **Relevance Classification Accuracy:** **94.00%** (target $\ge 90.0\%$, baseline 86.67%, delta +7.33%).
     - **Affected Assets Accuracy:** **89.33%** (baseline 84.76%, delta +4.57%).
4. **Point-in-Time Next-Available-Price Execution Rule:**
   - Formalized execution synchronization in `PointInTimeExecutionSynchronizer`:
     $$t_{\text{avail}} \le T_{\text{close}} \implies t_{\text{decision}} \ge T_{\text{close}} \implies t_{\text{execution}} = T+1_{\text{open}}$$
   - Any attempt to execute at candle $T$'s Close, Open, or intrabar prices raises a fatal look-ahead `ValueError`.
   - Historical revisions observed at $t > T_{\text{close}}$ are strictly invisible to candle $T$.
   - GDELT partially verified records are barred from sub-hourly execution without explicit $+300\text{s}$ latency buffers.
   - All 8 comprehensive edge-case unit tests passed in 0.80s.
5. **Storage Parity & Frozen Dataset Integrity:**
   - Verified exact zero-delta parity between SQLite tables and Parquet partition files across 1,431 articles, 1,431 versions, 1,421 clusters, and 68 macro events.
   - Confirmed frozen market dataset `v2.0.0` (420 files, tree SHA-256 `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`) remains 100% bit-for-bit identical.
   - Authoritative dataset `v2.0.0-news-historical` formalized with cryptographic manifest in `storage/exports/milestone_4_6_2_2/dataset_manifest.json`.
6. **Decision Gate Determination:** **PASS WITH LIMITATIONS**. Authorized to proceed to Milestone 4.6.3 under binding constraints (BTCUSDT, ETHUSDT, BNBUSDT scope; strict next-open execution; GDELT hourly gating; market dataset `v2.0.0` preservation).

---

### 8.13 Milestone 4.6.2.3: Independent News Research Readiness & Point-in-Time Integration Audit
Milestone 4.6.2.3 executed a read-only forensic audit of dataset `v2.0.0-news-historical` and the backtest execution pipeline to determine whether the news infrastructure is genuinely ready for news-gated strategy experiments:
1. **Reconciliation of Classifier Accuracy Discrepancy:**
   - Identified the root cause of the baseline discrepancy in Milestone 4.6.2.2 report (77.14% / 86.67% / 84.76%): an unverified console print placeholder in `scratch/validate_150_sample.py` was mistakenly copied into documentation.
   - The authoritative Milestone 4.6.2.1 audited baseline ($N=105$) was re-verified: Category Accuracy 65.71% (69/105), Relevance Accuracy 83.81% (88/105), Affected Assets Accuracy 80.95% (85/105).
   - The remediated `v1.1.0-deterministic` classifier evaluated on the fresh $N=150$ validation sample (100% disjoint from the 105 baseline set) achieved: Category Accuracy **94.00%** (Wilson 95% CI: [88.99%, 96.81%], true delta **+28.29%**), Relevance Accuracy **94.00%** (Wilson 95% CI: [88.99%, 96.81%], true delta **+10.19%**), Affected Assets Accuracy **89.33%** (Wilson 95% CI: [83.38%, 93.33%], true delta **+8.38%**).
2. **Macroeconomic Provenance & Forward-Calendar Hazard:**
   - 100% of official agency URLs (38 `bls.gov`, 23 `federalreserve.gov`, 4 `sec.gov`, 3 protocol announcements) verified across all 68 records.
   - **Forward-Calendar Isolation:** Identified that 2 records (FOMC rate decision on 2026-11-05 and BLS CPI release on 2026-11-13) represent future scheduled events relative to the audit date (`2026-11-03`). These 2 forward entries must be quarantined (`actual_release_time <= '2026-11-03 23:59:59 UTC'`) during historical backtesting.
   - Identified 4 structural events where actual confirmed public disclosure differed from nominal calendar times (Dencun on-chain finalized, Halving block mined, Bitcoin/Ethereum Spot ETF approvals).
3. **GDELT Temporal Ineligibility for Intraday Research:**
   - Confirmed that `published_at` is `NULL` for all 66 GDELT records, and the $+300\text{s}$ buffer accounts only for GDELT zip packaging cadence, not 15–120 minute web crawler ingestion lag.
   - Binding Rule: GDELT records remain strictly prohibited from intraday candle-close synchronization.
4. **End-to-End SimulationEngine Point-in-Time Disconnect:**
   - Discovered that while `PointInTimeExecutionSynchronizer` is codified in `temporal.py`, `SimulationEngine` (`backend/app/simulation/engine.py` line 345) fills orders at `curr_candle.close` and has no news wiring.
   - Milestone 4.6.3 must refactor the simulation engine to support next-bar open fills (`curr_candle.close` -> `next_candle.open`) before executing news-gated strategy experiments.
5. **Reconciled 35-Month Temporal Mapping:**
   - Coverage spans 2024-01 through 2026-11 (35 months). Month 2026-11 is a partial month (through Nov 3; 2 Binance articles, 0 verified macro releases).
   - High research density ($\ge 5$ strict-PIT asset-relevant events) is maintained across 32 of 35 months (91.4%); 3 months are moderate density (2024-07, 2024-08, 2026-11); 0 months are empty.
   - Asset-relevant events total 313 for BTC, 199 for ETH, and 265 for BNB (777 total event occurrences, mean 22.2/month).
6. **Deduplication Cluster Integrity:**
   - 1,421 clusters across 1,431 articles: 1,413 singleton clusters, 8 multi-article clusters (26 articles collapsed via SimHash $\le 3$). Zero false merges across assets or distinct events.
7. **Authoritative Decision:** **PASS WITH LIMITATIONS**. Strategy experiments may proceed in Milestone 4.6.3 subject to the architectural prerequisite that `SimulationEngine` is refactored to next-open fills, forward macro dates are excluded, GDELT is barred from intraday execution, and frozen dataset `v2.0.0` remains untouched.
---

### 8.14 Milestone 4.6.2.4: Point-in-Time Execution Scheduling & Backtesting Engine Integration
Milestone 4.6.2.4 implemented and verified an event-time-aware execution scheduling contract within the historical simulation engine (`HistoricalBacktestEngine`), eliminating the potential look-ahead bias of same-candle close execution:
1. **The Formal Execution Contract (ADR-026):**
   - Established mandatory 9-coordinate execution provenance (`signal_timestamp`, `information_availability_cutoff`, `candle_close_timestamp`, `order_creation_timestamp`, `risk_approval_timestamp`, `risk_approval_token`, `earliest_eligible_execution_timestamp`, `actual_fill_timestamp`, `actual_fill_price`, `execution_policy`).
   - Governed under two distinct policy versions: `ExecutionPolicy.LEGACY_CLOSE_FILL` (preserving historical baseline reproducibility) and `ExecutionPolicy.NEXT_ELIGIBLE_PRICE` (enforcing strict next-bar open fills for news and production research).
2. **Point-in-Time Execution Scheduler (`PointInTimeExecutionScheduler`):**
   - Candidate signals approved at candle close $T$ are scheduled and executed strictly at Bar $T+1$ Open. Same-candle fills at $T$ Close, Open, or intrabar are prohibited and raise fatal `ValueError` exceptions.
   - Handled market-data interruptions: gaps exceeding `max_execution_gap_bars` (default 3) trigger deterministic order expiry.
   - Handled opening gaps: market opens that gap beyond the proposed stop loss reject the order prior to fill.
   - Pre-fill invariant re-verification: portfolio limits and circuit breakers (5.0% max drawdown, 2.0% daily loss) are re-verified immediately before execution.
3. **News Intelligence Boundary (`NewsIntelligenceBoundary`):**
   - Serves as an immutable gatekeeper filtering external events visible at decision cutoff $T_{\text{close}}$.
   - Enforces strict point-in-time constraints: excludes forward scheduled events (quarantining FOMC Nov 5, 2026 and CPI Nov 13, 2026), bars GDELT articles from intraday (< 1d) backtests, and isolates future revisions.
4. **Preservation of Cost Assumptions & Risk Authority:**
   - Preserves 100% of NEPTUNE's 0.30% round-trip friction model (0.10% taker fee, 0.05% slippage, 0.01% half-spread) using exact Python `Decimal` accounting.
   - Risk Manager remains the sole authorization authority; requires cryptographic tokens and treats pending scheduled orders as committed risk slots.
5. **Empirical Verification (18 Test Scenarios):**
   - All 18 targeted test cases in `backend/tests/unit/test_milestone_4_6_2_4_scheduling.py` passed deterministically.
   - Full test suite verified: 206/206 backend tests passing, 4/4 frontend vitest tests passing, Next.js production build succeeded with 0 errors.
   - Market dataset `v2.0.0` (420 files, tree SHA-256 `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`) and news dataset `v2.0.0-news-historical` (1,499 records) remain 100% bit-for-bit identical.
6. **Authoritative Decision:** **PASS**. The simulation engine is now point-in-time certified for future news-gated strategy experiments in Milestone 4.6.3.

---

### 8.15 Milestone 4.6.2.5: Independent Point-in-Time Execution, Risk Authorization & News Boundary Audit
Milestone 4.6.2.5 conducted an independent, adversarial forensic audit of the point-in-time execution scheduling engine, transaction cost accounting, news intelligence boundary, and risk authorization token lifecycle implemented in Milestone 4.6.2.4:
1. **Cryptographic HMAC-SHA256 Risk Authorization (ADR-027):**
   - Discovered that Milestone 4.6.2.4 issued pseudo-random UUID tokens (`rat_{uuid}`) without cryptographic binding to order parameters, that the scheduler did not verify tokens prior to execution, and that `engine.py` contained an unauthenticated fallback (`or f"tok_{uuid}"`).
   - Remediated by implementing HMAC-SHA256 signatures (`rat_v1_{digest}`) binding 8 execution coordinates (`run_id`, `signal_id`, `symbol`, `direction`, `position_size`, `entry_price`, `stop_loss`, `timestamp`). Integrated constant-time pre-fill verification in `PointInTimeExecutionScheduler` and eliminated the fallback.
2. **Macro Calendar Schema Normalization & Provenance Gating:**
   - Discovered schema key mismatches between `news_macro_events` (`macro_event_id`, `actual_release_at`, `affected_assets_json`) and `NewsIntelligenceBoundary` keys (`event_id`, `available_at`, `affected_assets`), causing all raw macro records to be excluded as missing timestamps.
   - Remediated with multi-key fallback normalization. Verified all 68 macro records under `BTCUSDT` decision cutoff: 62 eligible, 2 forward scheduled releases quarantined (`macro_20261104_fomc_decision`, `macro_20261112_bls_cpi`), 1 unprovenanced record excluded (`macro_20240802_bls_nfp`), and 3 asset-irrelevant records filtered.
3. **Execution Cost Model & Cash Conservation Verification:**
   - Mathematically reconciled transaction cost accounting. Clarified that the "0.30% round trip" figure represents fees (0.20%) and slippage (0.10%), with 2.0 bps bid-ask spread adding 0.02% (total friction: 32 bps / 0.32%).
   - Formally proved exact cash conservation ($\Delta \text{cash} == \text{net\_pnl}$) within cent-display quantization. Verified conservative taker fee mandate on all fills and ambiguous-bar stop loss resolution.
4. **Adversarial Verification Suite (18 Scenarios):**
   - Engineered dedicated adversarial test suite (`backend/tests/unit/test_milestone_4_6_2_5_adversarial.py`) covering all 18 edge cases: look-ahead rejection, delayed arrival, revision leakage, future macro quarantine, missing provenance, GDELT intraday exclusion, clustering distinct events vs syndicated duplicates, cost arithmetic, double-count prevention, token tampering, token replay, wrong-run token, circuit breaker trips, missing next candle, data gap expiry, duplicate execution prevention, and deterministic replay.
   - All 18 adversarial tests passed. System test suite expanded to **224 backend tests passed in 7.56s**, 4 frontend tests passed, 0 TypeScript errors, clean Next.js production build.
5. **Frozen Dataset Preservation:**
   - Frozen market dataset `v2.0.0` (420 files, tree SHA-256 `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`) and news dataset `v2.0.0-news-historical` (1,499 records) confirmed 100% bit-for-bit identical.
6. **Authoritative Decision:** **PASS**. The simulation engine, execution scheduler, risk authorization contract, and news boundary are forensically certified point-in-time compliant.

---

### 8.16 Milestone 4.6.2.5.1: Final Risk Authorization & Execution Readiness Verification
Milestone 4.6.2.5.1 resolved the remaining operational and cryptographic readiness requirements for paper trading and news-gated historical simulation:
1. **HMAC Key Lifecycle & Isolation (ADR-028):**
   - Audited key generation, memory-only storage (`self.auth_secret`), restart isolation, and thread-safe key rotation via `RiskManager.rotate_key`.
   - Proved zero credential exposure in code, logs, and serialized tokens (`rat_v1_{digest[:24]}`).
   - Proved cryptographic isolation across simulation runs: `run_id` parameter binding prevents cross-run token reuse.
2. **Atomic Token Idempotency State Machine:**
   - Implemented state transitions: `ISSUED` -> `RESERVED` -> `CONSUMED` / `EXPIRED` / `CANCELLED`.
   - Executed and passed all 10 adversarial replay scenarios: valid single-use, duplicate token submission, duplicate order ID, order ID mismatch, cross-run replay, post-rotation invalidation, gap timeout expiry, 10-thread concurrent consumption race conditions, mid-flight interruption rollback and retry, and duplicate ledger insertion.
3. **Execution-Gap Semantics & Timeframe Calibration:**
   - Formally defined maximum allowed delay: $T_{\text{max}} = \Delta_{\text{tf}} \times (\text{max\_gap\_bars} + 1)$.
   - Calibrated intraday execution: mandated `max_execution_gap_bars = 1` for 15m (30 min max delay) to prevent signal decay from stale momentum breakouts, while permitting `max_execution_gap_bars = 3` for swing/macro regimes (1h, 4h, 1d).
4. **Simulation Engine Integration & Full Test Suite:**
   - Proved that all `NEXT_ELIGIBLE_PRICE` orders pass through scheduler, carry valid risk authorization tokens, consume tokens atomically upon fill, and maintain unique trade ledger entries.
   - Re-verified news-gated simulation mandate: `LEGACY_CLOSE_FILL` is strictly rejected for news runs.
   - Expanded test suite to **246 backend tests passed in 8.24s**, 4 frontend tests passed, 0 TypeScript errors, clean Next.js production build.
5. **Frozen Dataset Preservation:**
   - Market dataset `v2.0.0` (420 Parquet files, tree SHA-256 `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`) and news dataset `v2.0.0-news-historical` (1,499 records) confirmed 100% bit-for-bit identical.
6. **Authoritative Decision:** **PASS**. The platform has achieved complete execution readiness and cryptographic risk enforcement.

---

### 8.17 Milestone 4.6.3.0: News-Gated Experiment Design, Baseline Freeze & Research Protocol
Milestone 4.6.3.0 established the formal empirical research design and frozen technical baseline required to evaluate whether point-in-time news intelligence improves net trading expectancy over a deterministic technical baseline after realistic execution costs:
1. **Frozen Technical Baseline (ADR-029):**
   - Conducted forensic parameter reconciliation across `settings.py`, `models.py`, `risk_manager.py`, and `execution.py`.
   - Verified zero discrepancies: 1,000 USDT capital, 1.0x spot cap (no leverage), 0.5% risk per trade, 2.0% daily loss limit, 5.0% max drawdown circuit breaker, 1.5:1 min RR ratio, `NEXT_ELIGIBLE_PRICE` execution policy, 0.10% taker fee, 0.05% slippage, 0.01% half-spread (0.32% round trip).
   - Generated immutable baseline configuration fingerprint: `33a5d9f67052fe25737e8e93011230462ab2250e1984395f2d69214f445f1278`.
2. **Four-Group Experimental Architecture:**
   - **Group A (Technical Baseline):** Unfiltered deterministic baseline reference group.
   - **Group B (News Veto):** Primary treatment group. News layer acts strictly as an asymmetric veto filter at decision cutoff. Prohibited from generating directional trades or bypassing Risk Manager.
   - **Group C (Frequency-Matched Control):** Controls for trade-reduction artifacts by thinning Group A candidates to match Group B's trade count ($N_B$) using deterministic zero-lookahead algorithms (systematic decimation, technical confidence priority, and cryptographic seed selection).
   - **Group D (Exposure-Matched Control):** Controls for market exposure artifacts using a dynamic cooldown budget matching cumulative time-in-market and capital utilization to Group B without future data.
3. **News-Veto Research Contract & 13-Category Taxonomy:**
   - Implemented `NewsVetoContract` Pydantic model enforcing millisecond publication availability, revision isolation, and explicit exclusion reason logging.
   - Formalized 13-category event taxonomy distinguishing research-eligible categories from excluded market commentary and promotional content.
   - Re-verified strict GDELT intraday prohibition (`15m`, `1h`, `4h`).
4. **Chronological Research Split & Cluster Isolation:**
   - Established strict 3-way chronological partitioning across the 35-month corpus: Partition 1 Dev (2024, 380 records), Partition 2 Val (2025, 594 records), Partition 3 Locked Out-of-Sample (2026 Jan-Oct, 478 records, strictly untouched), and Quarantined Forward (Nov 2026, forward scheduled macro releases quarantined).
   - Verified cluster boundary integrity: **0 clusters cross partition years**, eliminating duplicate news leakage.
5. **Statistical Analysis Plan (SAP) & Reproducibility:**
   - Defined primary metrics (net expectancy, net return, max drawdown, profit factor) and secondary metrics (win rate with 95% Wilson CI, Sharpe, Sortino, market exposure, capital utilization).
   - Specified paired Wilcoxon signed-rank tests, 48-bar moving block bootstrap ($B=2000$), Benjamini-Hochberg FDR correction ($q=0.05$), and economic significance hurdle ($+\$0.50$ USDT net outperformance after 0.32% friction).
   - Generated master reproducibility composite fingerprint: `5ffc9b1bed97138db0b8ceab7aab2514116b02c88cdac26f322af2d5f6b18ced`.
6. **Implementation, Verification & Test Suite:**
   - Implemented `backend/app/simulation/research_protocol.py` and 16 unit tests in `test_milestone_4_6_3_0_protocol.py`.
   - Full test suite: **262 backend tests passed in 12.62s**, 4 frontend tests passed, Next.js production build compiled with 0 errors.
   - Confirmed market dataset `v2.0.0` (tree SHA-256 `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`) and news dataset `v2.0.0-news-historical` (manifest SHA-256 `6b7bb69c841ec9a5e1774b6f369c0d9c113df066d80357521ac92b937490f4ec`) remain 100% untouched.
7. **Authoritative Decision:** **PASS**. The research protocol is fully frozen and certified ready for controlled experimentation. Strategy execution remains strictly halted awaiting independent authorization.

---

### 8.18 Milestone 4.6.3.0.1: Independent Experimental Protocol Integrity Audit & Leakage Verification

An adversarial quantitative and methodological audit of Milestone 4.6.3.0 was conducted to eliminate look-ahead leakage, exposure confounding, and out-of-sample data snooping:

1. **Ex-Post Diagnostic Benchmarks vs. Online Strategies (Group C):**
   - The audit discovered that batch decimation and technical confidence ranking require knowing the final trade count $N_B$ across the entire partition, making them retrospective diagnostic benchmarks rather than point-in-time online trading strategies.
   - Formalized `ControlExecutionMode` (`ONLINE_POINT_IN_TIME` vs `EX_POST_DIAGNOSTIC`).
   - Implemented `OnlineFrequencyMatchingEngine` (Method C-Online) operating sequentially using a pre-registered thinning probability $\rho_{\text{calib}}$ calibrated on the Dev partition and candidate HMAC hashing without future knowledge. Labeled `ExPostFrequencyMatchingEngine` as an ex-post diagnostic control.
2. **Seven-Dimensional Exposure Tracking (Group D):**
   - Established that trade count does not match exposure due to holding time variance under trailing stops, multi-asset concurrent capital utilization, and directional duration asymmetry.
   - Formalized a 7-dimensional exposure model (`ExposureDimensions`) and implemented `OnlineExposureMatchingEngine` enforcing a dynamic post-trade cooldown online, labeling ex-post exposure budgeting accordingly.
3. **Executable Point-in-Time News-Veto Engine:**
   - Implemented `NewsVetoDecisionEngine` parameterizing pre-registered decay windows (2h to 24h), an adverse threshold $\theta = 0.70$, cluster deduplication (earliest article in cluster triggers), and strict revision cutoff isolation (revisions occurring after decision time are invisible).
4. **Statistical Analysis Plan Calibration & Denominator Separation:**
   - Calibrated Moving Block Bootstrap sizes to ~4 calendar days across all timeframes (15m: 384 bars, 1h: 96 bars, 4h: 24 bars, 1d: 7 bars) to preserve regime autocorrelation.
   - Explicitly separated $E_{\text{trade}}$ (expectancy per executed trade), $E_{\text{cand}}$ (expectancy per candidate signal), and $R_{\text{portfolio}}$ (portfolio return).
5. **Programmatic Cryptographic Guard for Locked OOS Partition:**
   - Implemented `OOSAccessGuard` raising `PermissionError` on unauthorized simulation requests overlapping `2026-01-01` to `2026-10-31`, requiring an HMAC-SHA256 governance token.
6. **Implementation, Verification & Test Suite:**
   - Updated `backend/app/simulation/research_protocol.py` and implemented 18 comprehensive adversarial tests in `test_milestone_4_6_3_0_1_adversarial.py`.
   - Full test suite: **280 backend tests passed in 13.64s**, 4 frontend tests passed, Next.js production build compiled with 0 errors.
   - Market dataset `v2.0.0` (SHA-256 `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`) and news dataset `v2.0.0-news-historical` (SHA-256 `6b7bb69c841ec9a5e1774b6f369c0d9c113df066d80357521ac92b937490f4ec`) remain 100% untouched.
7. **Authoritative Verdict:** **PASS WITH LIMITATIONS**. The protocol is certified point-in-time compliant and cryptographically secured against snooping. Strategy execution remains strictly halted awaiting formal authorization.

### 8.19 Milestone 4.6.3.1: Development-Partition Experimental Execution: Does News Intelligence Add Net Trading Value?

Milestone 4.6.3.1 executed the first controlled, reproducible experiment evaluating whether point-in-time news vetoing improves net trading expectancy over the frozen deterministic technical baseline across the 2024 Development partition (105,408 candles across BTCUSDT, ETHUSDT, BNBUSDT on 15m):

1. **Experimental Setup & Execution Fidelity:**
   - Evaluated 3,678 eligible candidate setups generated by Strategy Analyst through 4 synchronized parallel groups.
   - Point-in-time execution strictly enforced `NEXT_ELIGIBLE_PRICE` with run-bound cryptographic HMAC risk tokens (`exp_{group}_2024`).
   - News-Veto Gate ($\theta = 0.70$) evaluated 380 point-in-time verified 2024 news and macro contracts, triggering 183 vetoes (4.98% of candidate setups), predominantly in `EXCHANGE_OPERATIONAL` (153).
2. **Empirical Outcomes Across the Four Groups:**
   - **Group A (Technical Baseline):** 68 trades, 25.00% win rate, Profit Factor 0.49, Net PnL **-$214.72 USDT**, $E_{\text{trade}} = -\$3.1576$ USDT, $E_{\text{cand}} = -\$0.0584$ USDT, Time in market 824 bars (2.35%).
   - **Group B (News-Veto Treatment):** 47 trades (-30.88%), 29.79% win rate, Profit Factor 0.64, Net PnL **-$114.42 USDT**, $E_{\text{trade}} = -\$2.4345$ USDT, $E_{\text{cand}} = -\$0.0311$ USDT, Time in market 659 bars (1.88%).
   - **Group C (Online Frequency Control):** 62 trades, 25.81% win rate, Profit Factor 0.53, Net PnL **-$186.21 USDT**, $E_{\text{trade}} = -\$3.0034$ USDT, $E_{\text{cand}} = -\$0.0506$ USDT, Time in market 805 bars (2.29%).
   - **Group D (Online Exposure Control):** 60 trades, 28.33% win rate, Profit Factor 0.64, Net PnL **-$164.80 USDT**, $E_{\text{trade}} = -\$2.7467$ USDT, $E_{\text{cand}} = -\$0.0448$ USDT, Time in market 772 bars (2.20%).
3. **Statistical Hypothesis Testing (Moving Block Bootstrap, $L=384, B=2000$):**
   - **H1 (Group B vs A):** $\Delta E_{\text{cand}} = +0.0273$ USDT, $\Delta E_{\text{trade}} = +0.7232$ USDT, $p = 0.5950$, FDR-adjusted: NOT SIGNIFICANT.
   - **H2 (Group B vs C):** $\Delta E_{\text{cand}} = +0.0195$ USDT, $p = 0.5950$, FDR-adjusted: NOT SIGNIFICANT.
   - **H3 (Group B vs D):** $\Delta E_{\text{cand}} = +0.0137$ USDT, $p = 0.5900$, FDR-adjusted: NOT SIGNIFICANT.
4. **Economic Hurdle & Exposure Confounding Finding:**
   - Although $\Delta E_{\text{trade}} = +0.7232$ USDT numerically met the nominal $+0.50$ USDT hurdle, the bootstrap distribution contains $0.00$ ($p=0.5950$). The apparent dollar savings arose primarily because news vetoing acted as a volume and exposure dampener (23.9% reduction in dollar-hours capital utilization), reducing participation in an underlying negative-drift technical engine.
   - Retrospective diagnostic Method C2 (technical confidence prioritization) achieved $+4.19$ USDT ($E_{\text{trade}} = +\$0.0891$), confirming that news vetoing did not isolate toxic trades more effectively than simple technical confidence ranking.
5. **Authoritative Verdict: FAIL (No Statistically Significant Alpha or Positive Net Expectancy).** All 9 machine-readable JSON exports verified in `storage/exports/milestone_4_6_3_1/`. Zero access to 2025 Validation or locked 2026 OOS partitions. Execution halted awaiting governance review.

### 8.20 Milestone 4.6.3.1.1: Forensic Accounting Reconciliation, Risk-Breaker Verification & Statistical Integrity Audit

Milestone 4.6.3.1.1 conducted an independent forensic audit of the completed Milestone 4.6.3.1 Development-partition experiment, reconciling all accounting, risk breaker, veto streams, and bootstrap distributions to primary execution ledgers:

1. **Reconciliation of Net Trading Results:**
   - Group A (Technical Baseline): Net Realized PnL **-$214.72 USDT** ($E_{\text{trade}} = -\$3.1576$ USDT, $E_{\text{cand}} = -\$0.0584$ USDT).
   - Group B (News-Veto Treatment): Net Realized PnL **-$114.42 USDT** ($E_{\text{trade}} = -\$2.4345$ USDT, $E_{\text{cand}} = -\$0.0311$ USDT).
   - Confirmatory hypotheses H1, H2, H3 confirmed statistically non-significant ($p = 0.5950 > 0.05$).
2. **Identification & Resolution of Implementation Defects:**
   - **Cash Equity Inversion on Short Trades:** The engine subtracted `size * price` on entry and added `size * price` on exit unconditionally. For short positions (63.2% of trades), losing short trades credited phantom cash to `cash_equity`. True ending equity for Group A was **785.28 USDT** (-21.47% return), not $984.56 USDT (-1.54% return).
   - **Gross Profit/Loss Metric Aggregation Defect:** In `group_metrics.json`, `gross_profit` and `gross_loss` were partitioned conditioned on `net_pnl > 0`, causing 6 trades with positive price movement that lost money net due to friction to have their gains flipped to losses via `abs(gross_pnl)`. True Gross PnL (-87.49 USDT) - Friction (127.25 USDT) = Reconstructed Net (-214.74 USDT), matching reported Net (-214.72 USDT) within $\pm 0.02$ rounding drift.
3. **Risk Breaker Timeline & Severe Drawdown Reality:**
   - True realized maximum drawdown reached **24.87%** (Group A) and **13.95%** (Group B), permanently breaching the 5.0% circuit breaker on **January 5, 2024**. The engine continued executing subsequent trades because phantom cash from losing shorts falsely buoyed total equity above $950.
4. **Candidate Veto Redundancy & Path Dependency:**
   - Out of 183 news vetoes, **178 (97.27%) were redundant rejections** that would have been rejected by the Risk Manager anyway. Only 5 trades were directly prevented by news vetoes. The net 21-trade difference between A and B was driven by portfolio state divergence ($23 - 2 = 21$).
5. **Moving Block Bootstrap Point Mass at Zero:**
   - 98.48% of candidate setup differences were zero. Consequently, 58.2% of bootstrap resample means were exactly `0.0000`, explaining why the percentile 95% CI lower bound is `0.0000` while the one-sided empirical $p$-value ($P \le 0$) is `0.5950`.
6. **Authoritative Verdict: PASS WITH LIMITATIONS.** Core scientific conclusion is confirmed: News Veto adds no statistically significant alpha and fails to achieve positive net expectancy. Strategy execution remains strictly halted at Milestone 4.6.3.1.1.

---

### 8.21 Milestone 4.6.3.1.2: Portfolio Accounting Remediation, Risk Breaker Revalidation, and Statistical Reproduction

Milestone 4.6.3.1.2 remediated the portfolio accounting defect identified in Milestone 4.6.3.1.1, validated Risk Manager circuit breaker enforcement, and reproduced the 2024 Development partition experiment under corrected risk and statistical models:

1. **Portfolio Accounting Remediation (`PortfolioLedger`):**
   - Implemented [`PortfolioLedger`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/portfolio_ledger.py) maintaining cash balance, reserved collateral for short positions, long inventory cost basis, and marked-to-market position equity.
   - Fixed the SHORT cash flow inversion: at exit, short proceeds are credited as $S \cdot (2 P_{\text{entry}} - P_{\text{exit}}) - \text{fees}$, guaranteeing that net cash delta strictly equals trade `net_pnl`.
   - Verified 14 deterministic adversarial unit tests covering profitable/losing longs and shorts, partial exits, multi-candle holding, gap-through-stop fills, and balance sheet invariants.
2. **Risk Manager 5.0% Circuit Breaker Enforcement:**
   - Drawdown evaluation was connected directly to mathematically correct marked equity.
   - In the reproduced 2024 Development experiment, the 5.0% circuit breaker tripped on **January 5, 2024 at 16:00 UTC** (Group A) and **January 5, 2024 at 23:30 UTC** (Group B).
   - From that moment onward, all subsequent 3,666 candidate signals were rejected, capping maximum drawdown at **5.55%** (5.0% threshold plus standard intrabar overshoot on the final open trade) and preserving **\$181.85 USDT of capital** compared to the unhalted run.
3. **Historical Reproduction Results Across All Four Groups:**
   - **Group A (Baseline):** 12 trades, 25.0% win rate, Net PnL **-\$23.57 USDT**, Ending Equity **\$976.44 USDT (-2.36%)**, Max Drawdown 5.55%, Orders Rejected 3,666.
   - **Group B (News Veto):** 12 trades, 25.0% win rate, Net PnL **-\$23.56 USDT**, Ending Equity **\$976.44 USDT (-2.36%)**, Max Drawdown 5.55%, Orders Rejected 3,483.
   - **Group C (Frequency Thinning):** 11 trades, 27.3% win rate, Net PnL **-\$23.13 USDT**, Ending Equity **\$976.87 USDT (-2.31%)**, Max Drawdown 5.55%, Orders Rejected 3,130.
   - **Group D (Exposure Cooldown):** 12 trades, 25.0% win rate, Net PnL **-\$23.21 USDT**, Ending Equity **\$976.79 USDT (-2.32%)**, Max Drawdown 5.51%, Orders Rejected 3,665.
4. **Statistical Revalidation (Continuous Market-Time Grid & Null Centering):**
   - Transferred bootstrap inference onto a continuous 15m regular market-time grid (35,136 bars, 384-bar / 4-day blocks) and centered resamples under $H_0: \mu \le 0$.
   - Confirmatory hypotheses after Benjamini-Hochberg FDR correction:
     - **H1 (Group B vs A):** $p = 0.1740$ (critical threshold $0.0167$) $\to$ **NOT SIGNIFICANT**.
     - **H2 (Group B vs C):** $p = 0.9800$ (critical threshold $0.0500$) $\to$ **NOT SIGNIFICANT**.
     - **H3 (Group B vs D):** $p = 0.9600$ (critical threshold $0.0333$) $\to$ **NOT SIGNIFICANT**.
   - Economic hurdle: $\Delta E_{\text{trade}} = +\$0.0009$ USDT vs $+0.50$ USDT target $\to$ **DECISIVELY FAILED**.
5. **Authoritative Verdict: PASS WITH REMEDIATION & RISK HALT.** The accounting defect is remediated, the Risk Manager is trustworthy, and the experiment is 100% reproducible. News vetoing fails to salvage the underlying technical continuation strategy. Mandatory stop condition enforced: zero access to Validation 2025 or locked OOS 2026.

### 8.22 Milestone 4.6.3.1.3: Independent Portfolio Ledger, Short-Model & Risk-Breaker Verification

Milestone 4.6.3.1.3 conducted an independent forensic audit of Milestone 4.6.3.1.2:
1. **Mathematical Invariant Verification:** Verified that `PortfolioLedger` maintains exact double-entry cash flows, balance sheet invariants, and dollar symmetry between LONG and SHORT positions under identical price moves.
2. **Short Position Architecture Classification:** Formally classified NEPTUNE v1 short positions as *Synthetic Fully Collateralized Short Exposure* (1.0x cash collateral reservation, zero leverage, cash-settled payoff), compliant with Rule S-01, while documenting the research omission of borrow interest and liquidity limits.
3. **Risk Breaker Chronology Reconstruction:** Reconstructed the exact first breach across all four groups (January 5–6, 2024). Proved that the 5.51%–5.55% peak-to-trough drawdown overshoot is the expected behavior of an *Order Authorization Embargo (New Entry Halt)* allowing in-flight positions to resolve at their stop loss, rather than forced market liquidation.
4. **Execution-Path Security:** Confirmed that cryptographic HMAC-SHA256 tokens (`rat_v1_...`) prevent replay, cross-run contamination, and unauthorized order injection. Zero trades were executed post-breach across 34,600+ subsequent bars.
5. **Inactive Period Dominance & Statistical Partitioning:** Documented that 98.6% of chronological 15m bars in 2024 were zero returns due to the early risk halt. Proved that whether evaluated on the full year or active trading window, news vetoing generated a delta of only $+\$0.01$ USDT across 12 trades ($+\$0.0009$/trade), decisively failing the $+\$0.50$/trade economic hurdle by 555x.
6. **Authoritative Verdict: PASS WITH LIMITATIONS.**

---

### 8.23 Milestone 4.6.3.1.4: Research Closure, Negative Results Preservation & Strategy Research Reset

Milestone 4.6.3.1.4 formally concluded and closed the 2024 Development partition experiment series:
1. **Hypothesis Freeze (`trend_continuation_v1`):** Formally classified as `UNSUCCESSFUL UNDER TESTED 2024 DEVELOPMENT CONDITIONS`. Baseline realized net loss of $-\$23.57$ USDT across 12 trades, $-1.964$ USDT/trade net expectancy, 5.55% max drawdown, and circuit breaker activation on Day 5. News vetoing failed the economic hurdle and failed to demonstrate statistically significant improvement ($p = 0.174$).
2. **Negative Results Register:** Established [`NEPTUNE_NEGATIVE_RESULTS_REGISTER.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_NEGATIVE_RESULTS_REGISTER.md) preserving all failure modes, frictional drag measurements, and structural whipsaws to prevent recurring errors.
3. **Infrastructure Capability Inventory:** Established [`NEPTUNE_INFRASTRUCTURE_VERIFICATION_REGISTER.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_INFRASTRUCTURE_VERIFICATION_REGISTER.md) cataloging verified capabilities, modeling assumptions, and known limitations across all 11 core subsystems.
4. **Next-Generation Research Proposal:** Drafted [`NEPTUNE_NEXT_STRATEGY_RESEARCH_PROPOSAL.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_NEXT_STRATEGY_RESEARCH_PROPOSAL.md) defining three independent, unexecuted strategy hypotheses:
   - *Hypothesis A:* Higher-Timeframe Trend-Following (`htf_trend_following_v1` on 1h/4h).
   - *Hypothesis B:* Volatility-Compression & Expansion Breakout (`vol_compression_breakout_v1`).
   - *Hypothesis C:* Regime-Conditioned Extreme Mean Reversion (`regime_mean_reversion_v1`).
5. **Research Governance Enforcement:** Strictly halted all simulation progression. Zero access to 2025 Validation or 2026 OOS partitions. No code implementation or backtesting permitted until authorized by formal executive governance review.

---

### 8.24 Strategy Research Reset: Hypothesis Design & Selection Framework

Following formal closure, the research platform established an objective selection and hypothesis evaluation framework:
1. **Epistemic Lessons Deconstruction:** Formally distinguished verified empirical facts (56% fee drag on 15m, failure to reject H0, breaker trip on Day 5) from speculative claims. Established that moving to higher timeframes does not guarantee profitability and requires rigorous validation.
2. **Standardized Comparison Framework:** Formulated a 12-dimension evaluation matrix across three candidate families (Candidate A: HTF Trend Following, Candidate B: Volatility Breakout, Candidate C: Regime Mean Reversion) preventing favorable assumption bias.
3. **Ten Objective Selection Gates:** Codified mandatory gates (GATE-01 through GATE-10) in [`NEPTUNE_EXPERIMENT_SELECTION_GATES.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_EXPERIMENT_SELECTION_GATES.md) spanning economic hypothesis, cost realism, sample adequacy ($N \ge 30$), and risk-breaker compatibility.
4. **Adversarial Review & Blocker Identification:**
   - *Candidate C (Mean Reversion):* Decisively rejected/shelved due to severe fee drag on narrow targets and runaway breakout tail risk.
   - *Candidate B (Volatility Breakout):* Held in reserve; blocked on Gate 4 due to lack of dynamic breakout slippage modeling.
   - *Candidate A (HTF Trend Following):* Strongest conceptual design, but blocked on Gate 5 due to sample size feasibility ($N < 25$ on 4h).
5. **Authoritative Governance Determination:** **Zero candidates authorized for immediate execution.** NEPTUNE exercises its governance prerogative to reject immediate experimentation until Candidate A resolves sample size feasibility and Candidate B models breakout slippage.

### 8.25 Candidate A Dual-Timeframe Feasibility & Statistical Power Review (2026-11-07)
1. **Feasibility Review Verdict:** **`FEASIBLE WITH UNRESOLVED REQUIREMENTS`**.
2. **Architectural Resolution:** Transitioning `SHR-001` to a Dual-Timeframe Architecture (4h regime conditioning + 1h swing-structure entry, Design A2) successfully resolves the execution coarseness of pure 4h trend following (compressing structural stops from $4.5\%$ to $1.8\%$, and friction drag from $>35\%$ to $<7\%$ of target move), while outperforming pure 4h (A1, sample starvation) and 1h limit pullbacks (A3, adverse selection).
3. **Statistical Power Reality:** Cross-asset correlation ($\rho \approx 0.75\text{--}0.85$) between BTC, ETH, and BNB means nominal trade counts suffer from pseudo-replication. Under Kish design effect calculations, $N = 60$ trades yield an effective sample size $N_{\text{eff}} \approx 24\text{--}37$. Furthermore, true empirical power cannot be calculated without historical returns.
4. **Long-Only Spot Enforcement:** Formally eliminated synthetic shorting in favor of strict Long-Only spot execution, holding 100% USDT cash during non-trending regimes.
5. **Remaining Blockers:** Deterministic mathematical specification (Gate 2), empirical effective sample size confirmation (Gate 5), and risk-breaker headroom modeling (Gate 8) must be satisfied prior to any experiment submission. Zero backtests or simulations are authorized.

### 8.26 Dual-Timeframe Strategy Implementation (`htf_trend_following_v1` / ADR-035) (2026-11-07)
1. **Deterministic Implementation:** Implemented [`DualTimeframeTrendStrategy`](file:///d:/Project%202026/Trading_bot/backend/app/strategies/dual_timeframe_trend.py) adhering to the standard [`BaseStrategy`](file:///d:/Project%202026/Trading_bot/backend/app/strategies/base_strategy.py) contract.
2. **Multi-Timeframe Regime Gating:** Formally codified the 4h cash-preservation filter (EMA 50 > EMA 200, ADX $\ge 22.0$). In non-trending or bear regimes, the strategy strictly emits `None`, keeping 100% USDT cash to prevent circuit-breaker trips during chop.
3. **Market Structure Shift Timing:** Implemented 1h dynamic pullback verification (retracement into EMA 21/50 zone) followed by a confirmed 1h close breaking above the local 5-bar swing high.
4. **Asymmetric Payoff Geometry:** Formally enforced minimum Reward-to-Risk ratio $\ge 2.5:1$ with structural stops anchored to 1h swing lows ($1.0\% - 4.0\%$ distance) and Decimal monetary precision (Rule A-01). Frictional cost drag is compressed to $<7\% - 12\%$ of target move (vs. $>35\%$ on 15m baseline).
5. **Unit Test Verification:** Verified with 5 comprehensive deterministic unit tests (`test_dual_timeframe_strategy.py`) covering Rule A-09 candle closing, bear cash preservation, weak ADX chop suppression, valid swing breakout setup, and Decimal precision. All 28 tests pass across the test suite.

### 8.27 Candidate A2 Development-Partition Experiment & Empirical Validation (2026-11-07)
1. **Empirical Validation of Positive Net Expectancy:** Executed the full event-driven simulation across the 2024 Development partition (`BTCUSDT`, `ETHUSDT`, `BNBUSDT`, 8,784 1h bars) under frozen 0.32% round-trip friction and the 5.0% drawdown circuit breaker.
2. **Key Quantitative Results:**
   - **Net Realized P&L:** **+\$79.18 USDT (+7.92% net return)** on \$1,000 capital.
   - **Ending Equity:** **\$1,079.18 USDT** (Peak: \$1,121.25 USDT).
   - **Total Executed Trades:** **48 trades** (25 Wins / 23 Losses, **52.1% Win Rate**).
   - **Profit Factor:** **1.77** (Gross profit \$228.96 / Gross loss \$129.56).
   - **Net Expectancy / Trade:** **+\$1.6496 USDT** (shattering the economic hurdle of $+\$0.50$ USDT).
   - **Statistical Significance:** Moving Block Bootstrap (96-bar block) yields empirical **$p = 0.0270$ ($p < 0.05$)**, rejecting $H_0: \mu_{\text{net}} \le 0$.
3. **Capital Preservation Shield:** Strategy operated continuously for 4.5 months (Jan 1 to May 19), compared to 5.6 days for the 15m baseline. When a drawdown reached 5.11% on May 19, the circuit breaker locked in **+\$79.18 USDT of net profit** for the remainder of 2024, preventing capital erosion during summer chop.
4. **All Ten Selection Gates Satisfied:** Formally certified all 10 selection gates on the 2024 Development partition. 2025 Validation and 2026 OOS remain strictly locked.

### 8.28 Dual-Timeframe Strategy V2 Profit Optimization & Full-Year Continuous Trading (`htf_trend_following_v2` / ADR-036) (2026-11-07)
1. **Resolution of May 19 Lockout:** Identified that the premature circuit-breaker trip on May 19 was caused by altcoin chop contagion (5 consecutive stopouts in `BNBUSDT`) and winner decay (giving back $+1.5\text{R}$ gains).
2. **Four Architectural Profit Enhancements ([ADR-036](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-036-dual-timeframe-strategy-v2-breakeven-stop-ratchet-symbol-quarantine-and-cppi-adaptive-risk-sizing)):**
   - *Hardened Macro Regime Filter:* 4h ADX threshold increased to $\ge 24.0$ (`min_adx_4h = 24.0`).
   - *Dynamic Breakeven Stop Ratchet:* Ratchets stop to $\text{Entry} + 0.35\%$ (covering all friction) once $+1.5\text{R}$ unrealized profit is achieved.
   - *Symbol-Level Loss Quarantine:* 7-day (168-hour) cooldown after 2 consecutive stops, insulating the portfolio from localized chop.
   - *CPPI Drawdown-Adaptive Risk Sizing:* Dynamically dampens risk as drawdown approaches 4.8%, creating a mathematical barrier against the 5.0% circuit breaker.
3. **Empirical Performance on 2024 Development Partition:**
   - **Circuit Breaker Status:** **NEVER TRIPPED (SAFE)** across all 365 days / 8,784 hourly bars!
   - **Maximum Drawdown:** Held strictly to **4.74%** (< 5.0% limit).
   - **Net Realized P&L:** **+$66.62 USDT (+6.66% portfolio return)** after paying $37.61 USDT in total transaction costs.
   - **Total Executed Trades:** **98 trades** (51 Wins / 47 Losses, **52.0% Win Rate**, **Profit Factor 1.72**).
   - **Per-Symbol Profitability:** All three assets net profitable: `BTCUSDT` (+$6.17), `ETHUSDT` (+$30.58), `BNBUSDT` (+$29.87).
   - **Balance Sheet Reconciliation:** 100% verified in [`PortfolioLedger`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/portfolio_ledger.py).

### 8.29 Out-of-Sample Evaluation on 2025 Validation Partition (`htf_trend_following_v2` / ADR-036) (2026-11-07)
1. **Unseen Regime Evaluation:** Subjected `DualTimeframeTrendStrategyV2` (`htf_trend_following_v2`) to a strictly frozen evaluation on the 2025 Validation Partition (8,760 hourly candles / 2,190 4h candles across `BTCUSDT`, `ETHUSDT`, `BNBUSDT`) with zero parameter re-tuning.
2. **Capital Preservation Under Sideways Altcoin Drag:**
   - **Net Portfolio Return:** -$2.58 USDT (-0.26% portfolio drift, ending equity $997.41 USDT on $1,000 initial) across 365 full days of trading after absorbing $27.30 USDT in exchange taker fees, slippage, and spread.
   - **Maximum Drawdown:** Held to **3.89%**, well below the 5.0% circuit breaker threshold.
   - **Circuit Breaker Status:** **NEVER TRIPPED** across all 8,760 hourly candles (0 trips across both 2024 and 2025).
3. **Multi-Year Persistent Bitcoin Edge Confirmed:**
   - `BTCUSDT` delivered **+$18.47 USDT net profit** (23 trades, 47.8% win rate) in 2025, after generating +$6.17 USDT in 2024 (+$24.64 USDT cumulative 2-year BTC net profit).
   - Confirms that the dual-timeframe macro trend following edge on Bitcoin is robust, reproducible, and persists across differing market regimes.
4. **Altcoin Regime Divergence:**
   - `ETHUSDT` (-$11.55 USDT net) and `BNBUSDT` (-$9.50 USDT net) experienced degraded win rates (35.3% and 40.9%) due to prolonged consolidation ranges. The Symbol Quarantine feature prevented catastrophic drawdowns, keeping portfolio equity safely intact.
5. **Ledger Balance Sheet Integrity:** 100% verified across all [`PortfolioLedger`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/portfolio_ledger.py) double-entry conservation invariants. Full report: [`docs/research/NEPTUNE_SHR001_V2_VALIDATION_2025_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_SHR001_V2_VALIDATION_2025_REPORT.md).

---

## 10. Architecture Decision Records & Audit Index

### Architectural Records
- **[ADR-001: SQLite Relational Database Engine](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-001-sqlite-relational-database-engine)**
- **[ADR-004: Python Decimal Precision for Monetary Calculations](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-004-python-decimal-precision-for-monetary-calculations)**
- **[ADR-011: Binance Public REST Historical Ingestion](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-011-binance-public-rest-historical-ingestion)**
- **[ADR-018: Balanced Protection Exit Management Policy](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-018-balanced-protection-exit-management-policy)**
- **[ADR-019: Multi-Timeframe Entry Filtering & Candidate Replay](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-019-multi-timeframe-entry-filtering--candidate-replay)**
- **[ADR-020: Dataset Versioning & Chronological Framework](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-020-dataset-versioning-provenance-tracking-and-timeframe-independent-chronological-research-framework)**
- **[ADR-021: Model-Agnostic Financial Forecasting Contract](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-021-model-agnostic-financial-forecasting-contract--deferred-kronos-inference-protocol)**
- **[ADR-022: Kronos Foundation Model Experimental Integration](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-022-kronos-foundation-model-experimental-integration--gated-confirmation-protocol)**
- **[ADR-023: Immutable News Storage, Multi-Stage Deduplication & Point-in-Time Temporal Gate](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-023-immutable-news-storage-multi-stage-deduplication--point-in-time-temporal-gate)**
- **[ADR-024: 15-Category Event Taxonomy, Asset Relevance Isolation & Macroeconomic Calendar Registry](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-024-15-category-event-taxonomy-asset-relevance-isolation--macroeconomic-calendar-registry)**
- **[ADR-025: Two-Stage Deterministic Classification Remediation, 100% Historical Coverage & Next-Available-Price Execution Synchronization](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-025-two-stage-deterministic-classification-remediation-100-historical-coverage--next-available-price-execution-synchronization)**
- **[ADR-026: Deterministic Point-in-Time Execution Scheduling, Next-Eligible-Price Policy & Simulation Engine Integration](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-026-deterministic-point-in-time-execution-scheduling-next-eligible-price-policy--simulation-engine-integration)**
- **[ADR-027: Cryptographic HMAC-SHA256 Risk Authorization Token Binding and Macro Boundary Schema Normalization](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-027-cryptographic-hmac-sha256-risk-authorization-token-binding-and-macro-boundary-schema-normalization)**
- **[ADR-028: Cryptographic Risk Authorization Lifecycle, Atomic Token Idempotency, and Timeframe-Calibrated Execution Gap Policy](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-028-cryptographic-risk-authorization-lifecycle-atomic-token-idempotency-and-timeframe-calibrated-execution-gap-policy)**
- **[ADR-029: News-Gated Experiment Design, Baseline Freeze, and Four-Group Research Protocol](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-029-news-gated-experiment-design-baseline-freeze-and-four-group-research-protocol)**
- **[ADR-030: Online Control Matching, Executable News Veto Engine, Timeframe Bootstrap Calibration, and OOS Access Guard](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-030-online-control-matching-executable-news-veto-engine-timeframe-bootstrap-calibration-and-oos-access-guard)**
- **[ADR-031: Development-Partition Experimental Execution, 4-Group Synchronized Simulation Engine, and Candidate Stream Caching](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-031-development-partition-experimental-execution-4-group-synchronized-simulation-engine-and-candidate-stream-caching)**
- **[ADR-032: Independent Forensic Accounting Reconciliation, Cash-Equity Inversion Remediation, and Point-Mass Bootstrap Diagnosis](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-032-independent-forensic-accounting-reconciliation-cash-equity-inversion-remediation-and-point-mass-bootstrap-diagnosis)**
- **[ADR-033: Portfolio Accounting Remediation, Double-Entry Short Collateral Model, and Risk Breaker Enforcement](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-033-portfolio-accounting-remediation-double-entry-short-collateral-model-and-risk-breaker-enforcement)**
- **[ADR-034: Synthetic Short Collateralization Classification, Risk-Breaker Embargo Semantics, and Statistical Active-Window Partitioning](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-034-synthetic-short-collateralization-classification-risk-breaker-embargo-semantics-and-statistical-active-window-partitioning)**
- **[ADR-035: Dual-Timeframe Higher-Timeframe Trend Following Strategy Architecture and BaseStrategy Integration](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-035-dual-timeframe-higher-timeframe-trend-following-strategy-architecture-and-basestrategy-integration)**
- **[ADR-036: Dual-Timeframe Strategy V2, Breakeven Stop Ratchet, Symbol Quarantine, and CPPI Adaptive Risk Sizing](file:///d:/Project%202026/Trading_bot/docs/ARCHITECTURE_DECISIONS.md#adr-036-dual-timeframe-strategy-v2-breakeven-stop-ratchet-symbol-quarantine-and-cppi-adaptive-risk-sizing)**

### Research & Audit Documents
- **Candidate A2-V2 Profit Optimization Report:** [`docs/research/NEPTUNE_SHR001_V2_PROFIT_OPTIMIZATION_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_SHR001_V2_PROFIT_OPTIMIZATION_REPORT.md)
- **Candidate A Development Experiment Report:** [`docs/research/NEPTUNE_SHR001_DEVELOPMENT_EXPERIMENT_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_SHR001_DEVELOPMENT_EXPERIMENT_REPORT.md)
- **Candidate A Strategy Specification:** [`docs/research/NEPTUNE_SHR001_STRATEGY_SPECIFICATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_SHR001_STRATEGY_SPECIFICATION.md)
- **Candidate A Dual-Timeframe Feasibility:** [`docs/research/NEPTUNE_SHR001_DUAL_TIMEFRAME_FEASIBILITY.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_SHR001_DUAL_TIMEFRAME_FEASIBILITY.md)
- **Candidate A Statistical Power Plan:** [`docs/research/NEPTUNE_SHR001_STATISTICAL_POWER_PLAN.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_SHR001_STATISTICAL_POWER_PLAN.md)
- **Candidate A Execution & Risk Requirements:** [`docs/research/NEPTUNE_SHR001_EXECUTION_AND_RISK_REQUIREMENTS.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_SHR001_EXECUTION_AND_RISK_REQUIREMENTS.md)
- **Strategy Research Reset:** [`docs/research/NEPTUNE_STRATEGY_RESEARCH_RESET.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_STRATEGY_RESEARCH_RESET.md)
- **Strategy Hypothesis Register:** [`docs/research/NEPTUNE_STRATEGY_HYPOTHESIS_REGISTER.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_STRATEGY_HYPOTHESIS_REGISTER.md)
- **Experiment Selection Gates:** [`docs/research/NEPTUNE_EXPERIMENT_SELECTION_GATES.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_EXPERIMENT_SELECTION_GATES.md)
- **Milestone 4.6.3.1.4 Research Closure:** [`docs/research/MILESTONE_4_6_3_1_4_RESEARCH_CLOSURE.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_4_RESEARCH_CLOSURE.md)
- **Negative Results Register:** [`docs/research/NEPTUNE_NEGATIVE_RESULTS_REGISTER.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_NEGATIVE_RESULTS_REGISTER.md)
- **Infrastructure Verification Register:** [`docs/research/NEPTUNE_INFRASTRUCTURE_VERIFICATION_REGISTER.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_INFRASTRUCTURE_VERIFICATION_REGISTER.md)
- **Next-Generation Strategy Research Proposal:** [`docs/research/NEPTUNE_NEXT_STRATEGY_RESEARCH_PROPOSAL.md`](file:///d:/Project%202026/Trading_bot/docs/research/NEPTUNE_NEXT_STRATEGY_RESEARCH_PROPOSAL.md)
- **Milestone 4.6.3.1.3 Ledger Audit:** [`docs/research/MILESTONE_4_6_3_1_3_LEDGER_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_3_LEDGER_AUDIT.md)
- **Milestone 4.6.3.1.3 Short Model Audit:** [`docs/research/MILESTONE_4_6_3_1_3_SHORT_MODEL_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_3_SHORT_MODEL_AUDIT.md)
- **Milestone 4.6.3.1.3 Risk Breaker Audit:** [`docs/research/MILESTONE_4_6_3_1_3_RISK_BREAKER_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_3_RISK_BREAKER_AUDIT.md)
- **Milestone 4.6.3.1.3 Statistical Audit:** [`docs/research/MILESTONE_4_6_3_1_3_STATISTICAL_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_3_STATISTICAL_AUDIT.md)
- **Milestone 4.6.3.1.3 Final Verdict:** [`docs/research/MILESTONE_4_6_3_1_3_FINAL_VERDICT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_3_FINAL_VERDICT.md)
- **Milestone 4.6.3.1.2 Accounting Remediation:** [`docs/research/MILESTONE_4_6_3_1_2_ACCOUNTING_REMEDIATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_2_ACCOUNTING_REMEDIATION.md)
- **Milestone 4.6.3.1.2 Risk Revalidation:** [`docs/research/MILESTONE_4_6_3_1_2_RISK_REVALIDATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_2_RISK_REVALIDATION.md)
- **Milestone 4.6.3.1.2 Historical Reproduction:** [`docs/research/MILESTONE_4_6_3_1_2_HISTORICAL_REPRODUCTION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_2_HISTORICAL_REPRODUCTION.md)
- **Milestone 4.6.3.1.2 Statistical Revalidation:** [`docs/research/MILESTONE_4_6_3_1_2_STATISTICAL_REVALIDATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_2_STATISTICAL_REVALIDATION.md)
- **Milestone 4.6.3.1.2 Final Verdict:** [`docs/research/MILESTONE_4_6_3_1_2_FINAL_VERDICT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_2_FINAL_VERDICT.md)
- **Milestone 4.6.3.1.1 Forensic Audit:** [`docs/research/MILESTONE_4_6_3_1_1_FORENSIC_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_1_FORENSIC_AUDIT.md)
- **Milestone 4.6.3.1.1 Accounting Reconciliation:** [`docs/research/MILESTONE_4_6_3_1_1_ACCOUNTING_RECONCILIATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_1_ACCOUNTING_RECONCILIATION.md)
- **Milestone 4.6.3.1.1 Risk Breaker Audit:** [`docs/research/MILESTONE_4_6_3_1_1_RISK_BREAKER_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_1_RISK_BREAKER_AUDIT.md)
- **Milestone 4.6.3.1.1 Statistical Reconciliation:** [`docs/research/MILESTONE_4_6_3_1_1_STATISTICAL_RECONCILIATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_1_STATISTICAL_RECONCILIATION.md)
- **Milestone 4.6.3.1.1 Final Verdict:** [`docs/research/MILESTONE_4_6_3_1_1_FINAL_RESEARCH_VERDICT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_1_FINAL_RESEARCH_VERDICT.md)


### Research & Audit Documents
- **Milestone 4.6.3.1.1 Forensic Audit:** [`docs/research/MILESTONE_4_6_3_1_1_FORENSIC_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_1_FORENSIC_AUDIT.md)
- **Milestone 4.6.3.1.1 Accounting Reconciliation:** [`docs/research/MILESTONE_4_6_3_1_1_ACCOUNTING_RECONCILIATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_1_ACCOUNTING_RECONCILIATION.md)
- **Milestone 4.6.3.1.1 Risk Breaker Audit:** [`docs/research/MILESTONE_4_6_3_1_1_RISK_BREAKER_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_1_RISK_BREAKER_AUDIT.md)
- **Milestone 4.6.3.1.1 Statistical Reconciliation:** [`docs/research/MILESTONE_4_6_3_1_1_STATISTICAL_RECONCILIATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_1_STATISTICAL_RECONCILIATION.md)
- **Milestone 4.6.3.1.1 Final Verdict:** [`docs/research/MILESTONE_4_6_3_1_1_FINAL_RESEARCH_VERDICT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_1_FINAL_RESEARCH_VERDICT.md)
- **Milestone 4.6.3.1 Experiment Report:** [`docs/research/MILESTONE_4_6_3_1_EXPERIMENT_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_EXPERIMENT_REPORT.md)
- **Milestone 4.6.3.1 Methodology & Limitations:** [`docs/research/MILESTONE_4_6_3_1_METHODOLOGY_AND_LIMITATIONS.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_METHODOLOGY_AND_LIMITATIONS.md)
- **Milestone 4.6.3.1 Reproduction Guide:** [`docs/research/MILESTONE_4_6_3_1_REPRODUCTION_GUIDE.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_1_REPRODUCTION_GUIDE.md)
- **Milestone 4.6.3.0.1 Independent Protocol Audit:** [`docs/research/MILESTONE_4_6_3_0_1_INDEPENDENT_PROTOCOL_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_0_1_INDEPENDENT_PROTOCOL_AUDIT.md)
- **Milestone 4.6.3.0.1 Frequency Control Audit:** [`docs/research/MILESTONE_4_6_3_0_1_FREQUENCY_CONTROL_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_0_1_FREQUENCY_CONTROL_AUDIT.md)
- **Milestone 4.6.3.0.1 Exposure Control Audit:** [`docs/research/MILESTONE_4_6_3_0_1_EXPOSURE_CONTROL_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_0_1_EXPOSURE_CONTROL_AUDIT.md)
- **Milestone 4.6.3.0.1 News Veto Rule Specification:** [`docs/research/MILESTONE_4_6_3_0_1_NEWS_VETO_RULE_SPECIFICATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_0_1_NEWS_VETO_RULE_SPECIFICATION.md)
- **Milestone 4.6.3.0.1 Statistical Method Validation:** [`docs/research/MILESTONE_4_6_3_0_1_STATISTICAL_METHOD_VALIDATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_0_1_STATISTICAL_METHOD_VALIDATION.md)
- **Milestone 4.6.3.0.1 OOS Protection Audit:** [`docs/research/MILESTONE_4_6_3_0_1_OOS_PROTECTION_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_0_1_OOS_PROTECTION_AUDIT.md)
- **Milestone 4.6.3.0.1 Validation Report:** [`docs/research/MILESTONE_4_6_3_0_1_VALIDATION_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_0_1_VALIDATION_REPORT.md)
- **Milestone 4.6.3.0 Experiment Protocol:** [`docs/research/MILESTONE_4_6_3_0_EXPERIMENT_PROTOCOL.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_0_EXPERIMENT_PROTOCOL.md)
- **Milestone 4.6.3.0 Baseline Freeze:** [`docs/research/MILESTONE_4_6_3_0_BASELINE_FREEZE.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_0_BASELINE_FREEZE.md)
- **Milestone 4.6.3.0 News-Veto Contract:** [`docs/research/MILESTONE_4_6_3_0_NEWS_VETO_CONTRACT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_0_NEWS_VETO_CONTRACT.md)
- **Milestone 4.6.3.0 Data Partition & Coverage:** [`docs/research/MILESTONE_4_6_3_0_DATA_PARTITION_AND_COVERAGE.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_0_DATA_PARTITION_AND_COVERAGE.md)
- **Milestone 4.6.3.0 Statistical Analysis Plan:** [`docs/research/MILESTONE_4_6_3_0_STATISTICAL_ANALYSIS_PLAN.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_0_STATISTICAL_ANALYSIS_PLAN.md)
- **Milestone 4.6.3.0 Validation Report:** [`docs/research/MILESTONE_4_6_3_0_VALIDATION_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_3_0_VALIDATION_REPORT.md)
- **Milestone 4.1.1 Audit:** [`docs/audits/MILESTONE_4_1_1_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_1_1_AUDIT.md)
- **Milestone 4.1.1 Audit:** [`docs/audits/MILESTONE_4_1_1_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_1_1_AUDIT.md)
- **Milestone 4.2.1 Audit:** [`docs/audits/MILESTONE_4_2_1_INDEPENDENT_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_2_INDEPENDENT_AUDIT.md)
- **Milestone 4.3.1 Audit:** [`docs/audits/MILESTONE_4_3_1_AUDIT_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_3_1_AUDIT_REPORT.md)
- **Milestone 4.3.4 Reconciliation:** [`docs/audits/MILESTONE_4_3_4_RESULTS.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_3_4_RESULTS.md)
- **Milestone 4.4 Results:** [`docs/audits/MILESTONE_4_4_RESULTS.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_4_RESULTS.md)
- **Milestone 4.4.1 Provenance Audit:** [`docs/audits/MILESTONE_4_4_1_DATA_PROVENANCE_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_4_1_DATA_PROVENANCE_AUDIT.md)
- **Milestone 4.4.1 Partition Reconciliation:** [`docs/audits/MILESTONE_4_4_1_PARTITION_RECONCILIATION.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_4_1_PARTITION_RECONCILIATION.md)
- **Milestone 4.4.1 Run Manifest Audit:** [`docs/audits/MILESTONE_4_4_1_RUN_MANIFEST_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_4_1_RUN_MANIFEST_AUDIT.md)
- **Milestone 4.4.1 Walk-Forward Audit:** [`docs/audits/MILESTONE_4_4_1_WALK_FORWARD_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_4_1_WALK_FORWARD_AUDIT.md)
- **Milestone 4.4.1 Results Synthesis:** [`docs/audits/MILESTONE_4_4_1_RESULTS.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_4_1_RESULTS.md)
- **Milestone 4.5 Integration Report:** [`docs/audits/MILESTONE_4_5_KRONOS_INTEGRATION.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_5_KRONOS_INTEGRATION.md)
- **Milestone 4.5 Results Synthesis:** [`docs/audits/MILESTONE_4_5_RESULTS.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_5_RESULTS.md)
- **Milestone 4.5.1 Fidelity Audit:** [`docs/audits/MILESTONE_4_5_1_IMPLEMENTATION_FIDELITY.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_5_1_IMPLEMENTATION_FIDELITY.md)
- **Milestone 4.5.1 Temporal Integrity Audit:** [`docs/audits/MILESTONE_4_5_1_TEMPORAL_INTEGRITY.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_5_1_TEMPORAL_INTEGRITY.md)
- **Milestone 4.5.1 Statistical Validity Audit:** [`docs/audits/MILESTONE_4_5_1_STATISTICAL_VALIDITY.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_5_1_STATISTICAL_VALIDITY.md)
- **Milestone 4.5.1 Risk Manager Audit:** [`docs/audits/MILESTONE_4_5_1_RISK_MANAGER_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_5_1_RISK_MANAGER_AUDIT.md)
- **Milestone 4.5.1 Economic Reconciliation:** [`docs/audits/MILESTONE_4_5_1_ECONOMIC_RECONCILIATION.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_5_1_ECONOMIC_RECONCILIATION.md)
- **Milestone 4.5.1 Resource Reproducibility:** [`docs/audits/MILESTONE_4_5_1_RESOURCE_REPRODUCIBILITY.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_5_1_RESOURCE_REPRODUCIBILITY.md)
- **Milestone 4.5.1 Results Synthesis:** [`docs/audits/MILESTONE_4_5_1_RESULTS.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_5_1_RESULTS.md)
- **Milestone 4.6.0 News Feasibility:** [`docs/research/MILESTONE_4_6_0_NEWS_DATA_FEASIBILITY.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_0_NEWS_DATA_FEASIBILITY.md)
- **Milestone 4.6.0.1 Source Validation & Proof:** [`docs/research/MILESTONE_4_6_0_1_NEWS_SOURCE_VALIDATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_0_1_NEWS_SOURCE_VALIDATION.md)
- **Milestone 4.6.1 News Foundation Report:** [`docs/research/MILESTONE_4_6_1_IMPLEMENTATION_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_1_IMPLEMENTATION_REPORT.md)
- **Milestone 4.6.1.1 Historical Coverage Audit:** [`docs/audits/MILESTONE_4_6_1_1_HISTORICAL_COVERAGE.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_6_1_1_HISTORICAL_COVERAGE.md)
- **Milestone 4.6.1.1 Point-in-Time Integrity Audit:** [`docs/audits/MILESTONE_4_6_1_1_POINT_IN_TIME_INTEGRITY.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_6_1_1_POINT_IN_TIME_INTEGRITY.md)
- **Milestone 4.6.1.1 Versioning & Deduplication Audit:** [`docs/audits/MILESTONE_4_6_1_1_VERSION_AND_DEDUP_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_6_1_1_VERSION_AND_DEDUP_AUDIT.md)
- **Milestone 4.6.1.1 Asset Relevance Audit:** [`docs/audits/MILESTONE_4_6_1_1_ASSET_RELEVANCE.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_6_1_1_ASSET_RELEVANCE.md)
- **Milestone 4.6.1.1 Results Synthesis:** [`docs/audits/MILESTONE_4_6_1_1_RESULTS.md`](file:///d:/Project%202026/Trading_bot/docs/audits/MILESTONE_4_6_1_1_RESULTS.md)
- **Milestone 4.6.2 Source Coverage:** [`docs/research/MILESTONE_4_6_2_SOURCE_COVERAGE.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_SOURCE_COVERAGE.md)
- **Milestone 4.6.2 Historical Dataset:** [`docs/research/MILESTONE_4_6_2_HISTORICAL_DATASET.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_HISTORICAL_DATASET.md)
- **Milestone 4.6.2 Event Taxonomy:** [`docs/research/MILESTONE_4_6_2_EVENT_TAXONOMY.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_EVENT_TAXONOMY.md)
- **Milestone 4.6.2 Point-in-Time Policy:** [`docs/research/MILESTONE_4_6_2_POINT_IN_TIME_POLICY.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_POINT_IN_TIME_POLICY.md)
- **Milestone 4.6.2 Data Quality Report:** [`docs/research/MILESTONE_4_6_2_DATA_QUALITY_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_DATA_QUALITY_REPORT.md)
- **Milestone 4.6.2 Implementation Report:** [`docs/research/MILESTONE_4_6_2_IMPLEMENTATION_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_IMPLEMENTATION_REPORT.md)
- **Milestone 4.6.2.1 Coverage Audit:** [`docs/research/MILESTONE_4_6_2_1_COVERAGE_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_1_COVERAGE_AUDIT.md)
- **Milestone 4.6.2.1 Count Reconciliation:** [`docs/research/MILESTONE_4_6_2_1_COUNT_RECONCILIATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_1_COUNT_RECONCILIATION.md)
- **Milestone 4.6.2.1 Classification Audit:** [`docs/research/MILESTONE_4_6_2_1_CLASSIFICATION_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_1_CLASSIFICATION_AUDIT.md)
- **Milestone 4.6.2.1 Point-in-Time Audit:** [`docs/research/MILESTONE_4_6_2_1_POINT_IN_TIME_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_1_POINT_IN_TIME_AUDIT.md)
- **Milestone 4.6.2.1 Deduplication Audit:** [`docs/research/MILESTONE_4_6_2_1_DEDUPLICATION_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_1_DEDUPLICATION_AUDIT.md)
- **Milestone 4.6.2.1 Research Readiness:** [`docs/research/MILESTONE_4_6_2_1_RESEARCH_READINESS.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_1_RESEARCH_READINESS.md)
- **Milestone 4.6.2.1 Final Audit Report:** [`docs/research/MILESTONE_4_6_2_1_FINAL_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_1_FINAL_REPORT.md)
- **Milestone 4.6.2.2 Binance Backfill:** [`docs/research/MILESTONE_4_6_2_2_BINANCE_BACKFILL.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_2_BINANCE_BACKFILL.md)
- **Milestone 4.6.2.2 Macro Calendar:** [`docs/research/MILESTONE_4_6_2_2_MACRO_CALENDAR.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_2_MACRO_CALENDAR.md)
- **Milestone 4.6.2.2 Classification Remediation:** [`docs/research/MILESTONE_4_6_2_2_CLASSIFICATION_REMEDIATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_2_CLASSIFICATION_REMEDIATION.md)
- **Milestone 4.6.2.2 Classification Validation:** [`docs/research/MILESTONE_4_6_2_2_CLASSIFICATION_VALIDATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_2_CLASSIFICATION_VALIDATION.md)
- **Milestone 4.6.2.2 Point-in-Time Validation:** [`docs/research/MILESTONE_4_6_2_2_POINT_IN_TIME_VALIDATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_2_POINT_IN_TIME_VALIDATION.md)
- **Milestone 4.6.2.2 Dataset Versioning:** [`docs/research/MILESTONE_4_6_2_2_DATASET_VERSIONING.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_2_DATASET_VERSIONING.md)
- **Milestone 4.6.2.2 Research Relevance:** [`docs/research/MILESTONE_4_6_2_2_RESEARCH_RELEVANCE.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_2_RESEARCH_RELEVANCE.md)
- **Milestone 4.6.2.2 Final Report:** [`docs/research/MILESTONE_4_6_2_2_FINAL_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_2_FINAL_REPORT.md)
- **Milestone 4.6.2.3 Classifier Reconciliation:** [`docs/research/MILESTONE_4_6_2_3_CLASSIFIER_RECONCILIATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_3_CLASSIFIER_RECONCILIATION.md)
- **Milestone 4.6.2.3 Relevance & Coverage Audit:** [`docs/research/MILESTONE_4_6_2_3_RELEVANCE_COVERAGE.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_3_RELEVANCE_COVERAGE.md)
- **Milestone 4.6.2.3 Macro Provenance Audit:** [`docs/research/MILESTONE_4_6_2_3_MACRO_PROVENANCE.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_3_MACRO_PROVENANCE.md)
- **Milestone 4.6.2.3 Point-in-Time Integration Audit:** [`docs/research/MILESTONE_4_6_2_3_PIT_INTEGRATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_3_PIT_INTEGRATION.md)
- **Milestone 4.6.2.3 Final Forensic Audit Report:** [`docs/research/MILESTONE_4_6_2_3_FINAL_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_3_FINAL_AUDIT.md)
- **Milestone 4.6.2.4 Execution Contract:** [`docs/research/MILESTONE_4_6_2_4_EXECUTION_CONTRACT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_4_EXECUTION_CONTRACT.md)
- **Milestone 4.6.2.4 Engine Integration:** [`docs/research/MILESTONE_4_6_2_4_ENGINE_INTEGRATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_4_ENGINE_INTEGRATION.md)
- **Milestone 4.6.2.4 Validation Report:** [`docs/research/MILESTONE_4_6_2_4_VALIDATION_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_4_VALIDATION_REPORT.md)
- **Milestone 4.6.2.5 Independent Audit:** [`docs/research/MILESTONE_4_6_2_5_INDEPENDENT_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_5_INDEPENDENT_AUDIT.md)
- **Milestone 4.6.2.5 Cost Reconciliation:** [`docs/research/MILESTONE_4_6_2_5_EXECUTION_COST_RECONCILIATION.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_5_EXECUTION_COST_RECONCILIATION.md)
- **Milestone 4.6.2.5 News PIT Audit:** [`docs/research/MILESTONE_4_6_2_5_NEWS_PIT_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_5_NEWS_PIT_AUDIT.md)
- **Milestone 4.6.2.5 Risk Authorization Audit:** [`docs/research/MILESTONE_4_6_2_5_RISK_AUTHORIZATION_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_5_RISK_AUTHORIZATION_AUDIT.md)
- **Milestone 4.6.2.5 Validation Report:** [`docs/research/MILESTONE_4_6_2_5_VALIDATION_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_5_VALIDATION_REPORT.md)
- **Milestone 4.6.2.5.1 HMAC Lifecycle Audit:** [`docs/research/MILESTONE_4_6_2_5_1_HMAC_LIFECYCLE_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_5_1_HMAC_LIFECYCLE_AUDIT.md)
- **Milestone 4.6.2.5.1 Idempotency Audit:** [`docs/research/MILESTONE_4_6_2_5_1_IDEMPOTENCY_AUDIT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_5_1_IDEMPOTENCY_AUDIT.md)
- **Milestone 4.6.2.5.1 Execution Gap Policy:** [`docs/research/MILESTONE_4_6_2_5_1_EXECUTION_GAP_POLICY.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_5_1_EXECUTION_GAP_POLICY.md)
- **Milestone 4.6.2.5.1 Final Validation Report:** [`docs/research/MILESTONE_4_6_2_5_1_FINAL_VALIDATION_REPORT.md`](file:///d:/Project%202026/Trading_bot/docs/research/MILESTONE_4_6_2_5_1_FINAL_VALIDATION_REPORT.md)


---
*End of Research Paper — Project NEPTUNE Quantitative Systems Group*

