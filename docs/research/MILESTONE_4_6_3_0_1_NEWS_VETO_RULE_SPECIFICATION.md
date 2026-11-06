# NEPTUNE — Milestone 4.6.3.0.1
## Executable Point-in-Time News-Veto Rule Specification

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Document:** Executable News-Veto Contract & Decision Engine Specification  
**Author:** Quantitative Audit Agent  
**Governing Rules:** Rule S-04, Rule S-05, Rule S-06, ADR-028, ADR-030  

---

## 1. Architectural Purpose

Group B evaluates whether point-in-time news intelligence can improve trading expectancy by **vetoing** candidate technical setups that coincide with adverse news regimes.

Under Rule S-01, Rule S-04, and ADR-029:
- **News NEVER generates directional buy/sell signals.** All candidate setups are generated purely by the frozen technical strategy.
- **News CANNOT override the Risk Manager.** If the Risk Manager rejects an order, news intelligence cannot authorize it.
- **News acts solely as an adverse regime filter.**

---

## 2. Executable Decision Engine Architecture

The decision logic is encapsulated in [`NewsVetoDecisionEngine`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py):

```
Candidate Technical Signal (Time t)
                  │
                  ▼
   Fetch Active News Events (Available at or before t)
                  │
                  ▼
         For each candidate event:
           ├─ 1. Cluster Deduplication (Earliest in cluster only)
           ├─ 2. Invariant Validation (Availability <= t, Source Verified)
           ├─ 3. GDELT Intraday Filter (Disallow sub-daily GDELT vetoes)
           ├─ 4. Revision Cutoff (Ignore revisions occurring after t)
           ├─ 5. Asset Relevance Match (Market-wide or Base Asset match)
           ├─ 6. Decay Window Check (Elapsed time <= Pre-registered window)
           └─ 7. Severity Threshold Check:
                   effective_impact = adverse_score * reliability * taxonomy_weight
                   if effective_impact >= 0.70:
                       ==> VETO CANDIDATE SIGNAL
```

---

## 3. Pre-Registered Category Decay Windows

To prevent post-hoc curve fitting, decay windows are pre-registered prior to any simulation runs:

| Category ID | Decay Window | Duration | Scope | Rationale |
|-------------|--------------|----------|-------|-----------|
| `SECURITY_EXPLOITS` | 86,400s | 24 Hours | Market-wide | Major exploit volatility, contagion, and liquidity drainage persist for a full day. |
| `EXCHANGE_OUTAGES_SUSPENSIONS` | 14,400s | 4 Hours | Market-wide | Emergency maintenance and matching engine halts disrupt price discovery for several hours. |
| `NETWORK_PROTOCOL_INCIDENTS` | 43,200s | 12 Hours | Base Asset | Reorganizations and node faults require multiple block confirmations to resolve. |
| `EXCHANGE_OPERATIONAL` | 7,200s | 2 Hours | Market-wide | Scheduled wallet maintenance or brief platform updates resolve within 2 hours. |
| `DIRECT_BTC` | 21,600s | 6 Hours | BTCUSDT | Protocol-level or capital announcements affecting Bitcoin directly. |
| `DIRECT_ETH` | 21,600s | 6 Hours | ETHUSDT | Hard forks, upgrade delays, or Ethereum Foundation advisories. |
| `DIRECT_BNB` | 21,600s | 6 Hours | BNBUSDT | BNB Chain upgrades, quarterly burns, or exchange-native regulatory actions. |
| `REGULATORY` | 43,200s | 12 Hours | Market-wide | SEC/CFTC enforcement actions or major legal rulings create multi-hour volatility waves. |
| `MACROECONOMIC` | 7,200s | 2 Hours | Market-wide | FOMC rate decisions, US CPI, and NFP create high-volatility whipsaws that subside in 2 hours. |
| `ETF_INSTITUTIONAL_FLOW` | 14,400s | 4 Hours | BTC / ETH | Significant net outflows or filing updates affect institutional spot liquidity for half a session. |
| `LISTINGS_DELISTINGS` | 86,400s | 24 Hours | HTF Only | Ineligible for 15m/1h/4h intraday execution; daily/weekly aggregate breadth only. |

---

## 4. Scoring Formula and Threshold

A candidate signal is vetoed if any active, unexpired, asset-matching news event meets:

$$\text{effective\_impact} = S_{\text{adverse}} \times R_{\text{source}} \times W_{\text{taxonomy}} \ge \theta$$

Where:
- $S_{\text{adverse}} \in [0.0, 1.0]$: Event adverse impact score.
- $R_{\text{source}} \in [0.0, 1.0]$: Source reliability score (1.0 for official Binance/BLS, 0.5 for GDELT).
- $W_{\text{taxonomy}} \in [0.0, 1.0]$: Pre-registered taxonomy category weight.
- $\theta = 0.70$: Pre-registered adverse veto threshold.

---

## 5. Verification Status

All news-veto adversarial tests passed in [`test_milestone_4_6_3_0_1_adversarial.py`](file:///d:/Project%202026/Trading_bot/backend/tests/unit/test_milestone_4_6_3_0_1_adversarial.py):
- `test_future_publication_rejected_as_lookahead`: **PASSED**
- `test_expired_event_beyond_decay_window_rejected`: **PASSED**
- `test_active_event_within_decay_window_triggers_veto`: **PASSED**
- `test_cluster_deduplication_prevents_duplicate_processing`: **PASSED**
- `test_wrong_asset_relevance_ignored`: **PASSED**
- `test_gdelt_intraday_veto_prohibited`: **PASSED**
- `test_rejected_provenance_cannot_veto`: **PASSED**
