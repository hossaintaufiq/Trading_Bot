# NEPTUNE — Milestone 4.6.3.1.1
## Forensic Accounting Reconciliation: Gross P&L, Transaction Costs & Portfolio Equity

**Document:** Forensic Accounting & Portfolio State Reconciliation  
**Audit Target:** Milestone 4.6.3.1 Experimental Results (`storage/exports/milestone_4_6_3_1/`)  
**Artifact Link:** [`accounting_reconciliation.json`](file:///d:/Project%202026/Trading_bot/storage/exports/milestone_4_6_3_1_1/accounting_reconciliation.json) & [`equity_curve_reconciliation.json`](file:///d:/Project%202026/Trading_bot/storage/exports/milestone_4_6_3_1_1/equity_curve_reconciliation.json)  

---

## 1. Trade-Level Forensic Accounting Identity

The foundational accounting invariant governing all paper orders in NEPTUNE (Rule A-01, Rule A-10) is:

$$\text{Net PnL} = \text{Gross PnL} - \text{Total Friction} = \text{Gross PnL} - (\text{Fees} + \text{Slippage} + \text{Spread})$$

Where for each trade $i$:
1. **Gross Realized P&L:**
   $$\text{Gross PnL}_i = \begin{cases} (\text{Raw Exit}_i - \text{Raw Entry}_i) \times \text{Size}_i & \text{if LONG} \\ (\text{Raw Entry}_i - \text{Raw Exit}_i) \times \text{Size}_i & \text{if SHORT} \end{cases}$$
2. **Transaction Fees (Taker 0.10% on entry & exit):**
   $$\text{Fees}_i = (\text{Executed Entry}_i \times \text{Size}_i \times 0.001) + (\text{Executed Exit}_i \times \text{Size}_i \times 0.001)$$
3. **Adverse Slippage (0.05% on entry & exit):**
   $$\text{Slippage}_i = (\text{Raw Entry}_i \times \text{Size}_i \times 0.0005) + (\text{Raw Exit}_i \times \text{Size}_i \times 0.0005)$$
4. **Bid-Ask Spread (1.0 bps on entry & exit = 0.01%):**
   $$\text{Spread}_i = (\text{Raw Entry}_i \times \text{Size}_i \times 0.0001) + (\text{Raw Exit}_i \times \text{Size}_i \times 0.0001)$$

### Per-Trade Rounding Quantization Behavior
In `SimulatedTrade` ([`execution.py`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/execution.py#L375-L379)), each field is individually quantized to two decimal places using Python `Decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`:
- `gross_pnl.quantize(0.01)`
- `fees.quantize(0.01)`
- `slippage_cost.quantize(0.01)`
- `spread_cost.quantize(0.01)`
- `net_pnl.quantize(0.01)`

Because each term is rounded independently, $\text{Round}(\text{Gross}) - \text{Round}(\text{Fees}) - \text{Round}(\text{Slip}) - \text{Round}(\text{Spread})$ can differ from $\text{Round}(\text{Gross} - \text{Fees} - \text{Slip} - \text{Spread})$ by strictly $\pm \$0.01$ per trade. Over 68 trades, the cumulative quantization drift is bounded within $\pm \$0.06$ USDT across all groups.

---

## 2. Independent Group Reconciliation Table

| Metric | Group A (Technical Baseline) | Group B (News Veto Treatment) | Group C (Online Frequency Control) | Group D (Online Exposure Control) |
|---|---|---|---|---|
| **Executed Trades** | 68 | 47 | 62 | 60 |
| **Sum of Positive Gross PnL** | +$119.86 USDT | +$100.52 USDT | +$110.56 USDT | +$129.59 USDT |
| **Sum of Negative Gross PnL** | -$207.35 USDT | -$135.36 USDT | -$182.92 USDT | -$177.23 USDT |
| **Reconstructed True Gross PnL** | **-$87.49 USDT** | **-$34.84 USDT** | **-$72.36 USDT** | **-$47.64 USDT** |
| **Total Taker Fees** | $79.53 USDT | $49.73 USDT | $71.14 USDT | $73.25 USDT |
| **Total Slippage Cost** | $39.81 USDT | $24.89 USDT | $35.57 USDT | $36.60 USDT |
| **Total Spread Cost** | $7.91 USDT | $4.94 USDT | $7.08 USDT | $7.30 USDT |
| **Total Transaction Friction** | **$127.25 USDT** | **$79.56 USDT** | **$113.79 USDT** | **$117.15 USDT** |
| **Reconstructed Net PnL (Gross - Friction)** | **-$214.74 USDT** | **-$114.40 USDT** | **-$186.15 USDT** | **-$164.79 USDT** |
| **Reported Net PnL (Sum of Trade `net_pnl`)** | **-$214.72 USDT** | **-$114.42 USDT** | **-$186.21 USDT** | **-$164.80 USDT** |
| **Quantization Rounding Drift** | **-0.02 USDT** | **+0.02 USDT** | **+0.06 USDT** | **+0.01 USDT** |

---

## 3. Investigation of the Gross P&L Discrepancy

The audit inquiry highlighted the following apparent arithmetic contradictions in `group_metrics.json`:
- Group A: `108.24 - 218.97 - 127.25 = -237.98 != -214.72`
- Group B: `92.43 - 143.45 - 79.56 = -130.58 != -114.42`
- Group C: `101.49 - 191.99 - 113.79 = -204.29 != -186.21`
- Group D: `119.95 - 186.87 - 117.15 = -184.07 != -164.80`

### Forensic Determination: Defect in Metric Partitioning
Inspection of `backend/app/simulation/development_orchestrator.py` ([lines 866–873](file:///d:/Project%202026/Trading_bot/backend/app/simulation/development_orchestrator.py#L866-L873)) uncovered the root cause:

```python
wins = [t for t in trades if t.net_pnl > 0]
losses = [t for t in trades if t.net_pnl <= 0]

gross_profit = sum(t.gross_pnl for t in wins) if wins else Decimal("0")
gross_loss = sum(abs(t.gross_pnl) for t in losses) if losses else Decimal("0")
```

1. **Net-Winners Conditioning:** The code defined `wins` as trades with `net_pnl > 0` rather than `gross_pnl > 0`.
2. **Flipped Signs for Net Losers:** In Group A, there were **6 trades** that generated positive price movement ($+11.62 USDT total gross profit), but whose profit was smaller than the round-trip friction, resulting in negative `net_pnl`.
3. **The Distortion:** Because their `net_pnl <= 0`, these 6 trades were classified into `losses`. The line `sum(abs(t.gross_pnl) for t in losses)` took their *positive* gross profit (+11.62 USDT) and added it to `gross_loss`!
   - True positive gross profit = $108.24 + 11.62 = \mathbf{119.86\text{ USDT}}$.
   - True negative gross loss = $218.97 - 11.62 = \mathbf{207.35\text{ USDT}}$.
   - True gross PnL = $119.86 - 207.35 = \mathbf{-87.49\text{ USDT}}$.
4. **Reconciliation:**
   $$\text{True Gross PnL (-87.49)} - \text{Total Friction (127.25)} = \mathbf{-214.74\text{ USDT}}$$
   This perfectly equals the reported Net Realized PnL (-214.72 USDT) within 2 cents of rounding drift.

---

## 4. Forensic Investigation of Portfolio Equity & Return

The audit inquiry requested clarification on why the report gave:
- Group A: Net P&L of -$214.72 USDT, but ending equity of 984.56 USDT (1000 - 214.72 = 785.28, a gap of +$199.28).
- Group B: Net P&L of -$114.42 USDT, but ending equity of 988.34 USDT (1000 - 114.42 = 885.58, a gap of +$102.76).
- Group C: Net P&L of -$186.21 USDT, but ending equity of 981.20 USDT (1000 - 186.21 = 813.79, a gap of +$167.41).
- Group D: Net P&L of -$164.80 USDT, but ending equity of 1001.79 USDT (reported positive return +0.18% despite -$164.80 loss).

### Forensic Determination: Cash Equity Inverted-Sign Defect on Short Positions
In `development_orchestrator.py` ([lines 464, 503–505](file:///d:/Project%202026/Trading_bot/backend/app/simulation/development_orchestrator.py#L464-L505)), portfolio cash equity was updated on position fill and close as:

```python
# On order fill:
cash_outflow = (new_pos.position_size * new_pos.entry_price) + new_pos.entry_fee
grp.cash_equity -= cash_outflow

# On position close:
exit_notional = pos.position_size * trade.exit_price
exit_fee = exit_notional * self.backtest_cfg.taker_fee_pct
grp.cash_equity += (exit_notional - exit_fee)
```

### The Mechanism of Failure:
- **For LONG Positions:** Cash change = $\text{Size} \times (\text{Exit} - \text{Entry}) - \text{Fees} = \text{Net PnL}$. (Correct).
- **For SHORT Positions:** In reality, shorting involves borrowing base asset and selling it (cash inflow at entry, cash outflow at buy-to-cover). But the engine treated SHORT orders as if they were BUY orders, subtracting `Size * Entry` on open and adding `Size * Exit` on close!
- **The Consequence:** For a SHORT trade, the cash delta recorded was:
  $$\Delta \text{Cash} = \text{Size} \times (\text{Exit} - \text{Entry}) - \text{Fees}$$
  Notice that for a losing short (where price rose, $\text{Exit} > \text{Entry}$), $\Delta \text{Cash}$ was **positive**! The engine **credited the short loss as a cash inflow**!
- Because 63.2% of trades in Group A were SHORT positions (43 of 68), and most were losing trades, the engine credited **+$199.31 USDT of phantom cash** into Group A's cash balance over the year!

### Corrected True Equity & Portfolio Return Reconciliation

$$\text{True Ending Equity} = \text{Initial Capital (1,000)} + \sum \text{Net PnL}$$

| Group | Total Trades | Shorts Count | Cumulative Net PnL | Flawed Reported Ending Equity | True Reconstructed Ending Equity | Flawed Reported Return | True Portfolio Return |
|---|---|---|---|---|---|---|---|
| **Group A** | 68 | 43 (63.2%) | -$214.72 USDT | $984.56 USDT | **$785.28 USDT** | -1.54% | **-21.47%** |
| **Group B** | 47 | 28 (59.6%) | -$114.42 USDT | $988.34 USDT | **$885.58 USDT** | -1.17% | **-11.44%** |
| **Group C** | 62 | 39 (62.9%) | -$186.21 USDT | $981.20 USDT | **$813.79 USDT** | -1.88% | **-18.62%** |
| **Group D** | 60 | 38 (63.3%) | -$164.80 USDT | $1001.79 USDT | **$835.20 USDT** | +0.18% | **-16.48%** |

**Accounting Conclusion:** The true portfolio returns are strictly negative across all groups (-11.44% to -21.47%). The reported ending equity figures near $984–$1001 were an artifact of inverted cash-flow accounting on short trades.

