# NEPTUNE — Milestone 4.3.4: Full-Precision Accounting Verification

**Document Version**: 1.0.0  
**Audit Target**: Mathematical Precision, Quantization Mechanics & Discrepancy Reconciliation  
**Auditor**: Independent Quantitative System Auditor  
**Date**: 2026-11-02  
**Starting Commit Baseline**: `c1ffe20`  
**Governing Rules**: `AGENTS.md` (A-01 Python Decimal Mandatory, A-10 Execution Assumptions, S-06 No Fabrication)  

---

## 1. Executive Summary

This audit performs an independent, full-precision reconciliation of all monetary calculations across all 12 authoritative backtest event ledgers. 

The investigation conclusively resolves why small discrepancies exist between reported Net Realized PnL and the sum of displayed components:
- **Baseline BALANCED**: -$0.08 discrepancy (-$340.22 vs -$340.14).
- **H7 BALANCED**: -$0.01 discrepancy (+$14.02 vs +$14.03).
- **H7 FIXED_BRACKET**: -$0.14 discrepancy (-$5.59 vs -$5.45).
- **H1b BALANCED**: +$0.14 discrepancy (-$183.46 vs -$183.60).

### Core Finding:
The NEPTUNE execution simulator computes all monetary values internally using unrounded Python `Decimal` objects. In raw unquantized Decimal space, the accounting identity $\text{Net} = \text{Gross} - \text{Fees} - \text{Slippage} - \text{Spread}$ is **exact to 0.000000... with zero error**.  
When persisting trade ledgers, each component is independently quantized to cents (`Decimal("0.01")`) using `ROUND_HALF_UP`. This independent cent-rounding convention introduces a mathematically bounded variance of at most $\pm \$0.02$ per trade. Summed across hundreds of trades, these sub-cent quantization variances accumulate to small bounded values ($|\Delta| \le \$0.15$).

---

## 2. The Three Accounting Calculation Tiers

To eliminate ambiguity across reports, code, and documentation, NEPTUNE formally defines three distinct accounting calculation tiers:

### Tier 1: Full-Precision Aggregate Accounting (Internal Engine)
- **Definition**: All monetary calculations executed during the simulation lifecycle before string or storage quantization.
- **Data Types**: Python `Decimal` with arbitrary precision (up to 28 decimal places).
- **Identity**:
  $$\text{Net PnL}_{\text{raw}} = \text{Gross PnL}_{\text{raw}} - \text{Fees}_{\text{raw}} - \text{Slippage}_{\text{raw}} - \text{Spread}_{\text{raw}}$$
- **Discrepancy**: **$0.000000... (Zero error bit-for-bit)**.

### Tier 2: Sum of Individually Rounded Trade Values (Persisted Ledgers)
- **Definition**: The trade attributes stored in SQLite databases, CSV exports, and Parquet ledgers.
- **Quantization**: In `backend/app/simulation/execution.py` (lines 361–365), each term is independently rounded to the nearest cent:
  ```python
  gross_pnl = gross_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
  fees = total_fees.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
  spread_cost = total_spread_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
  slippage_cost = total_slippage_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
  net_pnl = net_pnl.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
  ```
- **Error Bound**: Because $\text{Net PnL}$ is rounded from $\text{Net}_{\text{raw}}$ rather than reconstructed from already-rounded components:
  $$\left| \text{round}(\text{Net}) - \left[ \text{round}(\text{Gross}) - \text{round}(\text{Fees}) - \text{round}(\text{Slip}) - \text{round}(\text{Spread}) \right] \right| \le \$0.02$$
- **Portfolio Cumulative Bound**: Across $N$ independent trades, Central Limit Theorem bounds cumulative variance to $|\sum \Delta| \le 3 \times 0.0064 \sqrt{N}$. For $N = 277$, the maximum expected variance is $\pm \$0.32$. The observed maximum across all 12 ledgers is **$\$0.14$**.

### Tier 3: Display-Rounded Aggregate Values (Reports & UI)
- **Definition**: Rendered strings in Markdown tables, logs, and frontend dashboards.
- **Formatting**: Values formatted via `round(val, 2)` or `f"{val:.2f}"`.
- **Formatting Defect Disclosure**: In Milestone 4.3.2 line 240 of `run_milestone_4_3_2_parallel.py`, `"spread": round(tot_spread)` omitted `, 2`, displaying `$27.14` as integer `27` ($27.00). The underlying Parquet and CSV ledgers always stored the exact Decimal cost.

