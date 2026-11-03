# NEPTUNE — Milestone 4.6.2.5: Execution Cost & Accounting Reconciliation

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Milestone:** 4.6.2.5  
**Topic:** Audit B — Independent Execution Cost Calculation, Spread/Slippage Attribution & Cash Conservation  
**Date:** 2026-11-03  
**Status:** Reconciled & Mathematically Verified  

---

## 1. Executive Cost Model Architecture

NEPTUNE enforces realistic paper execution dynamics without unearned windfall assumptions (Rule A-10, Rule S-06).

### 1.1 Parameter Definitions & Breakdown

The historical simulation engine operates with the following parameter configuration:

| Component | Parameter Symbol | Configuration Value | Calculation Basis |
|---|---|---|---|
| **Taker Entry Fee** | $f_{\text{entry}}$ | $0.0010$ ($0.10\%$) | Executed Entry Notional ($P_{\text{exec, entry}} \cdot Q$) |
| **Taker Exit Fee** | $f_{\text{exit}}$ | $0.0010$ ($0.10\%$) | Executed Exit Notional ($P_{\text{exec, exit}} \cdot Q$) |
| **Entry Slippage** | $s_{\text{entry}}$ | $0.0005$ ($0.05\%$) | Reference Midpoint Price ($P_{\text{ref, entry}} \cdot s_{\text{entry}} \cdot Q$) |
| **Exit Slippage** | $s_{\text{exit}}$ | $0.0005$ ($0.05\%$) | Reference Midpoint Price ($P_{\text{ref, exit}} \cdot s_{\text{exit}} \cdot Q$) |
| **Bid-Ask Spread** | $\text{spread\_bps}$ | $2.0\text{ bps}$ ($0.02\%$) | Half-Spread Fraction: $\phi = \frac{\text{spread\_bps}}{20000} = 0.0001$ ($0.01\%$) per side |

### 1.2 Resolution of the "0.30% Round-Trip" Assumption

The prior Milestone 4.6.2.4 report referred to a "0.30% round trip friction". Independent forensic arithmetic clarifies this figure:
- **Taker Fees (Round Trip):** $0.10\% + 0.10\% = 0.20\%$ ($20\text{ bps}$)
- **Slippage (Round Trip):** $0.05\% + 0.05\% = 0.10\%$ ($10\text{ bps}$)
- **Subtotal (Fees + Slippage):** $0.20\% + 0.10\% = \mathbf{0.30\%}$ ($30\text{ bps}$)
- **Half-Spread Penalty (Round Trip):** $0.01\% + 0.01\% = \mathbf{0.02\%}$ ($2\text{ bps}$)
- **Total Effective Round-Trip Friction:** $\mathbf{0.32\%}$ ($32\text{ bps}$)

> [!NOTE]
> If half-spread were assumed to be $0.05\%$ per side (10 bps full spread), the total friction would be $0.40\%$ ($40\text{ bps}$). Under NEPTUNE's default 2.0 bps spread model, total friction is exactly **32 bps (0.32%)**.

---

## 2. Step-by-Step Representative Long Trade Reconciliation

Consider a representative trade with initial cash equity $C_0 = \$1,000.00$, position size $Q = 0.01\text{ BTC}$, reference entry price $P_{\text{ref, entry}} = \$50,000.00$, and reference exit price $P_{\text{ref, exit}} = \$52,000.00$.

### 2.1 Entry Execution
1. **Friction Multiplier (Entry):**
   $$M_{\text{entry}} = 1 + s_{\text{entry}} + \phi = 1 + 0.0005 + 0.0001 = 1.0006$$
2. **Executed Entry Price:**
   $$P_{\text{exec, entry}} = P_{\text{ref, entry}} \cdot M_{\text{entry}} = \$50,000.00 \cdot 1.0006 = \$50,030.00$$
3. **Entry Notional:**
   $$\text{Notional}_{\text{entry}} = P_{\text{exec, entry}} \cdot Q = \$50,030.00 \cdot 0.01 = \$500.30$$
4. **Entry Frictions:**
   - $\text{Entry Slippage Cost} = P_{\text{ref, entry}} \cdot s_{\text{entry}} \cdot Q = \$50,000.00 \cdot 0.0005 \cdot 0.01 = \$0.2500$
   - $\text{Entry Spread Cost} = P_{\text{ref, entry}} \cdot \phi \cdot Q = \$50,000.00 \cdot 0.0001 \cdot 0.01 = \$0.0500$
   - $\text{Entry Fee} = \text{Notional}_{\text{entry}} \cdot f_{\text{entry}} = \$500.30 \cdot 0.0010 = \$0.5003$
