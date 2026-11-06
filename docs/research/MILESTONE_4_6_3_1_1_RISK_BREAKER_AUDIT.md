# NEPTUNE — Milestone 4.6.3.1.1
## Risk-Breaker Verification, Circuit Breakers & Drawdown Overshoot Audit

**Document:** Risk Invariant Audit & Circuit Breaker Timeline  
**Audit Target:** Milestone 4.6.3.1 Risk Manager & Circuit Breakers  
**Artifact Link:** [`risk_breaker_timeline.json`](file:///d:/Project%202026/Trading_bot/storage/exports/milestone_4_6_3_1_1/risk_breaker_timeline.json)  

---

## 1. Audit Mandate & The 5% Circuit Breaker Invariant

Under Rule S-04 and the frozen baseline protocol (ADR-029, ADR-030):
- **Maximum Drawdown Circuit Breaker:** Configured at **5.0%** (`max_drawdown_pct = 0.05`).
- **Daily Simulated Loss Limit:** Configured at **2.0%** (`daily_loss_limit_pct = 0.02`).

The original Milestone 4.6.3.1 report stated:
- Group A: 5.19% maximum drawdown.
- Group B: 5.38% maximum drawdown.
- Group C: 5.92% maximum drawdown.
- Group D: 5.79% maximum drawdown.

The audit mandate was to determine:
1. Why reported drawdowns exceeded the 5.0% configured threshold.
2. What the circuit breaker actually governs (intrabar vs closed-candle, order approval vs forced liquidation).
3. How the portfolio cash-equity defect impacted risk evaluations during 2024.

---

## 2. Risk Manager Implementation Architecture

Inspection of `backend/app/risk/risk_manager.py` ([lines 755–780](file:///d:/Project%202026/Trading_bot/backend/app/risk/risk_manager.py#L755-L780)) reveals the exact mechanics of the circuit breaker:

```python
# Check 2: Drawdown Circuit Breaker
if peak_equity > Decimal("0"):
    current_drawdown = (peak_equity - current_equity) / peak_equity
    if current_drawdown >= self.max_drawdown_pct:
        return RiskEvaluationResult(
            approved=False,
            rejection_code="MAX_DRAWDOWN_EXCEEDED",
            rejection_reason=f"Drawdown circuit breaker active: {current_drawdown:.4f} >= {self.max_drawdown_pct:.4f}",
            evaluated_checks=checks,
        )
```

### Critical Findings on Breaker Governance:
1. **The Circuit Breaker Rejects NEW Orders Only:** The Risk Manager is an authorization engine for proposed trade candidates. It does NOT force-close or liquidate existing active positions.
2. **Intrabar & Closed-Candle Overshoot is Normal & Expected:** If a portfolio is at 4.8% drawdown, a new trade may be approved. If that trade subsequently hits its stop loss, the realized drawdown can naturally expand from 4.8% to 5.19% or 5.38%. This is an expected operational characteristic of non-liquidation order-gate breakers.

---

## 3. The Critical Cash Equity Distortion on Risk Evaluations

While the minor overshoot (5.19% to 5.92%) is an expected characteristic of order gates, the forensic audit uncovered a far deeper, structural risk failure:

### Flawed Reported Equity vs True Realized Equity

| Group | Configured Breaker Limit | Flawed Reported Max Drawdown | True Realized Max Drawdown | True 5% Breach Date | Trades Before Breach | Trades After Breach |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Group A** | 5.0% | 5.19% | **24.87%** | **2024-01-05 09:00 UTC** | 8 | 60 |
| **Group B** | 5.0% | 5.38% | **13.95%** | **2024-01-05 20:45 UTC** | 7 | 40 |
| **Group C** | 5.0% | 5.92% | **22.13%** | **2024-01-05 20:45 UTC** | 8 | 54 |
| **Group D** | 5.0% | 5.79% | **20.04%** | **2024-01-05 20:45 UTC** | 8 | 52 |

### Root Cause Analysis:
1. **The Phantom Cash Buoyancy:** In `development_orchestrator.py`, the `current_equity` passed into `risk_manager.evaluate_signal` was `cash_equity + open_val`. Because `cash_equity` had the inverted short accounting bug, losing short trades credited cash, keeping `total_equity` falsely hovering around $950–$1000 throughout 2024.
2. **The Result:** The Risk Manager was evaluating an artificially inflated equity balance!
3. **The True Reality:** In true cumulative accounting, Group A lost -$51.15 by **January 5, 2024 (Trade #8)**, crossing the 5.0% circuit breaker permanently. Had the Risk Manager received true realized equity, **it would have halted all trading permanently on January 5, 2024**, preventing the subsequent 60 losing trades!

```
True Equity vs Reported Equity Trajectory (Group A)
1000 ──┐
       │ (Jan 5: True 5% Breaker Breached)
 950 ──┼────────────────── Reported Flawed Equity (Hovered at ~5.19% DD via short phantom cash)
 900 ──┼───────────┐
 850 ──┤           └──────────────┐
 800 ──┤                          └───────────┐
 785 ──┴──────────────────────────────────────┴── True Ending Equity ($785.28, 24.87% Max DD)
      Jan 2024                               Dec 2024
```

---

## 4. Candidate Veto & Execution Stream Reconciliation

The audit investigated how **183 news-veto decisions** translated into a difference of **21 executed trades** between Group A (68) and Group B (47).

### Forensic Breakdown of the 183 Vetoes

$$\text{Total Candidates Emitted} = 3,678, \quad \text{Total News Vetoes} = 183$$

1. **Vetoes Directly Preventing Trades: 5 (2.73%)**
   - Only 5 candidate setups vetoed by news were actually executable and became trades in Group A.
   - These 5 trades in Group A generated -$18.23 USDT net PnL.
2. **Redundant Vetoes: 178 (97.27%)**
   - 178 vetoed setups were completely redundant; even without the news veto, they would have been rejected by the Risk Manager due to max concurrent position limits (2 max concurrent), daily loss limits, or existing open positions.
   - Calling 183 news vetoes "183 prevented trades" is factually incorrect; **only 5 trades were directly prevented**.

### Portfolio Path Dependency Reconciliation ($23 - 2 = 21$)

The 21-trade difference between Group A (68) and Group B (47) reconciles as follows:

| Component | Trade Count | Explanation |
|---|:---:|---|
| **Common Trades** | 45 | Executed in both Group A and Group B |
| **Trades in Group A Only (Direct Veto)** | **5** | Technical setups vetoed by news in Group B |
| **Trades in Group A Only (State Divergence)** | **18** | Executed in Group A, but Group B was busy in a different trade due to diverging holding timelines |
| **Trades in Group B Only (State Divergence)** | **2** | Executed in Group B, but Group A was full (at 2 concurrent positions) and could not enter |
| **Net Trade Difference ($A - B$)** | **21** | $(5 + 18) - 2 = 23 - 2 = \mathbf{21\text{ trades}}$ |

---

## 5. Audit Conclusions & Governance Implications

1. **Breaker Invariant Preserved in Logic, Bypassed in State:** The Risk Manager correctly rejected orders when its input equity exceeded 5% drawdown. However, the input equity was distorted by the cash-accounting defect.
2. **Strategy Viability Defect Confirmed:** Far from being near breakeven (-1.54% return), the frozen technical strategy suffered an uncontrolled **-21.47% loss (24.87% drawdown)**.
3. **News Veto Ineffectiveness Confirmed:** Even when accounting for path dependency, news vetoing only directly altered 5 trades and reduced true drawdown from 24.87% to 13.95% solely by acting as an uncalibrated volume dampener.

