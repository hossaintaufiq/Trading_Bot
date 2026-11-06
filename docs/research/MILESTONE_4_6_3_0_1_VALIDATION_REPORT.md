# NEPTUNE — Milestone 4.6.3.0.1
## Research Protocol Integrity Audit & Leakage Verification Report

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Milestone:** 4.6.3.0.1  
**Audit Date:** 2026-11-06  
**Auditor:** Quantitative Audit Agent  
**Starting Baseline:** Milestone 4.6.3.0 (`56af6a9`)  
**Current Branch:** `quant-expectancy-validation`  
**Governing Rules:** Rule S-01, Rule S-04, Rule S-05, Rule S-06, ADR-028, ADR-029, ADR-030  

---

## 1. Authoritative Audit Verdict

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FINAL AUDIT VERDICT:                            │
│                        PASS WITH LIMITATIONS                           │
└────────────────────────────────────────────────────────────────────────┘
```

The experimental protocol established in Milestone 4.6.3.0, as remediated and fortified in Milestone 4.6.3.0.1, is **APPROVED FOR EXPERIMENTAL EXECUTION** strictly under the operational boundaries specified below.

---

## 2. Forensic Audit Summary

| Component | Audit Status | Key Remediation |
|-----------|--------------|-----------------|
| **Group A (Technical Baseline)** | **VERIFIED** | Baseline parameters frozen with reproducible SHA-256 fingerprint `33a5d9f67052fe25737e8e93011230462ab2250e1984395f2d69214f445f1278`. |
| **Group B (News-Veto)** | **VERIFIED** | Executable [`NewsVetoDecisionEngine`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py) implemented with pre-registered decay windows (2h to 24h), adverse threshold $\theta = 0.70$, cluster deduplication, and revision cutoff isolation. |
| **Group C (Frequency Control)** | **REMEDIATED & VERIFIED** | Batch decimation labeled as `EX_POST_DIAGNOSTIC`. [`OnlineFrequencyMatchingEngine`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py) implemented for online point-in-time thinning using pre-registered rate $\rho_{\text{calib}}$. |
| **Group D (Exposure Control)** | **REMEDIATED & VERIFIED** | Conflation of trade count and exposure resolved via 7-dimensional model [`ExposureDimensions`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py). [`OnlineExposureMatchingEngine`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py) implemented for dynamic cooldown. |
| **Statistical Analysis Plan** | **REMEDIATED & VERIFIED** | Bootstrap block sizes calibrated to ~4 calendar days across all timeframes (15m: 384, 1h: 96, 4h: 24, 1d: 7 bars). Denominators separated ($E_{\text{trade}}$ vs $E_{\text{cand}}$ vs $R_{\text{portfolio}}$). |
| **Out-of-Sample Guard** | **FORTIFIED & VERIFIED** | Programmatic [`OOSAccessGuard`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py) implemented, raising `PermissionError` on unauthorized access to Jan-Oct 2026 data. |

---

## 3. Operational Boundaries & Strict Constraints

Milestone 4.6.3 simulation runs must comply with the following mandatory operational constraints:

1. **Online Simulation Rule:** When running streaming or candle-by-candle simulations, Group C and Group D must execute using `OnlineFrequencyMatchingEngine` and `OnlineExposureMatchingEngine`. Ex-post matching methods must only be computed after simulation finalization as diagnostic controls.
2. **Locked OOS Access Boundary:** No simulation or data query covering dates between `2026-01-01` and `2026-10-31` may be executed without formal, signed HMAC governance authorization. All protocol tuning and exploratory tests must remain strictly within the Development (2023-12-01 to 2025-06-30) and Validation (2025-07-01 to 2025-12-31) partitions.
3. **News Signal Boundary:** News intelligence is strictly confined to candidate setup vetoes. Under no circumstances may news data generate directional entry signals or alter risk limits.
4. **Risk Manager Authority:** The Risk Manager agent remains the sole and final order authorization authority. No news veto or control matching rule can authorize an order that the Risk Manager rejected.
5. **Reported Metrics Integrity:** All research publications and reports must present both $E_{\text{trade}}$ and $E_{\text{cand}}$ side-by-side, along with the full 7-dimensional exposure comparison.

---

## 4. Cryptographic State & Reproducibility Hashes

- Market Dataset v2.0.0 Tree Hash: `b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c`
- News Dataset v2.0.0 Manifest Hash: `6b7bb69c841ec9a5e1774b6f369c0d9c113df066d80357521ac92b937490f4ec`
- Frozen Technical Baseline Fingerprint: `33a5d9f67052fe25737e8e93011230462ab2250e1984395f2d69214f445f1278`
- Research Protocol Version: `v1.1.0-m46301`
- Backend Tests Passing: 280 / 280 (100%)
- Adversarial Tests Passing: 18 / 18 (100%)
- Frontend Tests Passing: 4 / 4 (100%)
- Frontend Production Build: 0 errors
