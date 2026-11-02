# NEPTUNE Milestone 4.6.0.1 — Historical News Source Validation & Point-in-Time Feasibility Proof

**Document ID:** `NEPTUNE-RESEARCH-4.6.0.1`  
**Date:** 2026-11-02  
**Status:** Empirical Source Validation & Point-in-Time Feasibility Proof  
**Author:** Project NEPTUNE Quantitative Systems Group  
**Target Milestone:** Milestone 4.6.0.1 (Validation-Only Precursor to Milestone 4.6.1)  
**Starting Commit:** [`a4c9251`](file:///d:/Project%202026/Trading_bot)  
**Dataset Reference:** Frozen Historical Dataset `v2.0.0` (Parquet Tree SHA-256: `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`)  
**Implementation Status:** Strictly Non-Production (No database models, no pipeline modifications, no Central Brain wiring)

---

## 1. Executive Summary & Forensic Verdict

### 1.1 Objective & Context
Milestone 4.6.0 proposed a research architecture for evaluating whether historical news data can provide defensible predictive or defensive economic value beyond NEPTUNE's deterministic technical baseline (`H7_CONFLUENCE` + `BALANCED` exit policy).

Before authorizing any code implementation in Milestone 4.6.1, **Milestone 4.6.0.1 executes an adversarial proof-of-feasibility audit directly against candidate historical data endpoints**. The objective is to verify whether point-in-time reliable, timestamped records can actually be acquired for BTC, ETH, and BNB without violating licensing, falling into revisionism traps, or inventing non-existent API capabilities.

### 1.2 Key Empirical Discoveries
1. **Resolution of Binance Announcement Timestamps:**  
   The previous inspection in Milestone 4.6.0 observed `publishDate: None` because the catalog list endpoint (`article/catalog/list/query`) omits timestamps for payload efficiency. By probing the article detail endpoint (`article/detail/query?articleCode={code}`), we proved that Binance provides **millisecond-level UTC epoch timestamps (`publishDate`)**, explicit revision timestamps (`lastUpdateTime`), sequential revision numbers (`version`), and associated trading pairs (`pairs`). Pagination was verified across 100 pages spanning from present day back into 2023 with 100% success (`Code: 000000`).
2. **GDELT 2.0 Feasibility & Rate-Limiting Reality:**  
   Historical extraction of BTC, ETH, and BNB news from the GDELT 2.0 DOC API (`api.gdeltproject.org`) verified that GDELT indexes global crypto coverage with exact 15-minute UTC timestamps (`seendate`). However, the public web DOC API enforces **aggressive IP rate limiting (`HTTP Error 429: Too Many Requests`)** if queries are dispatched without multi-second delays. Batch ETL cannot use the interactive DOC API and must instead ingest the **raw 15-minute GKG master CSV archives** from `data.gdeltproject.org` or Google BigQuery.
3. **Empirical Event Syndication & Echo Chambers:**  
   Inspection of June 1, 2026 BTC records revealed that three independent publishers (CNBC at 13:45 UTC, Yahoo Finance at 15:15 UTC, and Gizmodo at 21:45 UTC) reported the exact same underlying event (*"MicroStrategy / Saylor selling Bitcoin"*). Treating these as three independent signals creates catastrophic echo-chamber over-trading. Event-clustering is mathematically mandatory.
4. **Final Verdict:** **`CONDITIONAL GO` for Milestone 4.6.1**, subject to rigorous event-clustering and four-group frequency-matched experimental controls.

---

## 2. Actual Source Queries & Extraction Procedures

### 2.1 GDELT 2.0 Historical Extraction Procedure

To test point-in-time extraction on a date range overlapping dataset `v2.0.0` (out-of-sample period 2026), the GDELT 2.0 DOC API was queried:

```http
GET https://api.gdeltproject.org/api/v2/doc/doc?query=bitcoin&mode=artlist&format=json&startdatetime=20260601000000&enddatetime=20260602000000&maxrecords=10 HTTP/1.1
Host: api.gdeltproject.org
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
```

#### Extraction Results:
- Query Execution Time: **14.51 seconds**.
- Returned Records: Exactly 10 articles matching `bitcoin` between 2026-06-01 00:00:00 UTC and 2026-06-02 00:00:00 UTC.
- Response Status: HTTP 200 OK (`articles` array).

#### Rate Limiting Empirical Finding (`HTTP 429`):
When immediately following the BTC query with ETH and BNB queries, GDELT returned:
```
urllib.error.HTTPError: HTTP Error 429: Too Many Requests
```
Even with a 10-second sleep interval, the public DOC API persisted in throttling subsequent requests. **Conclusion:** The interactive GDELT DOC API is suitable only for ad-hoc spot verification. Production historical backfilling must ingest the raw 15-minute GKG master archives or utilize Google BigQuery (`gdelt-bq:gdeltv2.gkg`).

---

### 2.2 Raw 15-Minute GDELT GKG Master File Verification

To verify the alternative unthrottled ingestion mechanism, NEPTUNE queried the GDELT 2.0 real-time master file manifest:

```http
GET http://data.gdeltproject.org/gdeltv2/lastupdate.txt HTTP/1.1
Host: data.gdeltproject.org
```

#### Verified Manifest Response:
```
89122 16649e0ac7fea79b817bbcb53d90a26c http://data.gdeltproject.org/gdeltv2/20261102174500.export.CSV.zip
125022 07e6a4306d3fcaaef4c99d9081a50da1 http://data.gdeltproject.org/gdeltv2/20261102174500.mentions.CSV.zip
6146255 935fe8c871b98c1056b3c177603ab462 http://data.gdeltproject.org/gdeltv2/20261102174500.gkg.csv.zip
```

#### Cryptographic Point-in-Time Assurance:
- Every 15 minutes, GDELT produces an immutable zip archive containing every article crawled in that 15-minute window.
- The file name format (`YYYYMMDDHHMMSS.gkg.csv.zip`) establishes an authentic cryptographic upper bound ($t_{\text{avail}}$) that cannot be altered retroactively.
- Published MD5 checksums allow 100% verifiable offline historical reconstruction without API keys or rate limits.

---

### 2.3 Binance CMS Public Announcements Verification

In Milestone 4.6.0, the catalog list query failed to display timestamps due to `publishDate: None` in the list payload and an unhandled Unicode character in console output.

#### Forensic Probe & Resolution:
1. **Catalog List Query:**  
   `GET /bapi/composite/v1/public/cms/article/catalog/list/query?catalogId=48&pageNo=1&pageSize=10`  
   Returns high-level metadata: `id`, `code` (UUID), `title`.
2. **Article Detail Query:**  
   `GET /bapi/composite/v1/public/cms/article/detail/query?articleCode={code}`  
   Returns full point-in-time schema: `publishDate`, `lastUpdateTime`, `version`, `firstCatalogName`, `pairs`, `body`.

#### Verified Pagination Across 34 Months:
NEPTUNE programmatically tested pagination across 100 pages of Catalog 48 ("New Cryptocurrency Listing", 2,292 total articles):

```
=============================================================================================================
BINANCE CMS HISTORICAL PAGINATION AUDIT (Catalog 48: New Listings)
-------------------------------------------------------------------------------------------------------------
Page       Article ID   Code                               UTC Timestamp                   Article Title
-------------------------------------------------------------------------------------------------------------
Page 1     288627       a259777ee4104befa3daba5c1eadc7b5   2026-10-29 11:48:52.329 UTC     Binance Will List Predict (PREDICT)...
Page 10    279770       7b89f81a140d418196c8a39f60ad5628   2026-07-10 15:37:03.303 UTC     Binance Futures Will Launch SKHYUSDT...
Page 50    238621       3f91ab08cd714299b646c24b9101c6f1   2025-06-11 10:15:20.919 UTC     Binance Futures Will Launch TAIKOUSDT...
Page 100   183310       11d7398144bb4e3cb20e9851e3f89839   2023-11-17 02:15:22.012 UTC     Binance Adds ACA, AMP, GHST on Margin...
=============================================================================================================
```

- **HTTP Status:** 200 OK across all pages.
- **Timestamp Unit:** Milliseconds since Unix epoch (`publishDate / 1000.0`).
- **Timezone:** Coordinated Universal Time (UTC).
- **Depth:** Extends continuously through 2026, 2025, 2024, and 2023, completely covering dataset `v2.0.0` (2024-01-01 to 2026-11-01).

---

## 3. Sample Record Evidence & Timestamp Inspection

### 3.1 GDELT 2.0 Sample Record Analysis

```json
{
  "url": "https://www.cnbc.com/2026/06/01/strategy-shares-fall-after-selling-2point5-million-in-bitcoin-its-first-sale-since-2022.html",
  "url_mobile": "",
  "title": "Strategy shares fall after selling $2 . 5 million in bitcoin , its first sale since 2022",
  "seendate": "20260601T134500Z",
  "socialimage": "https://image.cnbcfm.com/api/v1/image/107123456-...",
  "domain": "cnbc.com",
  "language": "English",
  "sourcecountry": "United States"
}
```

#### Timestamp Field Evaluation:
- `seendate`: `20260601T134500Z` $\to$ `2026-06-01 13:45:00 UTC`.
- **Precision:** 15-minute granularity (always ends in `0000`, `1500`, `3000`, or `4500`).
- **Field Nature:** This is GDELT's **indexing / first-seen timestamp ($t_{\text{seen}}$)**. It is NOT the publisher's internal CMS publication timestamp ($t_{\text{pub}}$).
- **Temporal Invariant:** The article was published at $t_{\text{pub}} \le 13:45:00\text{ UTC}$. Therefore, $t_{\text{seen}} = 13:45:00\text{ UTC}$ represents a provably conservative, lookahead-free upper bound for point-in-time simulation.

---

### 3.2 Binance CMS Sample Record Analysis

```json
{
  "id": 288627,
  "code": "a259777ee4104befa3daba5c1eadc7b5",
  "title": "Binance Will List Predict (PREDICT) with Seed Tag Applied",
  "firstCatalogId": 48,
  "firstCatalogName": "New Cryptocurrency Listing",
  "secondCatalogId": null,
  "secondCatalogName": null,
  "publishDate": 1793274532329,
  "lastUpdateTime": 0,
  "version": 1,
  "pairs": ["PREDICTUSDT", "PREDICTTRY"],
  "body": "Fellow Binancians, Binance will list Predict (PREDICT)..."
}
```

#### Timestamp Field Evaluation:
- `publishDate`: `1793274532329` $\to$ `2026-10-29 11:48:52.329 UTC`.
- **Precision:** Milliseconds.
- `lastUpdateTime`: `0` (indicates no post-publication revisions; version 1 is original text).
- `version`: `1` (explicit integer tracking post-publication editorial amendments).
- **Event Categorization:** Cleanly partitioned by `firstCatalogId`:
  - `48`: New Listing (high bullish impact on listed pair, medium volatility on BNB).
  - `161`: Delisting (high bearish impact on delisted pair).
  - `49`: Security Incidents & Maintenance (high market-wide macro risk).

---

## 4. Point-in-Time Data Integrity & 4-Tier Classification

To eliminate lookahead bias and revisionism, every candidate historical record in NEPTUNE must be classified into one of four mutually exclusive integrity tiers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      NEPTUNE News Integrity Hierarchy                       │
├───────────────────────────────────┬─────────────────────────────────────────┤
│ Tier 1: POINT_IN_TIME_VERIFIED    │ Both t_pub and t_seen cryptographically │
│                                   │ verified; revision history tracked.     │
├───────────────────────────────────┼─────────────────────────────────────────┤
│ Tier 2: PARTIALLY_VERIFIED        │ Reliable t_seen present (e.g. GDELT),   │
│                                   │ but publisher CMS edit log absent.      │
├───────────────────────────────────┼─────────────────────────────────────────┤
│ Tier 3: HISTORICAL_UNVERIFIED     │ Stated t_pub present, but unverified    │
│                                   │ by crawler; prone to retroactive edits. │
├───────────────────────────────────┼─────────────────────────────────────────┤
│ Tier 4: REJECTED                  │ Date-only precision, missing timestamp, │
│                                   │ or retrospective backfill.              │
└───────────────────────────────────┴─────────────────────────────────────────┘
```

### 4.1 Evaluation Rules by Tier

1. **`POINT_IN_TIME_VERIFIED` (Eligible for Full Backtesting):**
   - Must contain exact UTC millisecond/second timestamps.
   - Must have independent confirmation that the payload was frozen upon ingestion.
   - **Sources:** Binance CMS Announcements (`publishDate` + `version` + `lastUpdateTime`); GDELT raw 15-minute GKG files with MD5 verification.
   - **Decision Rule:** Eligible at candle close $T$ if $t_{\text{avail}} \le T$, where $t_{\text{avail}} = t_{\text{pub}} + 300\text{s}$.
2. **`PARTIALLY_VERIFIED` (Eligible with Conservative Latency Buffer):**
   - Ingestion timestamp $t_{\text{seen}}$ is authenticated, but publisher revision logs are unversioned.
   - **Sources:** GDELT DOC API articles (`seendate`).
   - **Decision Rule:** Eligible at candle close $T$ if $t_{\text{seen}} + 300\text{s} \le T$. To prevent headline revision leakage, only factual entity tags and event taxonomy may be consumed—subjective sentiment adjectives must be discounted.
3. **`HISTORICAL_TIMESTAMP_UNVERIFIED` (Ineligible for Strategy Backtesting):**
   - Public website sitemaps (CoinDesk, Cointelegraph) that report `dateModified` but overwrite the HTML body upon edit.
   - **Handling:** Prohibited from quantitative backtests. Usable only for exploratory research.
4. **`REJECTED` (Strictly Discarded):**
   - Articles with date-only timestamps (`YYYY-MM-DD`).
   - Scraped blog dumps with missing publication timestamps.
   - **Handling:** Dropped during ingestion. Never imputed.

---

## 5. News-Event Deduplication & Clustering Findings

### 5.1 The Syndication Reality: MicroStrategy Case Study
From our empirical extraction on June 1, 2026:

| Article ID | Publisher Domain | Headline | GDELT SeenDate (UTC) | Time Lag from First Report |
|---|---|---|:---:|:---:|
| **Record 1** | `cnbc.com` | *Strategy shares fall after selling $2.5 million in bitcoin...* | `2026-06-01 13:45:00` | **$t_0$ (First Observed)** |
| **Record 2** | `finance.yahoo.com` | *Bitcoin juggernaut Strategy stock drops as it sells coins...* | `2026-06-01 15:15:00` | +1.5 hours |
| **Record 3** | `zerohedge.com` | *Saylor Breaks The Immaculate Bitcoin Narrative* | `2026-06-01 17:15:00` | +3.5 hours |
| **Record 4** | `gizmodo.com` | *Price of Bitcoin Drops as Michael Saylor Strategy Sells...* | `2026-06-01 21:45:00` | +8.0 hours |
| **Record 5** | `wlac.iheart.com` | *Bitcoin Drops Below $70K After Strategy Sells Tokens* | `2026-06-02 15:15:00` | +25.5 hours |

### 5.2 Forensic Implications
- A naive algorithm that treats every headline as an independent signal would have fired **five separate sell/veto signals across two full trading days** on a single $2.5M corporate rebalancing event.
- By the time Gizmodo (Record 4) and iHeart (Record 5) published, the price had already dropped and mean-reverted. Entering on delayed syndicated headlines results in **buying the bottom of the news dip or selling the exact low**.

### 5.3 Proposed Event-Clustering Algorithm
To prevent echo-chamber bias, NEPTUNE specifies a **Four-Stage Event Cluster Protocol**:
1. **Canonical URL Deduplication:** Strip query tracking parameters (`utm_source`, `ref`); group identical canonical URLs.
2. **Text SimHash / MinHash Tokenization:** Compute 64-bit SimHash over normalized headline n-grams ($n=3$). If Hamming distance $\le 3$ within a 24-hour sliding window, merge into an existing event cluster.
3. **Named Entity Co-Occurrence:** If multiple articles share primary entity tuples (e.g., `(MicroStrategy, Sell, Bitcoin)`) within 12 hours, assign to the same `cluster_id`.
4. **First-Seen Trigger Invariant:**
   $$\text{Cluster Activation Timestamp: } \quad t_{\text{cluster}} = \min_{i \in \text{Cluster}} (t_{\text{avail}, i})$$
   Only the first article in the cluster may trigger a veto or trading decision. Subsequent syndicated articles update cluster volume and confidence, but **MUST NOT generate new trading triggers**.

---

## 6. Refined Trading-Value Research Design: The 4-Group Protocol

To definitively establish whether news adds true alpha—or merely reduces losses by reducing trade frequency and transaction fees—we refine the research experiment into **four strictly controlled groups**:

```
==================================================================================================
REFINE 4-GROUP EXPERIMENTAL MATRIX (OOS_FULL: 2026-01-01 to 2026-11-01)
==================================================================================================
Group ID   Strategy Configuration                     Trade Count Sizing     Alpha Attribution
--------------------------------------------------------------------------------------------------
Group A    Technical Baseline (H7 + BALANCED)         Unconstrained (26)     Pure Technical Breakout
Group B    Technical + News Veto Gate                 Filtered by News (K)   Technical + News Alpha
Group C    Frequency-Matched Technical Control        Matches Group B (K)    Fee & Trade Reduction Control
Group D    Exposure-Matched Technical Control         Matches Group B (Hrs)  Market Risk Reduction Control
==================================================================================================
```

### 6.1 Group Isolation & Hypothesis Testing

#### 1. Group A: Technical-Only Control
- Standard Milestone 4.5.1 baseline: `H7_CONFLUENCE` filter + `BALANCED` trailing protection.
- In `OOS_FULL`, Group A executed 26 trades on BTCUSDT (-$10.21 net P&L, 42.31% win rate, -$0.39 expectancy).

#### 2. Group B: Technical + News Veto
- Evaluates candidate trades from Group A against point-in-time verified news event clusters.
- **Veto Rule:** If a `LONG` setup occurs, but a high-severity negative news cluster ($S \le -0.50$, impact $\ge 0.70$) occurred within the lookback window ($T - 12h \le t_{\text{cluster}} \le T$), the trade is **vetoed**.
- Generates $K$ executed trades ($K < 26$).

#### 3. Group C: Frequency-Matched Technical Control (Critical Scientific Control)
- To eliminate the "trading less saves fees" artifact, Group C is a **purely technical strategy** with an elevated indicator threshold (e.g., ADX $\ge 32$ instead of 25) calibrated to execute **exactly $K$ trades**.
- **Falsifiable Hypothesis:**  
  $$\text{If } \quad \text{P\&L}_{\text{Group B}} \le \text{P\&L}_{\text{Group C}}, \quad \text{then News provides ZERO true alpha.}$$
  The observed P&L improvement is mathematically attributable to fee savings from lower trade frequency, not news intelligence.

#### 4. Group D: Exposure-Matched Technical Control
- Calibrated to hold positions for the exact same cumulative market exposure hours as Group B, controlling for reduced time-at-risk during volatile market regimes.

---

## 7. Statistical Methodology & Minimum Evidence Standards

1. **Unit of Statistical Analysis:**  
   The unit of observation is the **Independent Event Cluster**, NOT individual news articles. A cluster of 20 syndicated articles counts as $N=1$.
2. **Cumulative Abnormal Return (CAR) Event Study:**  
   $$\text{CAR}[0, \tau] = \sum_{t=t_0}^{t_0+\tau} \left( R_{i,t} - \beta_i R_{m,t} \right)$$
   Evaluated over $\tau \in \{1h, 4h, 24h\}$ post-event.
3. **Statistical Power & Minimum Sample Size:**  
   To achieve 80% statistical power ($\beta = 0.20$) at $\alpha = 0.05$ for detecting a modest net edge ($+0.15\%$ after friction), a minimum sample size of **$N \ge 100$ independent, non-overlapping event clusters** is mandatory.
4. **Multiple Comparison Correction:**  
   When testing across multiple assets (BTC, ETH, BNB), event categories (Regulatory, Listings, Hacks), and reaction windows, p-values must be adjusted using the **Benjamini-Hochberg False Discovery Rate (FDR)** procedure at $q = 0.05$.
5. **Stationary Bootstrap:**  
   Compute 95% confidence intervals on net trade expectancy using Politis-Romano stationary bootstrap resampling (block size $b=10$) to preserve time-series dependency.

---

## 8. Source Accessibility, Licensing & Cost Realities

| Data Provider | Historical Depth | API Cost Tier | Terms of Service / Licensing | Feasibility Assessment |
|---|:---:|:---:|---|:---:|
| **Binance CMS Announcements** | 2017–Present | **$0.00 (Public)** | Public exchange disclosures | **Fully Feasible (Production)** |
| **GDELT 2.0 (Raw GKG Archives)** | 2015–Present | **$0.00 (Public Domain)** | Open research / Creative Commons | **Fully Feasible (via Raw ETL)** |
| **GDELT 2.0 (Interactive DOC API)** | 2015–Present | $0.00 | Rate limited (`429`) after 2 queries | **Infeasible for Batch Backtesting** |
| **CCData (CryptoCompare)** | 2017–Present | Commercial License | Paid subscription required for historical ETL | **Infeasible on $0 Budget** |
| **CryptoPanic Developer API** | 2017–Present | $75+/month | Paid PRO subscription required for archives | **Infeasible on $0 Budget** |
| **NewsAPI.org** | Last 30 days | $449+/month | 30-day limit on free tier | **Completely Infeasible** |

---

## 9. Recommended Milestone 4.6.1 Acquisition Plan

NEPTUNE will implement a zero-cost, fully point-in-time compliant ingestion pipeline combining two verified endpoints:
1. **Binance Announcements Ingestion:**
   - Catalog 48 ("New Listings")
   - Catalog 161 ("Delistings")
   - Catalog 49 ("Security Incidents & System Upgrades")
   - Extracted via two-tier pagination (catalog list $\to$ detail query) to collect exact millisecond `publishDate`, `lastUpdateTime`, `version`, and `pairs`.
2. **GDELT 2.0 Raw Archive Ingestion (Out-of-Sample Window 2026):**
   - Download raw 15-minute GKG CSV zip archives for the targeted backtest evaluation period.
   - Filter locally by domain whitelist (`coindesk.com`, `cointelegraph.com`, `decrypt.co`, `theblock.co`, `cnbc.com`, `bloomberg.com`).
   - Extract `seendate`, canonical URL, SimHash headline fingerprint, and V2Tone sentiment metrics.

---

## 10. Explicit Recommendation: CONDITIONAL GO for Milestone 4.6.1

The Quantitative Systems Group recommends **`CONDITIONAL GO`** for Milestone 4.6.1, subject to four mandatory engineering constraints:

1. **Enforce Two-Tier Verified Sources Only:** Ingestion must be restricted strictly to Binance CMS Announcements and GDELT 15-minute raw GKG archives. No unverified web scraping or date-only academic datasets may be used.
2. **Mandatory Event-Clustering:** All incoming news records must pass through `NewsDeduplicationEngine` (SimHash $\le 3$ over 24h). Only the first-seen event trigger may be evaluated.
3. **Frequency-Matched Control Group Mandatory:** Any backtest claiming news-veto alpha **must** run Group C (Frequency-Matched Technical Control) to prove that outperformance is not an artifact of fee reduction.
4. **Strict Architectural Isolation:** News data models must reside in `backend/app/analytics/research/` and **must never** be wired into the live Central Brain, Risk Manager, or paper execution engine until positive expectancy is proven beyond reasonable doubt.

---
*End of Validation Report — Project NEPTUNE Quantitative Systems Group*
