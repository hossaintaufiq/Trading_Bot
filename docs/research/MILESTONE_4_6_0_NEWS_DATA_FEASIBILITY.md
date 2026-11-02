# NEPTUNE Milestone 4.6.0 — Historical News Data Feasibility & Research Design

**Document ID:** `NEPTUNE-RESEARCH-4.6.0`  
**Date:** 2026-11-02  
**Status:** Feasibility Study & Research Proposal (Audit Baseline)  
**Author:** Project NEPTUNE Quantitative Systems Group  
**Target Milestone:** Milestone 4.6.0 (Feasibility & Architecture Design Only)  
**Starting Commit:** [`e480f8e`](file:///d:/Project%202026/Trading_bot) (Branch: `quant-expectancy-validation`, clean working tree)  
**Dataset Reference:** Frozen Historical Dataset `v2.0.0` (SHA-256: `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`)  

---

## 1. Executive Summary

### 1.1 Objective
This milestone evaluates the scientific and engineering feasibility of integrating timestamped historical news and event intelligence into NEPTUNE. The objective is to design a sound, falsifiable research architecture to answer the core quantitative question:

> **Core Research Question:**  
> *Can timestamped historical news and macro event data provide incremental predictive or economic value beyond NEPTUNE's deterministic technical-analysis baseline under realistic exchange execution friction?*

### 1.2 Core Feasibility Findings
1. **The Historical Data Availability Reality:**  
   Most commercial crypto news APIs (e.g., CryptoCompare/CCData, CryptoPanic, NewsAPI) enforce strict paywalls or restrict free tiers to recent articles (e.g., last 200 posts or last 30 days). Free endpoints either reject historical pagination (`HTTP 401/403`) or lack fine-grained, immutable point-in-time edit histories.
2. **The Revisionism & Look-Ahead Trap:**  
   Public financial websites frequently revise, update, or append breaking stories hours after initial publication without preserving version histories. Using unversioned scraped headlines creates severe look-ahead bias, as post-move journalistic commentary ("Bitcoin surges past $90k on ETF inflows") is retroactively backfilled as the "initial" headline.
3. **Execution Friction Domination:**  
   As established in Milestone 4.5.1, realistic Binance spot trading costs (**0.30% round-trip friction**: 0.10% maker, 0.10% taker, 0.05% slippage per side) submerge marginal informational edges. Any news-driven alpha must generate forward abnormal returns exceeding 0.30% to avoid capital erosion.
4. **Feasibility Verdict:** **`CONDITIONAL GO`**  
   News intelligence is feasible and scientifically valuable **only if** acquired through an authentic point-in-time source with explicit publication and ingestion timestamps ($t_{\text{pub}}$ and $t_{\text{avail}}$), coupled with a conservative publication latency buffer ($\ge 5$ minutes).

---

## 2. Repository & Baseline Architecture Inspection

### 2.1 Current Working State & Branch
- **Repository:** `NEPTUNE`
- **Active Branch:** `quant-expectancy-validation` (clean working tree, synced with `main` at `2606c92`)
- **Baseline Commit:** `e480f8e` (Milestone 4.5.1 forensic audit complete)
- **Monolith Boundaries:** Modular monolith using FastAPI (`backend/app/`), SQLite (`storage/db/neptune.db`), and Parquet storage (`storage/datasets/` and `storage/historical/`).

### 2.2 Baseline Research Foundation (`v2.0.0` & H7 Confluence)
- **Historical Depth:** Frozen dataset `v2.0.0` encompasses **394,716 validated closed candles** (34 contiguous months from 2024-01-01 to 2026-11-01) across BTCUSDT, ETHUSDT, and BNBUSDT on 15m, 1h, 4h, and 1d timeframes.
- **Authoritative Technical Baseline (Group A):**
  - Strategy: `H7_CONFLUENCE` entry filter (ADX $\ge 25$, EMA stack alignment, 4h trend agreement, VWAP deviation) with `BALANCED` trailing protection exit policy.
  - In `OOS_FULL` (2026-01-01 to 2026-11-01), Group A generated 26 executed trades (all on BTCUSDT), 11 wins (42.31% win rate), -$10.21 net P&L, and 3.23% max drawdown.
- **Existing News Infrastructure in Codebase:**
  - `docs/AGENT_SPECIFICATION.md` designates Agent 5 as `NewsAnalyst` (`news_analyst`), tasked with deterministic macro event scoring and calendar alerts with a $\le 5$ ms latency budget.
  - Currently, no historical news parser, database schema, or ingestion pipeline exists in `backend/app/`. News intelligence remains an isolated research frontier.

---

## 3. Comprehensive Historical News Source Evaluation

An empirical investigation was conducted across ten candidate historical crypto news providers to distinguish verified capabilities from assumptions.

### Detailed Source Profiles

#### 1. CryptoCompare / CCData News Min-API
- **Provider & URL:** CCData / CryptoCompare (`https://min-api.cryptocompare.com/data/v2/news/`)
- **Historical Coverage:** Archives exist back to ~2017.
- **Timestamp Metadata:** Unix epoch integer in seconds (`published_on`).
- **Update / Edit Timestamps:** Not supported. CMS updates overwrite the original record.
- **Verified Accessibility:** **Requires API Key.** Anonymous calls return `HTTP Error 401: Unauthorized`. Free registered tier permits recent news; bulk historical backfill across 34 months requires paid commercial data access.
- **Reproducibility:** High if paginated backwards via the `lTs` (lower timestamp) cursor, but historical articles are occasionally pruned by upstream feeds.

#### 2. CryptoPanic Developer API
- **Provider & URL:** CryptoPanic (`https://cryptopanic.com/api/v1/posts/`)
- **Historical Coverage:** Inception ~2017.
- **Timestamp Metadata:** ISO-8601 UTC string (`published_at`, `created_at`).
- **Content Provided:** Aggregated headlines, source domain, community bullish/bearish votes, and source link. Full article body is **not hosted**.
- **Verified Accessibility:** **Requires Auth Token.** Anonymous calls return `HTTP Error 403: Forbidden`. Free tier strictly restricts access to the **latest 200 posts**. Accessing the historical archive requires a paid "Developer PRO" subscription.

#### 3. GDELT Project 2.0 (Global Database of Events, Language, and Tone)
- **Provider & URL:** GDELT Project (`https://www.gdeltproject.org/`)
- **Historical Coverage:** Uninterrupted global coverage since February 2015 (15-minute update frequency); daily coverage back to 1979.
- **Timestamp Metadata:** 15-minute UTC ingestion timestamp (`YYYYMMDDHHMMSS`). Point-in-time integrity is guaranteed because records are frozen upon 15-minute file release.
- **Content Provided:** Global knowledge graph (GKG) themes, emotion/tone scores (`V2Tone`), entity tags, publisher domain, and URL. Full text is withheld due to copyright.
- **Verified Accessibility:** **100% Free and Publicly Queryable** via Google BigQuery (`gdelt-bq:gdeltv2.gkg`) or direct raw CSV download from Google Cloud Storage.
- **Known Limitations:** Extreme noise-to-signal ratio. Crawls global news, blogs, and press releases. Requires aggressive domain whitelisting (CoinDesk, Cointelegraph, Decrypt, The Block) and keyword filtering (`bitcoin`, `ethereum`, `bnb`).

#### 4. NewsAPI.org
- **Provider & URL:** NewsAPI (`https://newsapi.org/v2/everything`)
- **Historical Coverage:** 5+ years for paid tiers; **strictly last 30 days for free tier**.
- **Verified Accessibility:** Free API keys return errors if `from` date exceeds 30 days in the past. Commercial archive access costs **$449+/month**. Completely unusable on free research budgets.

#### 5. Alpha Vantage News & Sentiment API
- **Provider & URL:** Alpha Vantage (`https://www.alphavantage.co/query?function=NEWS_SENTIMENT`)
- **Historical Coverage:** Inception ~2022.
- **Timestamp Metadata:** UTC timestamp string (`YYYYMMDDTHHMMSS`).
- **Verified Accessibility:** Free API tier is limited to **25 calls per day** and restricts historical lookbacks to recent weeks. Bulk backtesting across 34 months is blocked on the free tier.

#### 6. CoinDesk & Cointelegraph Web Archives (Sitemaps / Scraping)
- **Provider & URL:** Public website sitemaps (`coindesk.com/sitemap.xml`, `cointelegraph.com/sitemap.xml`)
- **Historical Coverage:** 2013 to present.
- **Timestamp Metadata:** HTML metadata headers (`datePublished`, `dateModified`).
- **Verified Accessibility:** Public web. However, scraping violates Terms of Service, triggers Cloudflare anti-bot blocks, and presents severe **revision bias** (articles edited post-market without revision logs).

#### 7. Binance Official Announcements CMS API
- **Provider & URL:** Binance Public CMS (`https://www.binance.com/bapi/composite/v1/public/cms/article/catalog/list/query`)
- **Historical Coverage:** Complete history of Binance listings, delistings, forks, system maintenance, and regulatory updates since exchange launch (2017+).
- **Timestamp Metadata:** Millisecond Unix epoch timestamp (`releaseDate` / `publishDate`).
- **Verified Accessibility:** **100% Free, Public, Programmatically Accessible** without API keys.
- **Scope Limitation:** Restricted to Binance exchange operational events (highly relevant to BNB and Binance spot listings, but does not cover macro journalism).

#### 8. Hugging Face Open Academic Datasets (e.g., `ElKulako/cryptonews`)
- **Provider & URL:** Hugging Face Hub (`ElKulako/cryptonews`, `FinGPT-crypto`)
- **Historical Coverage:** 2021–2023 static snapshots.
- **Timestamp Metadata:** Frequently **date-only (`YYYY-MM-DD`)**, lacking intraday hour and minute timestamps.
- **Integrity Limitation:** Date-only precision creates unavoidable look-ahead bias when backtesting intraday (15m, 1h, 4h) strategies.

---

## 4. Source Accessibility & Licensing Matrix

| Provider | Earliest Date | Timestamp Precision | Edit History | Free Tier Historical Access | Cost Tier for 34-Mo Backtest | Commercial / Redistribution Rights | Point-in-Time Viability |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **CCData (CryptoCompare)** | 2017 | Seconds (UTC) | No (Overwrites) | Blocked (`401` Key Required) | Commercial API Tier | Commercial license required | Medium (Requires $t_{\text{avail}}$ lag) |
| **CryptoPanic** | 2017 | Seconds (UTC) | No | Latest 200 posts only (`403`) | Developer PRO ($75+/mo) | Non-commercial research | Medium (Headlines only) |
| **GDELT Project 2.0** | Feb 2015 | 15-min Ingestion | **Yes (Immutable Slices)** | **100% Free (BigQuery/GCS)** | **$0.00 (Public Domain)** | Open Public Domain | **High (True Point-in-Time)** |
| **NewsAPI.org** | 2019 | Seconds (UTC) | No | Last 30 days only | Business ($449/mo) | Commercial license required | Zero on Free Tier |
| **Alpha Vantage** | 2022 | Seconds (UTC) | No | 25 calls/day, recent only | Premium ($49+/mo) | API Terms restricted | Low |
| **CoinDesk Sitemap Scraping** | 2013 | Seconds (UTC) | Ambiguous | Scrape with ToS risk | $0 (High legal/ban risk) | Copyrighted content | **Unacceptable (Revision Bias)** |
| **Binance CMS Announcements** | 2017 | Milliseconds (UTC) | No | **100% Free & Open** | **$0.00** | Public exchange notices | **High (Exchange Events)** |
| **Academic Dumps (HF)** | 2021 | Date only (`YYYY-MM-DD`) | Static | 100% Free | $0.00 | Research only | **Unacceptable for Intraday** |

---

## 5. Recommended Dataset Acquisition Strategy

To satisfy NEPTUNE's strict standards of scientific integrity, no fabricated data, and zero look-ahead bias without incurring commercial API licensing costs, we recommend a **Two-Tier Hybrid Acquisition Strategy**:

```
                              ┌────────────────────────────────────────┐
                              │ NEPTUNE Two-Tier News Ingestion Engine │
                              └───────────────────┬────────────────────┘
                                                  │
                 ┌────────────────────────────────┴────────────────────────────────┐
                 ▼                                                                 ▼
   ┌───────────────────────────┐                                     ┌───────────────────────────┐
   │ Tier 1: Deterministic     │                                     │ Tier 2: Curated Editorial │
   │ Exchange & Macro Events   │                                     │ Sentiment Stream          │
   ├───────────────────────────┤                                     ├───────────────────────────┤
   │ - Binance CMS Announce-   │                                     │ - GDELT 2.0 BigQuery      │
   │   ments (listings/forks)  │                                     │   (Domain Whitelisted)    │
   │ - Macro Calendar Registry │                                     │ - Direct CCData/Crypto-   │
   │   (FOMC, CPI, Halving)    │                                     │   Panic Archive Export    │
   │ - 100% Point-in-Time      │                                     │ - Conservative Lag Buffer │
   │ - Millisecond UTC         │                                     │   (t_avail = t_pub + 5m)  │
   └─────────────┬─────────────┘                                     └─────────────┬─────────────┘
                 │                                                                 │
                 └────────────────────────────────┬────────────────────────────────┘
                                                  ▼
                                ┌───────────────────────────────────┐
                                │ Point-in-Time Parquet Partition   │
                                │ `storage/news/{YYYY}/{MM}.parquet`│
                                └───────────────────────────────────┘
```

1. **Tier 1 (Deterministic Operational & Macro Events):**
   - **Binance Official Announcements API:** Ingest all listing, delisting, token swap, and maintenance notices with millisecond timestamps.
   - **Macroeconomic Calendar Registry:** Static, authoritative historical schedule of FOMC interest rate announcements, CPI releases, and Bitcoin halving blocks with exact millisecond timestamps.
2. **Tier 2 (Broad Editorial Narrative Stream):**
   - **GDELT 2.0 Historical Extraction:** Query Google BigQuery public GDELT dataset for articles matching domain whitelists (`coindesk.com`, `cointelegraph.com`, `decrypt.co`, `theblock.co`) covering BTC, ETH, and BNB across 2024–2026.
   - **Verified Point-in-Time Assurance:** GDELT’s 15-minute batch timestamp serves as the immutable upper bound for $t_{\text{avail}}$.

---

## 6. Point-in-Time Data Integrity & Schema Specification

### 6.1 The Point-in-Time Invariant
To prevent look-ahead bias, financial simulations must differentiate between when an event occurred, when it was written, and when the trading system could have observed it:

```
t_event                     t_pub                     t_seen                     t_avail                 T_decision
   │                          │                          │                          │                        │
   ▼                          ▼                          ▼                          ▼                        ▼
[Real-world event] ──► [Journalist writes] ──► [Crawler scrapes] ──► [DB indexed & verified] ──► [Candle closes & trade evaluated]
```

$$\text{Simulation Eligibility Condition: } \quad t_{\text{avail}} \le T_{\text{decision}}$$

Where:
- $t_{\text{event}}$: Real-world occurrence time (e.g., SEC files an enforcement lawsuit).
- $t_{\text{pub}}$: Claimed publication timestamp reported in the article header.
- $t_{\text{seen}}$: Timestamp when NEPTUNE's scraper or aggregator first received the payload.
- $t_{\text{avail}}$: Earliest timestamp when the normalized article, entity tags, and sentiment score were indexed and available in local storage.
- $T_{\text{decision}}$: Close timestamp of candle $C_t$ at which an entry or exit decision is made.

> [!IMPORTANT]
> If an external provider only provides $t_{\text{pub}}$, the ingestion pipeline **MUST** enforce a conservative publication latency buffer:
> $$t_{\text{avail}} = t_{\text{pub}} + \Delta t_{\text{buffer}} \quad (\Delta t_{\text{buffer}} = 300 \text{ seconds / 5 minutes})$$
> An article published at 14:58:00 UTC cannot be consumed by a 15:00:00 UTC candle close unless $t_{\text{avail}} \le 15:00:00$.

### 6.2 Proposed Immutable News Record Schema

```python
class NewsArticleRecord(BaseModel):
    # Primary Identifiers & Cryptographic Provenance
    article_id: str                      # UUIDv5 generated from (source_id, canonical_url, published_at)
    source_id: str                       # e.g., "coindesk", "gdelt", "binance_cms"
    source_name: str                     # e.g., "CoinDesk", "Binance Announcements"
    canonical_url: str                   # Clean URL stripped of UTM tracking parameters
    raw_payload_hash: str                # SHA-256 hash of original raw JSON/HTML payload

    # Content & Narrative
    headline: str                        # Clean text headline
    summary: Optional[str]               # Lead paragraph / summary snippet
    full_text_hash: Optional[str]        # SHA-256 of body text (body withheld if copyrighted)

    # Point-in-Time Temporal Coordinates (Stored strictly in UTC)
    published_at: datetime               # Stated publisher timestamp (UTC)
    updated_at: Optional[datetime]       # Stated publisher revision timestamp (UTC)
    first_seen_at: datetime              # Earliest timestamp crawler observed the URL (UTC)
    available_at: datetime               # Point-in-time timestamp for backtest eligibility (UTC)

    # Entity Linking & Classification Metadata
    primary_asset: str                   # "BTC", "ETH", "BNB", or "CRYPTO_MARKET"
    asset_relevance_scores: Dict[str, float]  # {"BTC": 0.95, "ETH": 0.10}
    event_category: str                  # Taxonomy: "REGULATORY", "EXPLOIT", "MACRO", "LISTING", "FORK"
    sentiment_score: Decimal             # Deterministic score: -1.0000 to +1.0000
    impact_severity: Decimal             # Estimated magnitude: 0.0000 (routine) to 1.0000 (catastrophic)

    # Lineage & Model Versioning
    classifier_version: str              # Version of NLP/regex classifier used (e.g., "rule_v1.0.0")
    dataset_version: str                 # Dataset release tag (e.g., "news-v1.0.0")
```

### 6.3 Handling Critical Data Anomalies & Edge Cases

| Anomaly / Edge Case | Engineering Handling Protocol |
|---|---|
| **Missing Timestamps** | Discard record. Never impute or backfill missing publication timestamps. |
| **Conflicting Timestamps** | Set $t_{\text{avail}} = \max(t_{\text{pub}}, t_{\text{seen}}, t_{\text{updated}})$. Strict conservative ordering. |
| **Syndicated / Duplicate Articles** | Compute MinHash / SimHash on headlines. Group into clusters. Retain earliest $t_{\text{avail}}$ as canonical; flag others as `is_duplicate=True` to prevent echo-chamber double counting. |
| **Post-Publication Headline Edits** | If an updated version is detected with a different headline, create a **new version record** (`version=2`) with $t_{\text{avail}} = t_{\text{updated}}$. The backtest engine must strictly observe version 1 before $t_{\text{updated}}$. |
| **Deleted / Retracted Articles** | Retain article in historical archive. Append retraction record. Do NOT delete historical rows, as the market reacted to the initial publication before the retraction occurred. |
| **Source Feed Outages** | Record feed heartbeat gaps. The backtest engine must enter fail-safe neutral mode (`sentiment=0.0`) during documented feed blackouts. |

---

## 7. News Intelligence System Architecture

The proposed news subsystem integrates cleanly into NEPTUNE's modular monolith without introducing microservices, Redis, Kafka, or PostgreSQL.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           NEPTUNE Central Monolith                              │
│                                                                                 │
│   ┌───────────────────────┐         ┌───────────────────────┐                   │
│   │   Raw News Feeds      │         │ Macro Calendar & CMS  │                   │
│   └───────────┬───────────┘         └───────────┬───────────┘                   │
│               │                                 │                               │
│               ▼                                 ▼                               │
│   ┌─────────────────────────────────────────────────────────┐                   │
│   │                 NewsIngestionPipeline                   │                   │
│   │ - Timestamp standardizer (UTC)                          │                   │
│   │ - Payload SHA-256 hasher                                │                   │
│   └───────────────────────────┬─────────────────────────────┘                   │
│                               ▼                                                 │
│   ┌─────────────────────────────────────────────────────────┐                   │
│   │                 NewsDeduplicationEngine                 │                   │
│   │ - URL canonicalizer & SimHash cluster deduplicator      │                   │
│   └───────────────────────────┬─────────────────────────────┘                   │
│                               ▼                                                 │
│   ┌─────────────────────────────────────────────────────────┐                   │
│   │             DeterministicNewsClassifier                 │                   │
│   │ - Entity linker: Symbol mapping (BTC/ETH/BNB)           │                   │
│   │ - Taxonomy rule engine: Event classification            │                   │
│   │ - Deterministic sentiment proxy (lexicon / FinBERT)     │                   │
│   └───────────────────────────┬─────────────────────────────┘                   │
│                               ▼                                                 │
│   ┌─────────────────────────────────────────────────────────┐                   │
│   │                  NewsRepository (Parquet)               │                   │
│   │ - Partitioned: `storage/news/{symbol}/{YYYY-MM}.parquet`│                   │
│   │ - SQLite index: `storage/db/neptune.db`                 │                   │
│   └───────────────────────────┬─────────────────────────────┘                   │
│                               │                                                 │
│               ┌───────────────┴───────────────┐                                 │
│               ▼                               ▼                                 │
│   ┌───────────────────────┐       ┌───────────────────────┐                     │
│   │  HistoricalBacktest   │       │   NewsAnalyst Agent   │                     │
│   │  Event Study Engine   │       │   (Runtime Inference) │                     │
│   └───────────────────────┘       └───────────────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### Component Breakdown
1. **`NewsIngestionPipeline`:** Standardizes raw JSON feeds into `NewsArticleRecord`, converts all timestamps to UTC, and computes payload checksums.
2. **`NewsDeduplicationEngine`:** Eliminates redundant syndicated wire releases across outlets (e.g., identical AP/Reuters feeds republished on 10 crypto blogs).
3. **`DeterministicNewsClassifier`:**
   - **Entity Linking:** High-precision regex with contextual stop-words (e.g., matching "Ethereum" or "$ETH", while rejecting "method", "ethernet", or "beth").
   - **Event Classifier:** Deterministic keyword taxonomy mapping articles to discrete categories (`REGULATORY`, `EXPLOIT_HACK`, `ETF_FLOWS`, `EXCHANGE_LISTING`).
   - **Sentiment Scoring:** Calibrated lexicon/transformer model generating continuous scores in $[-1.0000, +1.0000]$.
4. **`NewsRepository`:** Stores historical articles in columnar Parquet format partitioned by month, indexed by SQLite table `historical_news`.

---

## 8. Four-Group Experimental Research Design

To isolate whether news data adds true incremental alpha, an empirical four-group ablation study is designed:

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

### 8.1 Group Specifications

#### Group A: Deterministic Technical Baseline
- **Strategy Logic:** Identical to Milestone 4.3.4 and 4.5.1 baseline: `H7_CONFLUENCE` filter + `BALANCED` exit policy.
- **Role:** Control group representing state-of-the-art technical filtering.

#### Group B: Pure News Strategy
- **Strategy Logic:** Evaluates candle-close news sentiment. If net news sentiment over the prior 4-hour window exceeds threshold ($|\bar{S}| \ge 0.60$) and impact severity $\ge 0.70$, enter paper position in direction of news. Fixed holding horizon of 4 bars (4 hours on 1h timeframe).
- **Role:** Measures whether standalone news sentiment can overcome 0.30% exchange friction.

#### Group C: Hybrid Technical + News Gating
- **Strategy Logic:** Generates candidates using Group A's technical engine. Before authorization:
  - **News Confirmation Rule:** If Group A signals `LONG`, and news sentiment is neutral to bullish ($S \ge -0.20$), approve trade.
  - **News Veto Rule:** If high-severity negative news ($S \le -0.50$, severity $\ge 0.70$) occurred within the last 12 hours, veto the `LONG` signal.
- **Role:** Tests whether news intelligence functions effectively as a **defensive risk veto**.

#### Group D: Quad-Model Hybrid (Technical + News + Kronos)
- **Strategy Logic:** Combines Group A candidates, Group C news vetoes, and Kronos directional forecast confirmation ($|\hat{r}| \ge 0.35\%$).
- **Role:** Comprehensive multi-modal quantitative study evaluating synergy between deterministic technicals, deep-learning time-series forecasting, and natural language sentiment.

### 8.2 Execution Assumptions & Cost Standardization (Rule A-10)
All four groups **MUST** run under identical execution friction:
- Initial Capital: **$1,000.00 USDT**
- Maker Fee: **0.10%** (`Decimal("0.001")`)
- Taker Fee: **0.10%** (`Decimal("0.001")`)
- Slippage: **0.05% per side** (`Decimal("0.0005")`)
- **Total Round-Trip Hurdle:** **0.30% of notional**
- Risk Manager Circuit Breaker: **5.0% Max Drawdown** strictly enforced via `RiskManager.check_drawdown()`.

---

## 9. Statistical Methodology & Predictive Evaluation

Predictive accuracy must be evaluated **separately** from trading performance to avoid confusing market beta or fee reduction with true alpha.

### 9.1 Predictive Metric: Cumulative Abnormal Returns (CAR)
For every high-impact news event $k$ at timestamp $t_0$, compute abnormal returns across multiple event windows $\tau \in \{[0, 1h], [0, 4h], [0, 24h]\}$:

$$AR_{i, t} = R_{i, t} - \beta_i R_{m, t}$$
$$CAR_i(\tau_1, \tau_2) = \sum_{t=\tau_1}^{\tau_2} AR_{i, t}$$

Where:
- $R_{i, t}$ is asset return (BTC, ETH, BNB).
- $R_{m, t}$ is benchmark crypto market index return.
- $\beta_i$ is asset market beta estimated over a 30-day pre-event window.

### 9.2 Statistical Hypothesis Testing
1. **Directional Sign Test:** Test whether positive news generates positive abnormal returns ($CAR > 0$) with binomial $p$-value against $H_0: p = 0.50$.
2. **Multiple Comparison Correction:** When testing across multiple assets, event categories, and reaction horizons, apply **Benjamini-Hochberg False Discovery Rate (FDR)** control at $\alpha = 0.05$.
3. **Bootstrap Confidence Intervals:** Compute 95% stationary bootstrap confidence intervals on mean trade expectancy and Sharpe ratio.
4. **Minimum Sample Size Requirement:** A minimum of **$N \ge 100$ independent, non-overlapping news events** is required before accepting any claim of statistical significance.

---

## 10. News-Specific Quantitative Risks & Biases

| Risk Category | Mechanism of Bias | Mitigation Strategy in NEPTUNE |
|---|---|---|
| **Revision Bias** | Publishers alter headlines or text after market moves without changing publication date. | Strict point-in-time timestamping ($t_{\text{avail}} = t_{\text{pub}} + 5\text{m}$); immutable payload hashing. |
| **Hindsight Headline Bias** | Reporters rationalize price action in headlines ("Bitcoin drops as Fed signals caution"). | Classify based on factual event type (e.g., "Fed Rate Decision") rather than subjective adjectives. |
| **Insider Front-Running** | Insiders trade ahead of public news releases; prices move *before* publication. | Measure pre-event price drift ($[-4h, 0]$); discard signals where $>70\%$ of move occurred before $t_{\text{pub}}$. |
| **Syndication Echo Chamber** | A single press release is republished across 50 outlets, creating false appearance of consensus. | SimHash deduplication clustering; count each news event cluster exactly once. |
| **Survivorship / Dead Outlets** | Small crypto news blogs shutter or delete old archives. | Restrict historical training to institutional-grade, continuously archived sources (GDELT, CCData, Binance). |
| **Fee Erosion Dominance** | Marginal news sentiment (+0.05% edge) is wiped out by 0.30% round-trip friction. | Use news as a **defensive veto filter** (pruning bad technical trades) rather than high-frequency entry trigger. |

---

## 11. Estimated Implementation Roadmap (Milestone 4.6.1+)

If this research feasibility report is approved, implementation will proceed in four isolated phases:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       Milestone 4.6 Implementation Roadmap                  │
├─────────────────┬───────────────────────────────────────────────────────────┤
│ Milestone 4.6.1 │ News Data Schema, SQLite Database Models, & Ingestion API │
│ Milestone 4.6.2 │ Historical Point-in-Time Data Collection & Parquet Export │
│ Milestone 4.6.3 │ Deterministic Entity Linking, Taxonomy, & Sentiment Model │
│ Milestone 4.6.4 │ Four-Group Comparative Backtest & Independent Audit       │
└─────────────────┴───────────────────────────────────────────────────────────┘
```

1. **Milestone 4.6.1:** Implement `NewsArticleRecord` Pydantic models, SQLite `historical_news` schema, and deterministic URL normalizer.
2. **Milestone 4.6.2:** Ingest and cryptographically verify historical news Parquet files for 2024–2026 matching dataset `v2.0.0`.
3. **Milestone 4.6.3:** Implement rule-based entity extraction and sentiment scoring with zero look-ahead leakage.
4. **Milestone 4.6.4:** Execute four-group economic backtesting across Groups A, B, C, and D under full Risk Manager governance.

---

## 12. Explicit Recommendation & Verdict

### Final Recommendation: **`CONDITIONAL GO`**

The Quantitative Systems Group recommends proceeding with **CONDITIONAL GO**, subject to four non-negotiable architectural constraints:

1. **Mandatory Point-in-Time Latency Buffer:** Every historical news record must enforce $t_{\text{avail}} \ge t_{\text{pub}} + 5\text{ minutes}$. No article may be backtested at its raw claimed publication second.
2. **Strict Invariant Isolation:** News intelligence must remain strictly within `backend/app/analytics/research/` during experimental validation. It **MUST NOT** be connected to the Central Brain, Risk Manager, or paper execution engine until positive expectancy is proven beyond reasonable doubt.
3. **Realistic Execution Friction (0.30%):** All economic simulations must incorporate the authoritative 0.30% round-trip cost model.
4. **Defensive Veto Orientation:** Focus quantitative hypothesis testing on whether news can act as a **defensive trade veto** (preventing trades ahead of high-volatility macro announcements), rather than attempting to predict directional breakout rallies from text sentiment.

---
*End of Feasibility Report — NEPTUNE Quantitative Systems Group*
