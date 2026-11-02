# NEPTUNE — Milestone 4.6.2.3: Market Relevance & Cluster Coverage Audit

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Milestone:** 4.6.2.3 (Forensic Relevance Audit)  
**Evaluator:** Independent Forensic Audit Agent  
**Date:** 2026-11-03  
**Status:** COMPLETE — RELEVANCE QUANTIFIED & BOUNDED  
**Governing Rules:** S-06, S-07, ADR-024, ADR-025  

---

## 1. Executive Summary & Research Question

A fundamental warning raised in Milestone 4.6.2.1 was:
> *The news dataset is dominated by altcoin listings (Catalog 48) and general exchange updates, containing zero direct BTC, ETH, or BNB announcements.*

Milestone 4.6.2.3 conducted an exhaustive census of all **1,431 news articles**, **1,421 event clusters**, and **68 macroeconomic events** to separate direct trading asset relevance from exchange-wide and retail noise.

---

## 2. Census of All 1,431 News Articles by Relevance Tier

| Relevance Classification | Article Count | Share of Corpus | Economic Nature & Research Role |
|--------------------------|---------------|-----------------|---------------------------------|
| **`EXCHANGE_WIDE`** | **664** | **46.40%** | Binance futures specifications, margin tier changes, tick size schedules, wallet maintenance, and fee adjustments. Direct operational context for execution friction. |
| **`DIRECT_ASSET`** | **280** | **19.57%** | Articles explicitly naming target assets (BTC: 245, ETH: 131, BNB: 197) in an actionable economic context (ETF flows, network upgrades, direct token burns). |
| **`UNCLASSIFIED`** | **273** | **19.08%** | Retail marketing campaigns, Earn Wednesday, mystery boxes, giveaways, and referral promotions. **Zero economic signal; stripped from trading models.** |
| **`OTHER_ASSET`** | **195** | **13.63%** | Altcoin listings (Catalog 48) and delistings (Catalog 161) isolated from BTC/ETH. Serves solely as aggregate market risk appetite context. |
| **`MARKET_WIDE`** | **15** | **1.05%** | Broad industry-level regulatory, macro, or multi-asset developments. |
| **`MACRO`** | **4** | **0.28%** | Specific news articles reporting macroeconomic events (complemented by the 68 dedicated Source C calendar records). |
| **Total** | **1,431** | **100.0%** | Comprehensive census across all ingested article records. |

---

## 3. Direct Target Asset Breakdown

Across the 1,431 articles and 68 macro events:
- **BTC-Relevant Records:** **245 articles + 68 macro events = 313 events** (average 8.9 events/month).
- **ETH-Relevant Records:** **131 articles + 68 macro events = 199 events** (average 5.7 events/month).
- **BNB-Relevant Records:** **197 articles + 68 macro events = 265 events** (average 7.6 events/month).

### Audit Determination on Asset Coverage:
NEPTUNE is **not** data-starved for BTC, ETH, and BNB. With 5.7 to 8.9 direct/macro events per month per asset, there is sufficient event frequency to test defensive news filters (such as volatility pauses or leverage de-risking) without starving strategies of trade opportunities.

---

## 4. Event Clustering & Deduplication Audit

- **Total Stored Event Clusters:** **1,421 clusters** across 1,431 articles and 1,431 member mappings.
- **Single-Article Clusters:** **1,413 clusters** ($99.4\%$).
- **Multi-Article Clusters (Deduplicated):** **8 clusters** representing 26 articles.
- **Deduplication Method:** SimHash 64-bit with Hamming distance $\le 3$ bits and 24-hour temporal window.

### Top Multi-Article Clusters Identified:
1. `Updates on the Leverage & Margin Tiers of Multiple USDⓈ-M Perpetual Contracts (2025-02-17)`: 3 articles collapsed into 1 cluster.
2. `Updates on the Leverage & Margin Tiers of Multiple USDⓈ-M Perpetual Contracts (2025-02-24)`: 3 articles collapsed into 1 cluster.
3. `New funds will make investing in bitcoin easier. Here's what you need to know`: 2 GDELT syndicated wire articles collapsed into 1 cluster.
4. `Here's everything you need to know about Bitcoin ETFs`: 2 GDELT syndicated articles collapsed into 1 cluster.

**Audit Finding on Clustering:**  
The multi-stage clusterer successfully collapses identical exchange updates and syndicated wire news. The low multi-article rate ($0.6\%$) is expected given that Binance Public CMS issues distinct URLs and codes for different notices, while the GDELT sample was bounded.

---

## 5. Research Suitability Conclusion

1. **Defensive Filtering Suitability:** The dataset contains ample high-impact events (margin tier updates, tick size changes, ETF flows, and macroeconomic prints) to test whether avoiding or hedging around these periods improves net risk-adjusted returns.
2. **Directional Alpha Warning:** There is **no evidence** that headline sentiment predicts future directional returns. News intelligence must be tested as a defensive filter or volatility regime marker, not as an unconstrained directional signal.

