# NEPTUNE — Milestone 4.6.3.0.1
## Group D Exposure Control Integrity Audit

**Project:** NEPTUNE Autonomous Market Intelligence & Quantitative Research Platform  
**Document:** Group D Exposure Dimensions & Methodology Audit  
**Author:** Quantitative Audit Agent  
**Governing Rules:** Rule S-05, Rule S-06, ADR-028, ADR-030  

---

## 1. The Core Methodological Challenge

The purpose of Group D in the four-group experimental design is to serve as a **market-exposure control**.

Even if Group B (News-Veto) and Group C (Frequency-Matched) execute the same total number of trades, their actual market exposure may differ substantially:
- If news vetoes disproportionately filter out trades that would have been closed early by stop-losses, Group B's trades will have longer average holding periods than Group A's or Group C's.
- Conversely, if news vetoes prevent entries during prolonged consolidation periods, Group B's total time-in-market will be substantially lower.
- Differences in total time-in-market alter the amount of market drift, overnight risk, and funding costs to which the strategy is exposed.

Group D isolates the effect of news intelligence from the effect of aggregate market exposure.

---

## 2. Audit Discovery: The Trade-Count != Exposure Fallacy

Milestone 4.6.3.0 proposed matching exposure via `filter_by_cumulative_exposure_budget`, which calculated a target trade budget by dividing the cumulative target exposure bars by an assumed `average_holding_bars`:

$$\text{target\_trades} = \text{round}\left(\frac{\text{target\_total\_bars\_exposure}}{\text{average\_holding\_bars}}\right)$$

### Methodological Deficiencies Identified by the Audit

1. **Holding Period Variance:** In trend-following strategies with dynamic trailing stops, holding periods are heavily right-skewed. A small number of extended trends run for 50–100 bars, while losing trades exit in 5–15 bars. Dividing by a scalar average holding duration fails to match actual market exposure.
2. **Multi-Asset Overlap:** Holding two positions simultaneously for 10 bars consumes 20 position-bars of risk and double the virtual margin, but only 10 chronological bars of elapsed time. Scalar bar counts conflate portfolio utilization with calendar exposure.
3. **Directional Exposure Imbalance:** 100 bars of long exposure during a macro bull market has completely different expected returns than 100 bars of short exposure.
4. **Online vs. Ex-Post Conflation:** Consuming the final total bars of Group B across the entire partition requires retrospective knowledge.

---

## 3. The 7-Dimensional Exposure Model

To eliminate exposure confounding, NEPTUNE formalizes seven orthogonal exposure dimensions in [`ExposureDimensions`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py):

| Dimension | Metric | Purpose |
|-----------|--------|---------|
| 1. Time in Market (Bars) | `time_in_market_bars` | Total bars during which at least one position was open |
| 2. Market Exposure Percentage | `time_in_market_pct` | Fraction of total simulation duration exposed to market |
| 3. Trade Count & Holding Duration | `trade_count`, `average_holding_bars` | Discrete position turnover and average holding duration |
| 4. Asset Allocation Breakdown | `asset_breakdown_bars` | Per-symbol exposure bars (BTC vs. ETH vs. BNB) |
| 5. Directional Duration Ratio | `directional_duration_bars` | Net bars spent LONG vs. SHORT |
| 6. Dollar-Hours Capital Utilization | `dollar_hours_capital_utilization` | Time-weighted notional capital at risk ($\sum \text{position\_size} \times \text{entry\_price} \times \text{duration\_hours}$) |
| 7. Simultaneous Multi-Asset Risk | `simultaneous_multi_asset_bars` | Bars with concurrent positions running across multiple symbols |

---

## 4. Online Exposure Matching via Dynamic Cooldown

For online, point-in-time simulation, NEPTUNE implements [`OnlineExposureMatchingEngine`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py):
- Operates candle-by-candle without knowing future returns or holding times.
- Enforces a dynamic cooldown window (e.g., $C = 4$ bars on 15m) following each position exit for a given symbol.
- Naturally regulates time-in-market and dampens over-trading in choppy regimes without requiring future exposure totals.

For retrospective analysis, [`ExPostExposureMatchingEngine`](file:///d:/Project%202026/Trading_bot/backend/app/simulation/research_protocol.py) is retained and explicitly marked `is_ex_post_diagnostic = True`.

---

## 5. Verification Status

All adversarial tests for Group D passed in [`test_milestone_4_6_3_0_1_adversarial.py`](file:///d:/Project%202026/Trading_bot/backend/tests/unit/test_milestone_4_6_3_0_1_adversarial.py):
- `test_seven_exposure_dimensions_integrity`: **PASSED**
- `test_online_exposure_cooldown_engine`: **PASSED**
- `test_ex_post_exposure_engine_labeled`: **PASSED**
