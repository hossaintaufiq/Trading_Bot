# NEPTUNE — Milestone 4.6.3.0
# News-Veto Research Contract & Event Taxonomy Specification

**Milestone:** 4.6.3.0  
**Status:** FROZEN  
**Date:** 2026-11-06  
**Document Type:** Research Contract, Event Taxonomy & Invariant Specification  
**Governing Rules:** Rule S-05, Rule S-06, ADR-023, ADR-024, ADR-025, ADR-029  
**Classifier Engine Version:** `v1.1.0-deterministic`  

---

## 1. News-Veto Research Objective & Principles

The news-veto research layer serves a single bounded function in Group B:  
**To evaluate whether historically available adverse news events can filter out unprofitable technical candidate trades before order authorization.**

It is governed by strict negative-constraint principles:
1. **Asymmetric Veto Only:** The news layer can only veto a candidate trade. It can **never generate directional trade signals** and **never increase position sizing**.
2. **Subordination to Risk Manager (Rule S-04):** The news layer cannot override or bypass Risk Manager rejections. Risk Manager retains absolute authorization authority.
3. **Point-in-Time Immutability (Rule S-05):** An event can only veto a signal if it was historically available at or before the candle close decision timestamp ($T_{\text{avail}} \le T_{\text{decision\_cutoff}}$).
4. **Revision Isolation:** A subsequent article update, correction, or retraction recorded at $T > T_{\text{decision\_cutoff}}$ is strictly invisible at decision time.
5. **No Look-Ahead or Optimistic Buffering:** Missing timestamps are never inferred. A fixed 5-minute buffer is never assumed to prove availability.

---

## 2. Formal News-Veto Contract Schema

Every news item or macroeconomic release evaluated by Group B must conform to the `NewsVetoContract` Pydantic model (`backend/app/simulation/research_protocol.py`):

```python
class NewsVetoContract(BaseModel):
    contract_version: str = "v1.0.0-m4630"
    event_id: str                                    # Stable unique event ID
    cluster_id: Optional[str] = None                # Cluster ID for syndication deduplication
    event_category: EventCategory                    # 15-category taxonomy enum
    asset_relevance: RelevanceClassification         # 6-tier relevance enum
    is_direct_asset: bool                            # True = specific to pair; False = market-wide
    affected_assets: List[str]                       # Specific tickers (e.g. ["BTC", "ETH"])

    # Source & Reliability
    source_id: str                                   # binance_announcements, gdelt_gkg, bls, etc.
    source_reliability_score: float                  # 1.0 = official/exchange; 0.5 = aggregator

    # Exact Point-in-Time Temporal Coordinates (ISO 8601 UTC)
    original_publication_time: Optional[str] = None  # Official server publication timestamp
    first_observed_time: str                         # Earliest timestamp crawler indexed event
    collection_time: str                             # Timestamp record saved to local database
    availability_time: str                           # Effective decision cutoff timestamp
    revision_observation_time: Optional[str] = None  # Timestamp revision was recorded
    actual_macro_release_time: Optional[str] = None  # Bureau release timestamp (BLS, Fed)

    # Classification & Provenance
    classifier_version: str                          # Must be "v1.1.0-deterministic"
    classification_confidence: float                 # 0.0 to 1.0 confidence score
    provenance_status: SourceVerificationStatus      # POINT_IN_TIME_VERIFIED, etc.

    # Veto Evaluation & Exclusion
    is_veto_eligible: bool                           # True if passes all taxonomy & time rules
    explicit_exclusion_reason: Optional[str] = None  # Structured reason code if excluded
    adverse_impact_score: float                      # 0.0 = neutral/positive; 1.0 = severe adverse
    veto_decision: bool = False                      # True if event triggers trade veto
    veto_rationale: Optional[str] = None             # Explainable rationale for trade veto
```

---

## 3. Authoritative 13-Category Research Taxonomy

The research protocol establishes a 13-category event taxonomy governing eligibility and veto scope across assets and timeframes:

| ID | Category Name | Research Eligible | Affected Assets | Direct vs Market-Wide | Verified Pub Req | Intraday (15m-4h) Eligible | Adverse Veto Weight | Action / Rule Description |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **1** | **Exchange-wide operational incidents** | **YES** | All (`BTC`, `ETH`, `BNB`) | Market-Wide | **YES** (ms server) | **YES** | 0.85 | Wallet maintenance, scheduled upgrades. Vetoes all new entries across tracked pairs. |
| **2** | **Direct BTC events** | **YES** | `BTCUSDT` | Direct Asset | **YES** | **YES** | 0.90 | Protocol, legal, or major capital events directly affecting Bitcoin. Vetoes BTCUSDT entries. |
| **3** | **Direct ETH events** | **YES** | `ETHUSDT` | Direct Asset | **YES** | **YES** | 0.90 | Protocol, hard fork, or major events directly affecting Ethereum. Vetoes ETHUSDT entries. |
| **4** | **Direct BNB events** | **YES** | `BNBUSDT` | Direct Asset | **YES** | **YES** | 0.90 | BNB Chain, auto-burns, or native token regulatory actions. Vetoes BNBUSDT entries. |
| **5** | **Network & protocol incidents** | **YES** | Base asset or all | Direct / Market | **YES** | **YES** | 0.95 | Chain reorgs, RPC failures, node consensus bugs. Vetoes affected asset. |
| **6** | **Security exploits & vulnerabilities** | **YES** | Target asset or all | Market-Wide | **YES** | **YES** | 1.00 | Smart contract hacks, bridge drains, private key leaks. Immediate system-wide veto. |
| **7** | **Exchange outages & suspensions** | **YES** | All (`BTC`, `ETH`, `BNB`) | Market-Wide | **YES** | **YES** | 1.00 | Emergency withdrawal freezes, matching engine downtime. Mandatory immediate veto. |
| **8** | **Regulatory announcements** | **YES** | Specific or all | Direct / Market | **YES** | **YES** | 0.80 | SEC/CFTC/DOJ lawsuits, enforcement actions, bans, subpoenas. Vetoes directional risk. |
| **9** | **Macroeconomic releases** | **YES** | All (`BTC`, `ETH`, `BNB`) | Market-Wide | **YES** (BLS/Fed) | **YES** | 0.75 | FOMC rate decisions, US CPI, NFP with official timestamps. Vetoes during release window. |
| **10**| **ETF-related events** | **YES** | `BTCUSDT`, `ETHUSDT` | Direct Asset | **YES** | **YES** | 0.70 | 19b-4 / S-1 filings, ETF approvals, major net outflows. Vetoes longs on adverse outflow. |
| **11**| **Listings and delistings** | **PARTIAL** | `BNBUSDT` | Market Breadth | **YES** | **NO** (HTF only) | 0.30 | Catalog 48/161 altcoin notices. Ineligible for direct BTC/ETH; aggregate breadth sentiment only. |
| **12**| **General market commentary** | **NO** | None | Market-Wide | N/A | **NO** | 0.00 | **EXCLUDED:** Subjective opinion, unverified rumors, and retrospective commentary. |
| **13**| **Promotional content & marketing** | **NO** | None | Promotional | N/A | **NO** | 0.00 | **EXCLUDED:** Simple Earn, trading tournaments, giveaways, vouchers. Stripped by v1.1.0. |

---

## 4. Non-Negotiable Contract Invariant Rules

### Rule 1: Point-in-Time Cutoff Enforcement
An event record is eligible to veto a trade signal generated at candle close timestamp $T_{\text{close}}$ if and only if:
$$T_{\text{availability}} \le T_{\text{close}}$$
If $T_{\text{availability}} > T_{\text{close}}$, the event is rejected with structured reason:  
`EVENT_AVAILABLE_AFTER_DECISION_CUTOFF`.

### Rule 2: GDELT Intraday Prohibition
Under ADR-024 and Milestone 4.6.2.3 audit findings, GDELT Global Knowledge Graph records lack verified publisher timestamps and exhibit 15 to 120-minute crawler indexing latency.  
Therefore:
- GDELT records are **strictly prohibited** for intraday timeframes (`15m`, `1h`, `4h`).
- If evaluated for intraday timeframes, the contract emits:  
  `GDELT_SUB_DAILY_INTRADAY_PROHIBITED`.
- GDELT is restricted exclusively to exploratory daily (`1d`) analysis with a documented $+300\text{s}$ buffer.

### Rule 3: Provenance Verification & No Promotion
Records marked `REJECTED` or lacking official publisher/bureau timestamps are never promoted to verified status:
- Macro records require `first_observed_at` or `collected_at` provenance from authoritative government servers (`bls.gov`, `federalreserve.gov`, `sec.gov`). Missing provenance triggers:  
  `MISSING_REQUIRED_PROVENANCE`.
- Forward scheduled calendar entries ($> 2026-11-03\text{ UTC}$) are quarantined:  
  `FORWARD_SCHEDULED_EVENT_QUARANTINED`.

### Rule 4: Event Cluster Syndication Deduplication
Multiple syndicated articles reporting the same underlying event are clustered by SimHash and entity matching (`NewsEventCluster`).
- When evaluating adverse events, the engine tracks active `cluster_id`.
- Only the **earliest available article version** within a cluster is evaluated.
- Subsequent syndicated versions of the same cluster trigger:  
  `DUPLICATE_CLUSTER_MEMBER_<cluster_id>`.
- Syndicated duplicates are never counted as independent event occurrences.

### Rule 5: Separation of Unrelated Events
Unrelated events occurring within the same time window are never merged or conflated. Each distinct event maintains its own independent identity, classification evidence, and adverse impact scoring.