5. **Cash Outflow at Entry:**
   $$\text{Cash Outflow} = \text{Notional}_{\text{entry}} + \text{Entry Fee} = \$500.30 + \$0.5003 = \$500.8003$$
   $$C_1 = C_0 - \text{Cash Outflow} = \$1,000.00 - \$500.8003 = \$499.1997$$

### 2.2 Exit Execution
1. **Friction Multiplier (Exit):**
   $$M_{\text{exit}} = 1 - s_{\text{exit}} - \phi = 1 - 0.0005 - 0.0001 = 0.9994$$
2. **Executed Exit Price:**
   $$P_{\text{exec, exit}} = P_{\text{ref, exit}} \cdot M_{\text{exit}} = \$52,000.00 \cdot 0.9994 = \$51,968.80$$
3. **Exit Notional:**
   $$\text{Notional}_{\text{exit}} = P_{\text{exec, exit}} \cdot Q = \$51,968.80 \cdot 0.01 = \$519.6880$$
4. **Exit Frictions:**
   - $\text{Exit Slippage Cost} = P_{\text{ref, exit}} \cdot s_{\text{exit}} \cdot Q = \$52,000.00 \cdot 0.0005 \cdot 0.01 = \$0.2600$
   - $\text{Exit Spread Cost} = P_{\text{ref, exit}} \cdot \phi \cdot Q = \$52,000.00 \cdot 0.0001 \cdot 0.01 = \$0.0520$
   - $\text{Exit Fee} = \text{Notional}_{\text{exit}} \cdot f_{\text{exit}} = \$519.6880 \cdot 0.0010 = \$0.519688$
5. **Cash Inflow at Exit:**
   $$\text{Cash Inflow} = \text{Notional}_{\text{exit}} - \text{Exit Fee} = \$519.6880 - \$0.519688 = \$519.168312$$
   $$C_2 = C_1 + \text{Cash Inflow} = \$499.1997 + \$519.168312 = \$1,018.368012$$

---

## 3. P&L and Cash Conservation Proof

1. **Gross P&L:**
   $$\text{Gross P\&L} = (P_{\text{ref, exit}} - P_{\text{ref, entry}}) \cdot Q = (\$52,000.00 - \$50,000.00) \cdot 0.01 = \$20.0000$$
2. **Total Round-Trip Frictions:**
   - $\text{Total Fees} = \$0.5003 + \$0.519688 = \$1.019988 \approx \$1.02$
   - $\text{Total Slippage Cost} = \$0.2500 + \$0.2600 = \$0.5100$
   - $\text{Total Spread Cost} = \$0.0500 + \$0.0520 = \$0.1020 \approx \$0.10$
   - $\text{Sum of Frictions} = \$1.019988 + \$0.5100 + \$0.1020 = \$1.631988$
3. **Net P&L:**
   $$\text{Net P\&L} = \text{Gross P\&L} - \text{Sum of Frictions} = \$20.0000 - \$1.631988 = \$18.368012$$
   $$\text{Reported Net P\&L (Quantized to cents)} = \$18.37$$
4. **Delta Cash:**
   $$\Delta C = C_2 - C_0 = \$1,018.368012 - \$1,000.00 = \$18.368012$$
5. **Conservation Invariant:**
   $$\Delta C - \text{Net P\&L} = \$0.00000000$$

> [!IMPORTANT]
> The unquantized cash equity delta exactly equals the mathematical net P&L. No component is counted twice, omitted, or lost to floating-point truncation.

---

## 4. Execution Nuances & Bracket Handling

1. **Maker vs. Taker Mandate:**
   All entry orders, market exits, and resting bracket fills are conservatively charged the **taker fee ($0.10\%$)**. Maker fee rebates are never assumed in historical simulation (Rule S-06).
2. **Ambiguous Bar Conservative Resolution:**
   If both stop loss and take profit thresholds are touched within the same OHLC bar, the simulator conservatively resolves the outcome as an **immediate stop loss hit (`AMBIGUOUS_BAR_STOP`)**.
3. **Opening Gap Stop Handling:**
   If the market opens below the stop loss level on a Long trade, the execution simulator fills at the worse opening price ($\min(\text{stop\_loss}, c_{\text{open}})$) rather than the theoretical stop price.
4. **Opening Gap Entry Rejection:**
   If the market gaps past the stop loss prior to order execution ($c_{\text{open}} \le \text{stop\_loss}$ for Long), the scheduler immediately cancels the order before fill to prevent instantaneous negative equity.
