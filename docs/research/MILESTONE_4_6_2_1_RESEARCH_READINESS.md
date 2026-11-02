# NEPTUNE — Milestone 4.6.2.1: Quantitative Research Readiness Assessment

**Document:** Strategy Experimentation Suitability & Economic Relevance Evaluation  
**Milestone:** 4.6.2.1 (Forensic Data Audit)  
**Evaluator:** Independent Audit Agent  
**Date:** 2026-11-03  
**Status:** COMPLETE — QUALIFIED RESEARCH READINESS (EVENT STUDIES & MACRO FILTERS ONLY)  

---

## 1. Primary Research Question

The core mandate of this audit is to answer the fundamental question:

> **Does NEPTUNE currently possess a sufficiently representative, correctly classified, point-in-time-safe historical news dataset to conduct controlled experiments that could help discover a profitable trading strategy?**

### The Definitive Verdict:
**YES, WITH STRICT LIMITATIONS.**

NEPTUNE possesses a point-in-time-safe, reproducible dataset that is **immediately suitable for discrete Event Studies and Macroeconomic Risk Filters**. However, it is **not yet suitable for continuous intraday alpha backtesting** across the entire 35-month market dataset `v2.0.0` due to the 2025 coverage void.

---

## 2. Asset-Specific Economic Relevance Analysis

From `storage/exports/milestone_4_6_2_1/asset_specific_event_coverage.csv`, we independently quantified the volume of economically relevant news events for NEPTUNE's three primary spot trading pairs:

| Target Asset | Direct Asset Articles | Exchange-Wide Articles | Macro-Relevant Articles | Canonical Macro Events | Total Economically Relevant Events | PIT Verified Ratio |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **BTCUSDT** | 164 | 26 | 22 | 24 | **236** | $90.7\%$ |
| **ETHUSDT** | 93 | 15 | 22 | 24 | **154** | $85.7\%$ |
| **BNBUSDT** | 81 | 1 | 22 | 22 | **126** | $82.5\%$ |

### Economic Insights:
1. **High Macro Relevance:** All 24 canonical macro calendar events in 2024 (FOMC, CPI, NFP, Halving, ETFs) directly impacted BTCUSDT and ETHUSDT market dynamics.
2. **Conservative Attribution for BNB:**
   - Under the Rule established in 4.6.2 ("*A Binance exchange operational incident must not become DIRECT_ASSET for BNB unless it directly alters the BNB token contract or supply*"), out of 241 `EXCHANGE_WIDE` operational announcements, only 1 was attributed as direct BNB relevance (BNB auto-burn). The remaining 240 were isolated as exchange infrastructure operations. This successfully eliminates the false positive trap of treating maintenance notices as BNB price shocks.

---

## 3. Allowed vs. Prohibited Research Modalities

| Research Modality | Status | Methodological Justification |
|:---|:---:|:---|
| **Macroeconomic Risk Overlay** | **AUTHORIZED** | Testing whether pausing entry signals $\pm 2$ hours around the 24 FOMC and CPI releases in 2024 improves strategy Sharpe ratio and reduces maximum drawdown. All 24 events are 100% PIT-verified. |
| **Discrete Event Studies** | **AUTHORIZED** | Measuring post-event price drift (1h, 4h, 24h, 72h) following discrete regulatory actions, ETF approvals, hard forks, or delistings in 2024 and late 2026. |
| **Exchange Operational Volatility Filter** | **AUTHORIZED** | Evaluating whether exchange wallet maintenance or futures system upgrades predict temporary liquidity dry-ups or spread widening. |
| **Continuous 35-Month Intraday Alpha Backtest** | **PROHIBITED** | The dataset contains 0 records in 2025 and Jan–May 2026. Running a continuous 35-month walk-forward backtest would create an artificial 17-month news vacuum, distorting performance metrics. |
| **High-Frequency GDELT Sentiment Signal** | **PROHIBITED** | GDELT records lack primary publication timestamps (`published_at` is `NULL`). Using GDELT in 1m, 5m, or 15m candle backtests introduces timestamp ambiguity. |

---

## 4. Requirements for Milestone 4.6.3

To graduate from "Qualified Research Readiness" to "Full Continuous Research Readiness":

1. **Backfill the 2025 Void (Pages 11–47):**
   - Execute a polite, throttled historical crawl of Binance Catalog 49 pages 11 through 47.
   - Pacing: 1.0s delay between requests with exponential backoff on HTTP 429.
2. **Expand Macro Calendar to 2025–2026:**
   - Ingest official FOMC rate decisions and BLS CPI/NFP release timestamps for calendar years 2025 and 2026.
3. **Deploy Classifier v1.1.0:**
   - Implement title-primary classification to prevent legal disclaimers from overriding listing categories.
   - Strip standard risk disclaimers before regex matching.
   - Add punctuation normalization (`E.T.F.` $\to$ `ETF`).

---
*End of Research Readiness Assessment.*