---

## 3. Full-Precision Accounting Reconciliation Across All 12 Ledgers

Every trade across all 12 authoritative event ledgers was evaluated trade-by-trade using Decimal precision:

| Authoritative Ledger | Trades | Gross Realized PnL ($) | Total Fees ($) | Total Slippage ($) | Total Spread ($) | Net Realized PnL ($) | Sum of Parts ($) | Rounding Difference ($) | Trades with Sub-Cent Variance | Max Single Trade Diff ($) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `balanced_baseline` | 277 | $93.47 | $271.00 | $135.47 | $27.14 | **-$340.22** | -$340.14 | **-$0.08** | 71 | $0.02 |
| `balanced_h1_adx_25` | 277 | $93.47 | $271.00 | $135.47 | $27.14 | **-$340.22** | -$340.14 | **-$0.08** | 71 | $0.02 |
| `balanced_h1b_adx_30` | 194 | $137.00 | $200.33 | $100.23 | $20.04 | **-$183.46** | -$183.60 | **+$0.14** | 58 | $0.01 |
| `balanced_h4_rvol_85` | 274 | $124.75 | $270.07 | $135.02 | $27.03 | **-$307.38** | -$307.37 | **-$0.01** | 68 | $0.01 |
| `balanced_h5_volatility_bounds`| 137 | $69.72 | $52.18 | $26.08 | $5.22 | **-$13.86** | -$13.76 | **-$0.10** | 39 | $0.01 |
| `balanced_h7_confluence` | 126 | $90.42 | $47.77 | $23.85 | $4.77 | **+$14.02** | +$14.03 | **-$0.01** | 35 | $0.02 |
| `fixed_bracket_baseline` | 269 | $89.81 | $260.94 | $130.53 | $26.01 | **-$327.65** | -$327.67 | **+$0.02** | 62 | $0.01 |
| `fixed_bracket_h1_adx_25` | 269 | $89.81 | $260.94 | $130.53 | $26.01 | **-$327.65** | -$327.67 | **+$0.02** | 62 | $0.01 |
| `fixed_bracket_h1b_adx_30` | 198 | $154.00 | $194.02 | $97.04 | $19.38 | **-$156.47** | -$156.44 | **-$0.03** | 53 | $0.01 |
| `fixed_bracket_h4_rvol_85` | 267 | $85.29 | $268.01 | $134.04 | $26.77 | **-$343.51** | -$343.53 | **+$0.02** | 59 | $0.01 |
| `fixed_bracket_h5_volatility_bounds`| 147 | $65.35 | $55.95 | $28.01 | $5.54 | **-$24.19** | -$24.15 | **-$0.04** | 42 | $0.02 |
| `fixed_bracket_h7_confluence` | 139 | $78.16 | $52.27 | $26.17 | $5.17 | **-$5.59** | -$5.45 | **-$0.14** | 41 | $0.02 |

*Data persisted in [`storage/exports/milestone_4_3_4/full_precision_accounting_reconciliation.csv`](file:///d:/Project%202026/Trading_bot/storage/exports/milestone_4_3_4/full_precision_accounting_reconciliation.csv).*

---

## 4. Architectural Verification & Regression Tests

To ensure that displayed values are never mistaken for ledger values and that the independent cent-rounding convention remains intact:
1. **Automated Test Suite**: Added 5 dedicated unit tests in [`backend/tests/unit/test_milestone_4_3_4_accounting.py`](file:///d:/Project%202026/Trading_bot/backend/tests/unit/test_milestone_4_3_4_accounting.py).
2. **Invariants Enforced**:
   - $\text{Net}_{\text{raw}} == \text{Gross}_{\text{raw}} - \text{Fees}_{\text{raw}} - \text{Slip}_{\text{raw}} - \text{Spread}_{\text{raw}}$ bit-for-bit.
   - Max single-trade discrepancy $|\Delta| \le \$0.02$.
   - Max portfolio cumulative discrepancy $|\sum \Delta| \le \$0.20$.
   - Valid SHA256 hashes for all 12 authoritative ledger files in `benchmark_manifest.json`.

**Audit Conclusion**: The accounting across all 12 NEPTUNE models reconciles completely under the Tier 2 independent cent-rounding convention. There are zero unexplained accounting discrepancies.

