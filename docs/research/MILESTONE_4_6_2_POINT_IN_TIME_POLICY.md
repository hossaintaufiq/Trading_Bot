# NEPTUNE — Milestone 4.6.2: Point-in-Time Data Policy & Temporal Coordinates

> **Document ID:** `DOC-RES-4.6.2-PIT`  
> **Milestone:** 4.6.2 — Historical News Backfill, Event Classification & Point-in-Time Dataset Construction  
> **Status:** APPROVED & BINDING  
> **Date:** 2026-11-03  
> **Governing Rules:** Rule S-05 (Absolute Look-Ahead Bias Prevention), Rule S-06 (Honesty in Data), ADR-023, ADR-024  
> **Temporal Engine:** [`temporal.py`](file:///d:/Project%202026/Trading_bot/backend/app/data/news/temporal.py)  

---

## 1. The Point-in-Time Imperative

In algorithmic trading research, the single greatest source of false profitability is **look-ahead bias** caused by improper temporal alignment of unstructured data. 

News articles present three acute point-in-time risks:
1. **Publication vs. Indexing Asynchrony:** An aggregator like GDELT captures articles minutes, hours, or days after publication. Using the aggregator's timestamp as the publication time misrepresents market reality.
2. **Post-Hoc Headline / Body Editing:** Media outlets routinely update headlines, add corrections, or revise facts hours after an initial break. Consuming a revised article as if it were available at the original release timestamp constitutes look-ahead bias.
3. **Observation Latency:** A news item published at `14:00:00 UTC` cannot be consumed by a strategy evaluating candle `14:00:00 UTC` if network latency, parsing delays, or indexing lag delayed receipt until `14:03:00 UTC`.

To prevent all forms of look-ahead leakage, NEPTUNE strictly enforces the **Multi-Coordinate Temporal Data Model**.

---

## 2. Multi-Coordinate Temporal Model

Every news record in NEPTUNE maintains seven distinct temporal coordinates in ISO-8601 UTC format:

| Coordinate Field | Definition & Semantic Grounding | Source Availability |
| :--- | :--- | :--- |
| `published_at` | Official publication timestamp certified by the publisher or agency release wire. | Present in Binance (`publishDate`) and Macro Registry; **NULL** in GDELT. |
| `provider_seen_at` | First timestamp at which the data provider or aggregator observed/indexed the item. | Present in GDELT (15-minute batch timestamp). |
| `archive_available_at` | Independently verified timestamp at which the raw archive file became public. | Derived from GDELT master file list release logs. |
| `first_seen_at` | Timestamp when NEPTUNE first encountered or registered the article record. | Recorded at ingestion runtime. |
| `collected_at` | Actual wall-clock timestamp of network retrieval. | Generated via `datetime.now(timezone.utc)`. |
| `updated_at` | Publisher-reported timestamp of last article revision or version bump. | Present in Binance (`lastUpdateTime`); **NULL** if unedited. |
| `research_available_at` | Conservative, defensible point-in-time boundary for research backtesting. | Computed via source-specific conservative latency buffers. |

```
Timeline of an Ingested News Event:

  14:00:00.000Z ─── published_at (Agency / Publisher release)
        │
        ▼ (Parsing & Network Transmission)
  14:02:15.000Z ─── provider_seen_at (GDELT / Aggregator batch detection)
        │
        ▼ (+300s conservative buffer)
  14:07:15.000Z ─── research_available_at (Earliest allowable strategy consumption)
        │
        ▼ (Engine Collection)
  14:15:00.000Z ─── collected_at (NEPTUNE ingestion checkpoint)
```

---

## 3. Strict Point-in-Time Eligibility Criterion

Governed by Rule S-05 and ADR-023:
> **An event record is eligible for candle consumption if and only if:**
> $$\text{research\_available\_at} \le \text{candle\_close\_timestamp}$$

Under no circumstances may an article be consumed in backtesting prior to its `research_available_at` coordinate.

### Source-Specific Buffer Rules:
1. **Binance Announcements (`POINT_IN_TIME_VERIFIED`):**
   - Timestamp is provided with millisecond precision directly from the exchange CMS (`publishDate`).
   - Conservative buffer: $+60\text{ seconds}$ to account for edge CDN cache propagation.
   - Eligible for backtesting down to 1-minute and 5-minute candle resolutions.
2. **Historical Macro Calendar (`POINT_IN_TIME_VERIFIED`):**
   - Official Federal Reserve, BLS, and SEC releases are scheduled and logged to the exact second.
   - Conservative buffer: $+30\text{ seconds}$ to account for wire dissemination.
   - Eligible for strict point-in-time backtesting.
3. **GDELT 2.0 Historical GKG (`PARTIALLY_VERIFIED`):**
   - Lacks verified publisher publication time; only 15-minute batch observation time (`provider_seen_at`) is available.
   - Conservative buffer: $+300\text{ seconds}$ (5 minutes) applied to the 15-minute batch window.
   - **Policy:** GDELT records are **EXCLUDED** from strict high-frequency point-in-time backtesting. They are restricted to exploratory, daily, or regime-level analysis where sub-hourly precision is not critical.

---

## 4. Verification Status Taxonomy

Every record carries an immutable verification status:

| Status Label | Criteria | Research Eligibility | Record Count |
| :--- | :--- | :--- | :--- |
| `POINT_IN_TIME_VERIFIED` | Millisecond or second precision timestamp certified by publisher or government agency. | Fully eligible for all backtesting and simulation models. | **439 records (86.9%)** |
| `PARTIALLY_VERIFIED` | Aggregator observation timestamp available with $\le 15$-minute resolution, but original publisher time unverified. | Eligible only for low-frequency/regime research; excluded from strict PIT backtests. | **66 records (13.1%)** |
| `HISTORICAL_TIMESTAMP_UNVERIFIED` | No valid observation or publication timestamp available. | Excluded from quantitative backtesting; retained for editorial audit. | **0 records (0.0%)** |
| `REJECTED` | Timestamps corrupted, future-dated, or failing sanity checks. | Discarded into quarantine log. | **0 records (0.0%)** |

---

## 5. Auditability and Immutable Versioning

If a publisher revises an article post-release (e.g., changes a delisting date or amends a statement):
1. The original version record in `news_article_versions` remains **completely immutable** (`version_number = 1`).
2. A new version record is created (`version_number = 2`) with the new payload, new payload SHA-256, and updated `collected_at` timestamp.
3. Historical backtests replaying candle periods prior to the revision's collection timestamp consume **only Version 1**. Version 2 is invisible to the time machine until its actual collection timestamp has passed.
