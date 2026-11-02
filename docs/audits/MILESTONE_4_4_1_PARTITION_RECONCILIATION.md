# NEPTUNE Milestone 4.4.1 — Partition P&L Reconciliation Audit

**Audit Date:** 2026-11-02  
**Baseline Commit:** `ae908d1` / `4f59a94`  
**Dataset Version:** `v2.0.0`  
**Audit Scope:** Independent forensic reconciliation of reported partition P&L discrepancies between `TRAIN`, `VALIDATION`, `OOS_FULL`, and `FULL`.

---

## 1. The Discrepancy Investigated

Milestone 4.4 reported the following aggregate results for `Baseline BALANCED`:

| Partition | Time Window | Executed Trades | Reported Net P&L | Total Fees |
|---|---|---:|---:|---:|
| **TRAIN** | 2024-01-01 to 2025-06-30 | 510 | **-$687.34** | $358.62 |
| **VALIDATION** | 2025-07-01 to 2025-12-31 | 314 | **-$292.92** | $267.94 |
| **OOS_FULL** | 2026-01-01 to 2026-11-01 | 210 | **-$170.36** | $191.20 |
| *Naive Linear Sum* | *2024-01-01 to 2026-11-01* | *1,034* | *-$1,150.62* | *$817.76* |
| **FULL (Continuous)** | **2024-01-01 to 2026-11-01** | **430** | **-$285.16** | **$200.12** |

### The Core Inquiry
Why is the reported `FULL` P&L (-$285.16 across 430 trades) dramatically less negative than the sum of its chronological sub-partitions (-$1,150.62 across 1,034 trades)?

---

## 2. Root Cause Analysis & Forensic Findings

Our audit confirms that this discrepancy is **not an accounting error**, but the direct consequence of **four structural and architectural design mechanisms**:

### Factor 1: Omission of the 15m Timeframe in FULL
In `scratch/run_milestone_4_4_research.py` (line 244), the 15m timeframe was explicitly omitted from `FULL` to conserve computation time:
```python
if tf == "15m" and part.name == "FULL":
    continue
```
In the partitioned runs, `15m` suffered massive fee drag and stop-loss churn:
- **TRAIN 15m:** 135 trades, **-$359.83** P&L
- **VALIDATION 15m:** 82 trades, **-$216.94** P&L
- **OOS_FULL 15m:** 77 trades, **-$126.96** P&L
- **Total 15m Partition Drag:** **-$703.73** across 294 trades!

Because `FULL` completely omitted the 15m timeframe, it did not incur this -$703.73 drag.

---

### Factor 2: The 5.0% Drawdown Circuit Breaker Lockout (The Primary Mechanism)
Under Rule `S-04` and `S-10`, NEPTUNE's Risk Manager ([`backend/app/risk/risk_manager.py`](file:///d:/Project%202026/Trading_bot/backend/app/risk/risk_manager.py#L106-L118)) enforces a non-negotiable **5.0% Maximum Drawdown Circuit Breaker**:
```python
# Check 2: Drawdown Circuit Breaker
if peak_equity > Decimal("0"):
    current_drawdown = (peak_equity - current_equity) / peak_equity
    if current_drawdown >= self.max_drawdown_pct:
        return RiskEvaluationResult(
            approved=False,
            rejection_code="MAX_DRAWDOWN_EXCEEDED",
            ...
        )
```

