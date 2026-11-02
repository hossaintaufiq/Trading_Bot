# NEPTUNE — Milestone 4.6.2.1: Event Deduplication & Clustering Audit

**Document:** Forensic Audit of Event Clustering, SimHash Distance & Duplicate Resolution  
**Milestone:** 4.6.2.1 (Forensic Data Audit)  
**Evaluator:** Independent Audit Agent  
**Date:** 2026-11-03  
**Status:** COMPLETE — CLUSTERING VERIFIED (474 CLUSTERS / 5 CONFIRMED DUPLICATES)  

---

## 1. Executive Summary

This audit independently assesses the semantic deduplication engine implemented in Milestone 4.6.2.

When news events occur across multiple publishers or wire services, identical stories are repeatedly syndicated. If each syndicated article were treated as an independent trading signal, trading models would experience artificial signal compounding (cascading false order triggers).

### Key Audit Findings:
- **Total Articles Processed:** 479 articles.
- **Total Clusters Produced:** 474 clusters.
- **Duplicate Syndication Pairs Identified:** Exactly **5 clusters** contain multiple articles (2 articles each = 10 articles total).
- **Singletons:** Exactly **469 clusters** contain single articles.
- **Deduplication Precision:** **100%**. All 5 multi-article clusters were verified as true identical syndications of the same news event published by different media outlets on the same date.
- **Zero False Merges:** There were zero instances of distinct market events being erroneously merged into the same cluster.
- **Macro Calendar Isolation:** Per ADR-007, the 26 canonical macro calendar records are structurally isolated from article clusters to prevent noisy media headlines from corrupting economic release dates.

---

## 2. Clustering Architecture & Algorithmic Parameters

The deduplication pipeline in `backend/app/data/news/service.py` applies a two-stage filter:

```
[Candidate Article 1]           [Candidate Article 2]
         │                                │
         ├────────────────────────────────┤
         ▼                                ▼
[Stage 1: Temporal Filter]  |t1 - t2| <= 86,400s (24 Hours)
         │  (If False: DIFFERENT EVENTS)
         ▼
[Stage 2: Semantic Filter]  SimHash Distance(Title1, Title2) <= 3 bits
         │  (If True: DUPLICATE EVENT)
         ▼
[Cluster Assignment]        Add Article 2 to Article 1's Cluster
```

### Algorithmic Invariants:
1. **Temporal Gate:** Events separated by $> 24$ hours are never merged, even if their headlines are identical (e.g., recurring weekly posts like "Earn Wednesday" or monthly "Notice of Removal of Spot Trading Pairs").
2. **64-bit SimHash Metric:** Calculates locality-sensitive hashing across 3-gram character shingles of the normalized title. Hamming distance $\le 3$ indicates $\ge 90\%$ semantic similarity.

---

## 3. Forensic Inventory of Deduplicated Clusters

All 5 multi-article clusters from `storage/exports/milestone_4_6_2_1/cluster_reconciliation_inventory.csv` were inspected:

| Cluster ID | Title | Primary Symbol | Member 1 ID & Source | Member 2 ID & Source | SimHash Distance | Audit Verdict |
|:---|:---|:---:|:---|:---|:---:|:---:|
| `cl_0d5df535cc0de5e3` | Here's everything you need to know about Bitcoin ETFs: Listing, fees and more | `BTC` | `art_gdelt_77ad2aa5f63e2964`<br>(GDELT GKG) | `art_gdelt_fd5c31741b95a7d8`<br>(GDELT GKG) | 0 bits (Identical) | `TRUE_DUPLICATE_SYNDICATION` |
| `cl_527ffbb5d2562a6c` | New funds will make investing in bitcoin easier. Here's what you need to know | `BTC` | `art_gdelt_d4102dcc888bd50b`<br>(GDELT GKG) | `art_gdelt_e9ba8c65f11197c8`<br>(GDELT GKG) | 0 bits (Identical) | `TRUE_DUPLICATE_SYNDICATION` |
| `cl_7317ade1cc583c6b` | Spot Bitcoin ETF: Listing, fees and trading hours | `BTC` | `art_gdelt_2da4e77372c3d0df`<br>(GDELT GKG) | `art_gdelt_ecbe65ef0b9bb879`<br>(GDELT GKG) | 0 bits (Identical) | `TRUE_DUPLICATE_SYNDICATION` |
| `cl_9c46b58abc368493` | Bitcoin ETF Approval: Market Reaction and Impact | `BTC` | `art_gdelt_1cfab0d8df302ba2`<br>(GDELT GKG) | `art_gdelt_8ff65a2512fdbb34`<br>(GDELT GKG) | 1 bit | `TRUE_DUPLICATE_SYNDICATION` |
| `cl_9d7eefb890fe7616` | Bitcoin Spot ETF Approved: What You Need to Know | `BTC` | `art_gdelt_1a1e0eb762883f3e`<br>(GDELT GKG) | `art_gdelt_74a54c601d368e54`<br>(GDELT GKG) | 2 bits | `TRUE_DUPLICATE_SYNDICATION` |

### Hard Negative Evaluation:
- **Test Case: Recurring Announcements:**
  - `Earn Wednesday (2024-09-25)` vs `Earn Wednesday (2024-10-02)`:
  - Titles are nearly identical, but separated by 7 days.
  - **Result:** Correctly maintained as distinct single-article clusters due to the 24-hour temporal gate.
- **Test Case: Different Delisting Batches:**
  - `Notice of Removal of Spot Trading Pairs - 2024-05-17` vs `Notice of Removal of Spot Trading Pairs - 2024-06-21`:
  - **Result:** Correctly maintained as distinct clusters.

---

## 4. Deduplication Audit Conclusion

The clustering engine achieves high precision ($100\%$ on audit sample) without false merges. The mapping of 479 articles to 474 clusters is verified, deterministic, and safe for quantitative event clustering.

---
*End of Deduplication Audit Report.*

