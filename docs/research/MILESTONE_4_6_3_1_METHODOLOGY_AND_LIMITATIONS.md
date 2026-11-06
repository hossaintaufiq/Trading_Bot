# NEPTUNE — Milestone 4.6.3.1
## Methodology and Limitations Report: 2024 Development Partition

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Milestone:** 4.6.3.1  
**Partition:** 2024 Development / Training (`2024-01-01T00:00:00Z` to `2024-12-31T23:59:59Z`)  
**Date:** 2026-11-06  
**Governing Rules:** Rule S-01, Rule S-04, Rule S-05, Rule S-06, ADR-028, ADR-029, ADR-030  

---

## 1. Experimental Methodology Overview

Milestone 4.6.3.1 executes the first controlled empirical experiment under NEPTUNE's frozen research protocol.

The core objective is to evaluate the causal impact of adding point-in-time news intelligence as an adverse veto filter to a deterministic technical strategy, after strictly controlling for:
1. Trade opportunity frequency (Group C).
2. Capital utilization and time-in-market (Group D).
3. Realistic transaction costs (32 bps round-trip friction).
4. Risk Manager authorization constraints (0.5% risk/trade, 2% daily loss limit, 5% max drawdown circuit breaker).

```
Candidate Stream (Shared across all 4 groups)
         │
         ├───────────────────┬───────────────────┬───────────────────┐
         ▼                   ▼                   ▼                   ▼
    ┌─────────┐         ┌─────────┐         ┌─────────┐         ┌─────────┐
    │ Group A │         │ Group B │         │ Group C │         │ Group D │
    │ Baseline│         │News-Veto│         │Frequency│         │Exposure │
    └────┬────┘         └────┬────┘         └────┬────┘         └────┬────┘
         │                   │                   │                   │
    Direct Pass         PIT News Veto       Online Thinning     Online Cooldown
         │              (θ >= 0.70)         (ρ = 0.85)          (4 bars)
         │                   │                   │                   │
         └─────────┬─────────┴─────────┬─────────┴─────────┬─────────┘
                   ▼                   ▼                   ▼
         ┌───────────────────────────────────────────────────┐
         │ Risk Manager Sole Order Authorization (Rule S-04) │
         └─────────────────────────┬─────────────────────────┘
                                   │
                                   ▼
         ┌───────────────────────────────────────────────────┐
         │ Point-in-Time Execution Scheduler (NEXT_PRICE)    │
         └───────────────────────────────────────────────────┘
```

---

## 2. Experimental Group Implementations

### Group A: Deterministic Baseline
- **Execution Mode:** `ONLINE_POINT_IN_TIME`.
- **Strategy:** `trend_continuation_v1` on `BTCUSDT`, `ETHUSDT`, `BNBUSDT` (15m timeframe).
- **Filtering:** No external news or thinning applied. Every technical candidate setup meeting confluence criteria is passed directly to the Risk Manager.
- **Role:** Primary reference benchmark.

### Group B: Point-in-Time News Veto
- **Execution Mode:** `ONLINE_POINT_IN_TIME`.
- **Input Stream:** Identical candidate setups generated at identical candle timestamps as Group A.
- **Veto Engine:** [`NewsVetoDecisionEngine`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py).
- **Veto Rules:**
  - Events visible at or before candle close timestamp $T$ ($T_{\text{avail}} \le T_{\text{close}}$).
  - Effective adverse impact $I_{\text{eff}} = S_{\text{adverse}} \times R_{\text{source}} \times W_{\text{taxonomy}} \ge 0.70$.
  - Pre-registered decay windows (2 hours for operational/macro to 24 hours for security exploits).
  - Cluster deduplication (earliest observed article in syndication cluster triggers veto).
  - Strict revision cutoff isolation (revisions occurring after decision time are invisible).
  - GDELT sub-daily intraday records strictly prohibited.
- **Safety Invariant:** News intelligence cannot generate entry signals and cannot override Risk Manager rejections.

### Group C: Online Frequency-Matched Control
- **Execution Mode:** `ONLINE_POINT_IN_TIME`.
- **Engine:** [`OnlineFrequencyMatchingEngine`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py).
- **Mechanism:** Sequential cryptographic HMAC thinning:
  $$\text{score} = \frac{\text{int}(\text{HMAC-SHA256}(\text{seed}, \text{cand\_id} \parallel \text{timestamp} \parallel \text{symbol})[:8], 16)}{2^{32} - 1}$$
  $$\text{Accepted if } \text{score} < \rho_{\text{calib}} \quad (\rho = 0.85)$$
- **Zero-Lookahead Guarantee:** Does not consume future candidate arrivals, future trade counts ($N_B$), or future trade returns.

### Group D: Online Exposure-Matched Control
- **Execution Mode:** `ONLINE_POINT_IN_TIME`.
- **Engine:** [`OnlineExposureMatchingEngine`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py).
- **Mechanism:** Enforces a running dynamic cooldown of 4 bars (60 minutes) per symbol following any position exit.
- **Zero-Lookahead Guarantee:** Does not consume future trade holding durations, total partition exposure bars, or future price drift.

---

## 3. Retrospective Ex-Post Diagnostic Controls

In compliance with Milestone 4.6.3.0.1 audit findings, any matching method requiring the final total count ($N_B$) or final total exposure bars of Group B across the entire partition is classified as an **Ex-Post Diagnostic Benchmark**, not an online trading strategy:

1. **Method C1 (Systematic Decimation):** Decimates Group A candidate stream uniformly to match exact count $N_B$.
2. **Method C2 (Technical Confidence Priority):** Prunes Group A candidates by sorting by `raw_confidence` descending to retain the top $N_B$ candidates.
3. **Method C3 (Cryptographic Seed Selection):** Pseudorandomly samples exactly $N_B$ candidates from Group A using a deterministic SHA-256 seed.
4. **Method D-ExPost (Exposure Budget Match):** Budgets candidate entries to match Group B's total exposure bars retrospectively.

---

## 4. Methodological Limitations

1. **Development Partition Specificity:** The 2024 Development partition represents a distinct macroeconomic regime (Bitcoin spot ETF approvals in January 2024, post-halving consolidation in April–October 2024, and post-election expansion in November–December 2024). Results obtained on this partition cannot be generalized without out-of-sample validation.
2. **Catalog 49 Coverage Boundary:** Historical news coverage relies primarily on Binance Announcements and authoritative macroeconomic releases. Altcoin-specific sentiment from GDELT is prohibited on intraday timeframes due to timestamp imprecision.
3. **Single-Timeframe Execution:** Intraday execution is evaluated on 15m candles with higher-timeframe alignment. Multi-timeframe execution dynamics (e.g. 1h, 4h) may exhibit different sensitivity to event decay windows.
4. **Execution Gap Tolerance:** Intraday orders expire if market data gaps exceed 1 bar (30 minutes). Extreme network latency in live execution could cause higher expiration rates than observed in simulated historical replay.
5. **Conservative Ambiguity Policy:** Intrabar ambiguity resolution conservatively assumes stop losses are hit before take-profit targets when both price thresholds are touched within the same candle bar.

