# NEPTUNE — Milestone 4.6.2.5: Risk Authorization & Cryptographic Token Audit

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Milestone:** 4.6.2.5  
**Topic:** Audit E — Cryptographic HMAC Risk Authorization Token Lifecycle & Pre-Fill Verification  
**Date:** 2026-11-03  
**Status:** Remediated & Cryptographically Verified  

---

## 1. Risk Manager Authority Mandate (Rule S-04)

Under NEPTUNE Persistent Engineering Rules (Rule S-04, docs/RISK_MANAGEMENT.md), all paper trading orders must be explicitly authorized by the **Risk Manager**. No other agent, scheduler, or execution simulator possesses the authority to create, size, or approve orders.

### 1.1 The Five Non-Negotiable Invariants
Every candidate signal must pass all 5 checks at the decision candle close:
1. **Daily Loss Limit Check ($2.0\%$):** Realized daily net P&L + open unrealized P&L cannot exceed $-2.0\%$ of daily starting equity.
2. **Drawdown Circuit Breaker ($5.0\%$):** Cumulative drawdown from peak equity cannot exceed $5.0\%$.
3. **Max Concurrent Positions ($2$):** Active open positions + pending scheduled orders cannot exceed 2.
4. **Asset Correlation Exposure ($1$ per asset):** Only 1 concurrent position permitted per symbol.
5. **Minimum Risk/Reward Ratio ($\ge 1.5:1$):** Reward distance to stop distance must satisfy $\text{RR} \ge 1.5$.

---

## 2. Forensic Vulnerability Discovery (F-4625-02)

During the Milestone 4.6.2.5 code inspection, a critical architectural gap was identified in the Milestone 4.6.2.4 token implementation:

1. **Unauthenticated Random UUIDs:**
   In [`backend/app/risk/risk_manager.py`](file:///d:/Project%202026/Trading_bot/backend/app/risk/risk_manager.py), tokens were issued as `f"rat_{uuid.uuid4().hex[:16]}"`. This token was a pseudo-random identifier rather than a cryptographic signature bound to the order's specific parameters.
2. **Missing Pre-Fill Verification:**
   [`PointInTimeExecutionScheduler`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/scheduling.py) queued orders and passed the token to [`PaperExecutionSimulator`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/execution.py) without verifying that the token was valid, untampered, or issued by the Risk Manager.
3. **Unsafe Fallback in Simulation Engine:**
   In [`HistoricalBacktestEngine`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/engine.py) (lines 553 and 574), orders were submitted with:
   ```python
   risk_approval_token=risk_eval.risk_approval_token or f"tok_{uuid.uuid4().hex[:8]}"
   ```
   This fallback permitted unauthenticated orders to bypass Risk Manager token issuance entirely if `risk_eval.risk_approval_token` was omitted.

---

## 3. Cryptographic HMAC-SHA256 Token Binding Architecture

To eliminate this vulnerability, a formal HMAC-SHA256 authorization contract was engineered:

### 3.1 Token Message Payload
The authorization token cryptographically binds 8 immutable execution coordinates:
$$\text{Payload} = \text{run\_id} \mathbin{\Vert} \text{signal\_id} \mathbin{\Vert} \text{symbol} \mathbin{\Vert} \text{direction} \mathbin{\Vert} \text{position\_size} \mathbin{\Vert} \text{entry\_price} \mathbin{\Vert} \text{stop\_loss} \mathbin{\Vert} \text{timestamp}$$

### 3.2 Token Generation
Using a secure secret key ($K_{\text{auth}}$):
$$\text{Digest} = \text{HMAC-SHA256}(K_{\text{auth}}, \text{Payload})[:24]$$
$$\text{Token} = \text{"rat\_v1\_"} \mathbin{\Vert} \text{Digest}$$

### 3.3 Token Verification
Before executing any fill at Bar $T+1$ Open, [`PointInTimeExecutionScheduler`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/scheduling.py) invokes `risk_manager.verify_risk_token(...)` using constant-time string comparison (`hmac.compare_digest`).

If any bound parameter has been altered (e.g. quantity inflated, stop loss narrowed, symbol substituted, or run ID mismatched), verification fails immediately, and the order is marked `OrderStatus.REJECTED` with:
$$\text{rejection\_reason} = \text{"Risk token verification failed: TOKEN\_SIGNATURE\_MISMATCH\_OR\_TAMPERED"}$$

Furthermore, the unsafe fallback in [`HistoricalBacktestEngine`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/engine.py) was completely eliminated. Any candidate signal lacking an authentic Risk Manager token is rejected prior to scheduling.

---

## 4. Adversarial Verification Matrix

The cryptographic token lifecycle was audited across 5 dedicated adversarial test scenarios:

| Test ID | Scenario | Injected Anomaly | Observed System Response | Status |
|---|---|---|---|---|
| **ADV-11** | Parameter Tampering | Position size inflated from $0.005$ to $1.0\text{ BTC}$ post-authorization | Scheduler detects signature mismatch; marks order `REJECTED` | **PASSED** |
| **ADV-12** | Token Replay | Authentic token from Signal A attached to Signal B | Scheduler detects signal ID mismatch; marks order `REJECTED` | **PASSED** |
| **ADV-13** | Cross-Run Replay | Token generated in `run_first` executed in `run_second` | Scheduler detects run ID mismatch; marks order `REJECTED` | **PASSED** |
| **ADV-14** | Circuit Breaker Trip | Drawdown breaches $5\%$ between decision and fill | Pre-fill check detects breach; cancels order before fill | **PASSED** |
| **ADV-17** | Duplicate Fill | Re-submitting already-filled order to scheduler | Scheduler removes order from pending queue; rejects re-fill | **PASSED** |

---

## 5. Key Management & Guarantees

1. **Key Isolation:** Simulation runs generate deterministic or environment-provided authentication keys (`auth_secret`). Keys are never logged or exposed in trade ledgers (Rule S-02).
2. **Replay Invariant:** Because the token binds `run_id` and `timestamp`, tokens cannot be replayed across different simulation runs or historical replay sessions.
3. **Execution Point Invariant:** The scheduler acts as an immutable enforcement proxy. The Risk Manager remains the sole authorization authority, and unauthenticated orders cannot reach the simulated exchange fill model.
