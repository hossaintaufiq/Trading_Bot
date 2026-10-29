# 🔱 Neptune Bot — Quantitative Day Trading & Multi-Bot Suite

An institutional-grade, multi-bot algorithmic crypto trading platform built in Python. Features real-time **1-second live WebSocket market telemetry**, **15-second quantitative radar pulses**, integrated **Day Trader Skills** (Opening Range Breakout, Bull Flag, Oversold Bounce, 20-MA Reclaim), a **Monte Carlo Time Machine (1,000 Paths)** simulator, and a **Cyber-Oceanic Glassmorphic Web Dashboard**.

---

## 🌟 The Day Trader Skill Implementation

Neptune Bot directly incorporates the proven quantitative skills from the Day Trader pack:

| Skill | Module | Neptune Bot Execution |
| :--- | :--- | :--- |
| **`trader-scanner`** | Setup Radar | Scans real-time candles every 15s for **ORB Breakouts**, **Bull Flags**, **Oversold Bounces**, and **20-MA Reclaims**. |
| **`trader-entry`** | Entry Timer | Watches bar-by-bar and executes *only* on confirmed candle closes to prevent fakeout wicks. |
| **`trader-exit`** | Bracket Planner | Generates pre-trade bracket orders: Stop at Range Midpoint (`or-mid`) or `atr:1.5`, and Take-Profit at **2R** target. |
| **`trader-timemachine`** | Time Machine | Replays **1,000 simulated paths** using the asset's empirical bar return distribution. Displays Target Hit %, Stop Hit %, and Expected R before risking capital. |
| **`trader-budget`** | Budget Sizer | Sizes orders dynamically: `Position Units = Max Risk ($50) / Distance to Stop`. |
| **`trader-risk`** | Risk Gate | Pre-trade validation gate enforcing minimum 1.5R reward-to-risk, daily drawdown caps, and cash buffers. |

---

## 🤖 The Neptune Autonomous Multi-Bot Fleet

In the dashboard, you can run individual bots or deploy the entire fleet:

1. **🔱 Neptune Autonomous Fleet (Default)**:
   * Runs all 5 bots concurrently in parallel.
   * Every second, it evaluates incoming market ticks.
   * When any setup triggers and passes the Risk Gate and Time Machine odds, the Fleet executes the trade!
2. **Bot 1: Opening Range Breakout (ORB)**:
   * Measures the 15-minute Opening Range. Buys on the first closed bar breaking out above the range high. Sets stop at range midpoint.
3. **Bot 2: Bull Flag Momentum**:
   * Identifies strong impulse spikes followed by tight consolidation inside a 1.2% channel, triggering on the flag breakout.
4. **Bot 3: Oversold Bounce**:
   * Detects RSI(14) oversold dips below 30 and enters on the first green reversal candle targeting mean reversion.
5. **Bot 4: 20-MA Reclaim**:
   * Buys when price reclaims the 20-period moving average with rising volume.
6. **Bot 5: EMA 9/21 Trend Momentum**:
   * Golden Cross momentum engine with support pullback dip-buying.

---

## ⏱️ Telemetry Cadence: 1s Live Ticks / 15s Radar Scan

* **1-Second Live Loop**:
  * Real-time WebSocket connection to Binance (`BTC/USDT`, `ETH/USDT`, `SOL/USDT`, `BNB/USDT`).
  * Instant tick updates on price, active position P&L, indicator values, and chart candles.
* **15-Second Radar Pulse**:
  * Scans all 4 day-trading setups.
  * Runs the **Time Machine Monte Carlo 1,000-path simulation**.
  * Updates the bracket plan and risk gate status.

---

## 🚀 Quick Launch (Windows)

```powershell
cd "d:\Project 2026\Trading_bot"
python run.py
```

* Opens browser automatically to **`http://localhost:8000`**.
* Click **`TEST BUY`** at the top to simulate an instant trade and verify execution, chart markers, sound chimes, and P&L cards.
* Click **`START BOT`** to let the Neptune Fleet trade autonomously.