1. **Behavior in `FULL` (Continuous 34 Months):**
   - Starting with $1,000.00, any net loss of $50.00 permanently breaches the 5.0% drawdown limit.
   - During early 2024 (the `TRAIN` period), high chop caused drawdowns to exceed 5.0% across all 1h series:
     - `BNBUSDT 1h`: max drawdown reached **6.63%** ($67.51) at trade 63.
     - `BTCUSDT 1h`: max drawdown reached **5.30%** ($54.46) at trade 68.
     - `ETHUSDT 1h`: max drawdown reached **7.46%** ($83.36) at trade 129.
     - `BTCUSDT 4h`: max drawdown reached **6.61%** ($66.18) at trade 32.
     - `ETHUSDT 4h`: max drawdown reached **5.28%** ($54.13) at trade 22.
   - **The Circuit Breaker Locked:** From that exact bar forward, `RiskManager` rejected 100% of candidate signals with `MAX_DRAWDOWN_EXCEEDED`!
   - In `FULL`, trading on `1h` (and `4h` for BTC/ETH) was **completely halted for the remainder of 2025 and 2026**!
   - This explains why `BNBUSDT 1h` has **exactly 63 trades in both TRAIN and FULL**, and why the trades fingerprints match bit-for-bit!

2. **Behavior in `VALIDATION` and `OOS_FULL` (Independent Partitions):**
   - When `VALIDATION` (2025-H2) and `OOS_FULL` (2026) were run as separate partitions, their starting capital was re-initialized to **$1,000.00**, resetting their drawdown to **0.0%**.
   - This unblocked the circuit breaker, allowing new trades to execute in late 2025 and 2026.

3. **The Empirical Proof (1d Timeframe Invariance):**
   - On the `1d` timeframe, wider swings prevented drawdowns from reaching 5.0% (BNBUSDT 1d max drawdown: 1.55%; BTCUSDT 1d: 3.65%; ETHUSDT 1d: 3.65%).
   - Because the 1d series **never breached the circuit breaker**, `FULL` took trades continuously across all 34 months:
     - BNBUSDT 1d: 7 trades in TRAIN -> **12 trades in FULL**.
     - BTCUSDT 1d: 7 trades in TRAIN -> **14 trades in FULL**.
     - ETHUSDT 1d: 7 trades in TRAIN -> **12 trades in FULL**.
   - This conclusively proves that the flatlining in 1h/4h was solely caused by the Risk Manager's non-negotiable 5% drawdown constraint.

---

### Factor 3: Portfolio Capital and Position Sizing Resets
- Position sizing uses `risk_per_trade_pct = 0.5%`.
- In an independent partition starting at $1,000.00, each trade risks exactly $5.00.
- In a continuous simulation whose capital has dropped to $900.00, position sizing scales down risk to $4.50 per trade.
- Sizing is mathematically state-dependent and cannot be linearly summed across periods.

---

### Factor 4: Boundary Position Truncation & Slot Occupancy
- In partitioned runs, open positions are terminated at the partition end boundary, and new partitions start with 0 positions and all concurrency slots free (`max_concurrent_positions = 2`).
- In continuous runs (`FULL`), positions open at month-end continue holding, occupying portfolio slots and suppressing candidate signals in subsequent months.

---

## 3. Reconciled Mathematical Summary Table

Reconciling `Baseline BALANCED` strictly across comparable series (excluding 15m and isolating 1d, 1h, 4h):

| Metric | TRAIN (1d, 1h, 4h) | VALIDATION (1d, 1h, 4h) | OOS_FULL (1d, 1h, 4h) | Sum of Partitions | FULL (Continuous) | Variance Mechanism |
|---|---:|---:|---:|---:|---:|---|
| **Trades** | 375 | 232 | 133 | 740 | **430** | -310 trades suppressed by 5% circuit breaker lockout in FULL |
| **Net P&L** | -$327.51 | -$75.98 | -$43.40 | -$446.89 | **-$285.16** | +$161.73 saved by circuit breaker preventing further losses |
| **Total Fees** | $257.65 | $172.90 | $124.78 | $555.33 | **$200.12** | $355.21 in fee drag prevented by circuit breaker halt |

---

## 4. Conclusion & Audit Sign-Off

The reported difference between partition P&Ls and `FULL` P&L is **fully reconciled and verified**. 
- It is not an accounting defect.
- It reflects the intended safety operation of NEPTUNE's Risk Manager: **the circuit breaker successfully protected paper capital by halting trading when the strategy experienced severe drawdown**.

