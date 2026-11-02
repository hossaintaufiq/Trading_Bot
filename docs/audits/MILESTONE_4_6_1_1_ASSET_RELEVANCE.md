# NEPTUNE — Milestone 4.6.1.1 Audit E: Asset Relevance
## Forensic Audit of Entity Extraction, Ticker Disambiguation & Semantic False Positives

> **Audit ID:** `AUD-4.6.1.1-ASSET`  
> **Date:** 2026-11-03  
> **Subject:** Cryptocurrency Entity Extraction & Symbol Resolution Logic  
> **Governing Standards:** Rule S-06, ADR-023

---

## 1. Executive Summary

This audit forensicly evaluates the asset-matching and entity-resolution logic implemented in `binance_client.py` and `gdelt_client.py`. Specifically, it examines whether:
1. Target assets (`BTC`, `ETH`, `BNB`) are accurately identified with sufficient evidence.
2. Exchange-wide announcements (e.g., hacks, regulatory actions, system upgrades) are conflated with native token events (e.g., BNB).
3. The catalog selection introduces systematic omission of core trading pairs.

### Core Audit Findings
1. **Catalog 48 Generates 0 Core Asset Signals:** All 60 Binance announcements were retrieved from Catalog 48 ("New Cryptocurrency Listing"). None of these articles correspond to BTC or ETH.
2. **Exchange vs. Native Token Conflation on BNB:** In GDELT GKG records, 5 of 6 articles were assigned to `BNB` solely because the word `binance` appeared in the headline or organizations column. All 5 articles discussed the **Binance $6.3B Hack and $4.7B Customer Outflow** crisis, an exchange-wide security event rather than a BNB token protocol announcement.
3. **Regex Disambiguation Verified:** The word-boundary regex `\b(ethereum|ether|eth|vitalik)\b` successfully prevented false positives from common English words like `whether`, `death`, or `tehran`.

---

## 2. Ingested Record Classification Census

Every record in the persisted dataset was audited against four semantic categories:

```
========================================================================================
ASSET CLASSIFICATION CENSUS (66 TOTAL PERSISTED ARTICLES)
========================================================================================
Category                    Binance Announcements     GDELT GKG Records     Total (%)
----------------------------------------------------------------------------------------
Direct Core Asset (BTC/ETH) 0                         1 (16.7%)             1  (1.5%)
Exchange-Wide Event (BNB)   0                         5 (83.3%)             5  (7.6%)
Other Altcoin Listing       60 (100.0%)               0                     60 (90.9%)
Ambiguous / Unclassified    0                         0                     0  (0.0%)
========================================================================================
Total Audited Records:      60                        6                     66 (100%)
========================================================================================
```

---

## 3. Forensic Case Studies

### Case Study 1: The BNB Entity Conflation Trap
- **Article ID:** `art_gdelt_72e1f88f83b4ffd2`
- **Headline:** *"Binance says customers pulled net $4.7 billion after hack"*
- **URL:** `https://www.businessinsurance.com/binance-says-customers-pulled-net-4-7-billion-after-hack/`
- **Assigned Entity:** `["BNB"]`
- **Evidence:** `CRYPTO_PATTERNS["BNB"] = re.compile(r"\b(binance|bnb)\b")` matched `binance`.
- **Audit Assessment:** 
  - This article describes exchange corporate insolvency risk and customer withdrawal runs.
  - While exchange solvency undeniably exerts downward pressure on BNB/USDT, it is an **exchange-wide macro shock**, not a BNB token utility event.
  - If a research strategy consumes this as a purely asset-specific signal, it risks misinterpreting exchange-level market contagion as token-level idiosyncratic volatility.

### Case Study 2: Altcoin Listing Saturation in Catalog 48
- **Article ID:** `art_binance_a276e9ff873c56d7`
- **Headline:** *"Binance Will Add 2 bStocks Tokenized Securities as Collateral Asset - 2026-09-09"*
- **Assigned Entity:** `[]`
- **Audit Assessment:**
  - Ingesting Catalog 48 yielded 60 announcements concerning obscure altcoin listings and tokenized equities.
  - None of these records provide actionable entry, exit, or regime veto signals for `BTCUSDT`, `ETHUSDT`, or `BNBUSDT`.
  - For NEPTUNE's core trading universe, Catalog 48 is irrelevant noise.

### Case Study 3: Direct BTC Narrative Match
- **Article ID:** `art_gdelt_fc4421989afa9fdb`
- **Headline:** *"Blockchain potential goes far beyond Bitcoin, says Bilal Bin Saqib"*
- **URL:** `https://en.dailypakistan.com.pk/02-Nov-2026/blockchain-potential-goes-far-beyond-bitcoin-says-bilal-bin-saqib`
- **Assigned Entity:** `["BTC"]`
- **Evidence:** Matched `bitcoin` in title.
- **Audit Assessment:**
  - The article is an opinion piece/interview discussing blockchain adoption.
  - While correctly tagged as BTC relevant, it possesses near-zero market-moving volatility information.

---

## 4. Recommendations for Milestone 4.6.2

1. **Split Entity Taxonomy into Two Distinct Tiers:**
   - `DIRECT_ASSET`: Specific to the token's network, protocol upgrades, halving, ETF inflows, or tokenomics (e.g. `BTC`, `ETH`).
   - `EXCHANGE_WIDE`: Exchange maintenance, regulatory enforcement, hacks, delistings, or collateral changes (e.g. `BINANCE_EXCHANGE`).
2. **Catalog Diversification for Binance:**
   - Ingest Catalog 49 ("Latest Binance News") and Catalog 161 ("Delisting") to capture direct pair maintenance announcements for BTC and ETH.
3. **Sentiment & Entity Grounding:**
   - Exclude generic op-eds and interviews that merely mention "Bitcoin" in passing without substantive macroeconomic or financial catalysts.

---
*End of Audit E — Project NEPTUNE Quantitative Systems Group*
