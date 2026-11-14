# NEPTUNE 🔱

**Autonomous Quantitative Market Intelligence & Institutional Paper Trading Platform**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![Next.js 14](https://img.shields.io/badge/Next.js-14.2+-black.svg)](https://nextjs.org)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg)](https://www.typescriptlang.org)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4+-38B2AC.svg)](https://tailwindcss.com)
[![Paper Trading Only](https://img.shields.io/badge/Execution-Paper%20Trading%20Only-orange.svg)](#absolute-safety-rules)
[![Zero Look-Ahead Bias](https://img.shields.io/badge/Data%20Integrity-Zero%20Look--Ahead%20Bias-emerald.svg)](#algorithmic-integrity)

> ⚠️ **RESEARCH & PAPER TRADING PLATFORM ONLY.**  
> NEPTUNE is strictly an educational and quantitative research system. In accordance with Architectural Decision **ADR-001** and Rule **S-01**, it does **not** execute live orders, hold private keys, manage real investor funds, or promise commercial financial returns.

---

## 🌟 Executive Overview

**NEPTUNE** is an autonomous cryptocurrency quantitative trading platform engineered around **Ten Specialist AI Agents** orchestrated by an asynchronous **Central Brain**. Its current research strategy is a low-turnover **daily trend-following** rule (`daily_trend_v1`); the earlier intraday V2 strategy (4h/1h with CPPI sizing and a profit-lock ratchet) is retained for research but was found unprofitable.

Every paper trade is subjected to rigorous Monte Carlo simulation and must be unconditionally approved by an independent **Risk Manager** before execution.

```
                                  ┌────────────────────────┐
                                  │   4-Hour Macro Trend   │
                                  │  EMA 50 > 200 + ADX>24 │
                                  └───────────┬────────────┘
                                              ▼
┌──────────────────────┐          ┌────────────────────────┐
│  BTC Macro Shield    │ ───────► │ 1-Hour Value Pullback  │
│  Altcoin Bear Filter │          │ RSI (40-52) + Reversal │
└──────────────────────┘          └───────────┬────────────┘
                                              ▼
                                  ┌────────────────────────┐
                                  │ Ten Specialist Agents  │
                                  │  Orchestrated by Brain │
                                  └───────────┬────────────┘
                                              ▼
                                  ┌────────────────────────┐
                                  │ Dynamic 2-Stage Ratchet│
                                  │ +1.0R B/E ➔ +2.0R Lock │
                                  └────────────────────────┘
```

---

## 📊 Research Results (corrected 2026-11-13, ADR-037)

> ⚠️ **Earlier versions of this README claimed the intraday V2 algorithm was profitable (+5.8% over 3 years, zero breaker trips). That was wrong.** The backtest runners leaked the still-forming 4h candle into the 4h trend filter (look-ahead). After the fix, with parameters unchanged, V2 is **not profitable**. The old figures have been removed.

### Intraday V2 (`DualTimeframeTrendV2`) — failed after look-ahead fix

| Year | Trades | Gross P&L (before costs) | Net P&L |
|---|---:|---:|---:|
| 2024 | 80 | +$67.45 | +$47.94 (5% breaker tripped 2024-11-24) |
| 2025 | 58 | +$3.47 | −$13.56 |
| 2026 | 51 | −$35.22 | −$46.39 |
| **Total** | **189** | **+$35.70 (t = 0.66, not significant)** | **−$12.01** |

No demonstrable gross edge; costs (0.32% round trip) turn it negative.

### Current research candidate: `daily_trend_v1` (paper only)

Long-only daily Donchian rule: buy when a daily close exceeds the prior 20-day highest close, sell when a close falls below the prior 10-day lowest close, otherwise hold cash. Fills at the next open with fees 0.10%, slippage 0.05%, half-spread 0.01% per side. Rule chosen on 2018–2023 only; 2024–2026 evaluated once.

| Universe | Period | Strategy (net) | Buy & hold | Max drawdown |
|---|---|---:|---:|---:|
| BTC/ETH/BNB | 2018–2023 (selection) | +3,221% | +1,318% | 55.5% |
| BTC/ETH/BNB | **2024–2026 (test)** | **+25.6%** | +55.6% | 38.1% |
| 36 coins incl. delisted | **2024–2026 (test)** | **+52%** | −44% | 37% |

By calendar year (36 coins): 2024 +71%, **2025 −5%, 2026 −7%**. A $1,000 paper account opened Jan 2024 is at +24.7%, Jan 2025 at −3.1%, Jan 2026 at −9.1%.

**Limits:** survivorship bias (coins that never listed are absent), only a handful of independent trends, drawdowns of 25–45%, only 17 of 36 coins were individually profitable in the test window, and it loses money in sideways/falling markets. This is research evidence, **not** a profitability claim (Rule S-07). Forward paper trading is still required.

---

## 🧠 The Ten Specialist Agents Architecture

NEPTUNE strictly prohibits peer-to-peer agent chatter. All agent inputs, telemetry, and actions are coordinated through the **Central Brain State Machine**:

```
[OBSERVING] ──► [ANALYZING] ──► [SIGNAL_DETECTED] ──► [VALIDATING] ──► [SIMULATING]
                                                                            │
[AUDITED] ◄── [CLOSED] ◄── [POSITION_MONITORING] ◄── [PAPER_ORDER] ◄── [RISK_REVIEW]
```

```
                               ┌─────────────────┐
                               │  CENTRAL BRAIN  │
                               │  State Machine  │
                               └────────┬────────┘
             ┌──────────────────────────┼──────────────────────────┐
             ▼                          ▼                          ▼
    ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
    │ Market Scanner  │        │ Signal Validator│        │  Risk Manager   │
    │ Regime & Symbol │        │ Multi-Timeframe │        │ Capital Sizing  │
    └─────────────────┘        └─────────────────┘        └─────────────────┘
             ▼                          ▼                          ▼
    ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
    │  Trend Analyst  │        │Momentum Analyst │        │ Volume Analyst  │
    │ EMA & ADX Trend │        │ RSI, MACD Bias  │        │ VWAP & Profile  │
    └─────────────────┘        └─────────────────┘        └─────────────────┘
             ▼                          ▼                          ▼
    ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
    │  News Analyst   │        │Strategy Analyst │        │Execution Manager│
    │ Deterministic V1│        │ Signal Factory  │        │ Paper Simulator │
    └─────────────────┘        └─────────────────┘        └─────────────────┘
                                        ▼
                               ┌─────────────────┐
                               │ Perf. Auditor   │
                               │ Post-Trade Telem│
                               └─────────────────┘
```

1. **Market Scanner (`market_scanner`)**: Scans registered pairs on closed candles to detect current volatility regimes.
2. **Trend Analyst (`trend_analyst`)**: Measures exponential moving average alignments (EMA 20/50/200) and directional strength (ADX).
3. **Momentum Analyst (`momentum_analyst`)**: Computes RSI divergences, MACD histogram velocity, and overbought/oversold boundaries.
4. **Volume Analyst (`volume_analyst`)**: Assesses volume moving average spikes and VWAP deviations to prevent low-liquidity entries.
5. **News Analyst (`news_analyst`)**: Parses macro economic headlines and sentiment scores via deterministic heuristics.
6. **Strategy Analyst (`strategy_analyst`)**: Evaluates multi-timeframe rulesets (`DualTimeframeTrendV2`) and constructs raw order setups.
7. **Signal Validator (`signal_validator`)**: Verifies alignment between higher-timeframe trends (4h) and lower-timeframe execution triggers (1h).
8. **Risk Manager (`risk_manager`)**: **Sole authorizing gatekeeper**. Enforces strict 0.5% risk limits, circuit breakers, and CPPI position sizing.
9. **Execution Manager (`execution_manager`)**: Manages the paper order lifecycle, applying realistic bid/ask spreads, exchange fees, and slippage.
10. **Performance Auditor (`performance_auditor`)**: Evaluates completed trade batches, tracking real-world R-multiples, Sharpe ratio, and slippage drift.

---

## ⚡ The Algorithm: Dual-Timeframe Trend V2 with Macro Gating (unprofitable after look-ahead fix — kept for reference)

Full quantitative formulations and pseudocode are maintained in [`algo.md`](algo.md).

### 1. Macro Trend Filter (4-Hour Bar)
A symbol is eligible for long swing entries if and only if:
$$\text{Close}_{4h} > \text{EMA}_{50}(4h) > \text{EMA}_{200}(4h) \quad \text{and} \quad \text{ADX}_{14}(4h) \ge 24$$

### 2. Bitcoin Macro Shield (`btc_macro_gating = True`)
Altcoins (`ETHUSDT`, `BNBUSDT`) cannot enter long positions unless Bitcoin (`BTCUSDT`) is also in a confirmed 4-hour bull trend. This single filter eliminated over 70% of altcoin bear traps during 2026.

### 3. Execution Trigger (1-Hour Bar)
Entries occur strictly on healthy pullbacks into dynamic value:
1. Short-term trend aligned: $\text{EMA}_{21}(1h) > \text{EMA}_{55}(1h)$
2. Pullback zone: $40 \le \text{RSI}_{14}(1h) \le 52$
3. Dynamic support touch: $\text{Low}_{1h} \le \text{EMA}_{21}(1h)$
4. Reversal confirmation: Bullish candle close with $\text{Close}_{1h} > \text{Open}_{1h}$

### 4. Dynamic Two-Stage Ratchet Exit Mechanism
- **Initial Protective Stop:** Placed at swing low with minimum 1.5% distance.
- **Stage 1 (Breakeven):** When unrealized profit reaches $+1.0R$, stop immediately moves to entry price ($0.0R$).
- **Stage 2 (Profit Lock):** When unrealized profit reaches $+2.0R$, stop ratchets to lock in $+1.0R$ guaranteed profit.
- **Take-Profit Target:** Set at $+2.5R$ with active trailing above target.

---

## 🖥️ Live Market & Agent Dashboard (default page)

Open `http://localhost:3000`; it goes to **Live Market & Agent**, built to be understood without finance knowledge:

- **Market switcher:** Bitcoin / Ethereum / BNB cards with live price and a badge (*Holding* or *In cash*).
- **Live candlestick chart** (Binance public stream, read-only) with Daily / 4h / 1h / 15m / 1m views.
- **Agent arrows:** on the Daily view, green ▲ BOUGHT and red ▼ SOLD (with result after fees) mark every move, plus dashed lines where the agent would act next.
- **Agent panel:** plain-English status ("keeping its money in cash… will buy if a day closes above $X").
- **Activity feed:** every buy/sell with a one-line reason; live banner when a new trade happens, and "heads up" notes when price crosses a trigger line.
- **Practice wallet:** a $1,000 paper account (start Jan 2024/2025/2026) showing cash, coins held and total value after **every** trade, with fees.

**UI design (2026-11-14):** premium dark theme with a single iris accent, glass-style surfaces, smooth curved chart lines and curved (wavy) underlines instead of straight ones. Fully responsive: sidebar on desktop (≥1024px), sticky top bar with slide-in menu on tablet/phone, stacked market cards, horizontally scrollable switchers and wallet table. Shared chart styling lives in `frontend/components/live/chartTheme.ts`; design tokens in `frontend/tailwind.config.js` and `frontend/app/globals.css`.

Only the strategy agent is implemented and shown; the other nine specialist agents are specified but not active, and no activity is invented for them.

API: `GET /api/v1/daily-trend`, `/api/v1/daily-trend/agent/{symbol}`, `/api/v1/daily-trend/account?start=`, `/api/v1/simulation/{2024|2025|2026}`.

---

## 🖥️ Interactive Command Center (legacy explainer — contains superseded V2 figures)

The Next.js 14 frontend includes a dedicated **Command Center** dashboard designed for complete transparency into the algorithmic engine:

- **Tab 1: Overview & Telemetry:** Real-time capital balance, CPPI cushion gauge, daily loss circuit-breaker bar, live prices, and 10-agent health checks.
- **Tab 2: How The Algorithm Works:** Step-by-step visual explainer breaking down why each mathematical indicator exists.
- **Tab 3: Ten Specialist Agents:** Interactive cards displaying each agent's trigger, inputs, actions, and architectural rationale.
- **Tab 4: Interactive Capital Simulator:** Dynamic position calculator testing any capital size ($50, $100, $1,000, $10,000) with real-time risk budgeting (0.5%), stop loss, breakeven trigger, and profit lock values.
- **Tab 5: 3-Year Stress Test Proof:** Audited year-by-year performance metrics across the 2024, 2025, and 2026 crypto cycles.

---

## 📁 Repository Structure

```
Trading_bot/
├── algo.md                 # Complete Mathematical & Algorithmic Blueprint
├── AGENTS.md               # Persistent Engineering & Architecture Rules
├── README.md               # System Overview & Quick Start
├── docs/                   # Full Technical Documentation & Architecture
│   ├── ARCHITECTURE_DECISIONS.md # ADR Register (ADR-001 through ADR-037)
│   ├── PRD.md              # Product Requirements Document
│   └── research/           # Empirical Research Papers & OOS Ledgers
│       ├── NEPTUNE_SHR001_V2_OOS_2026_REPORT.md
│       └── NEPTUNE_STRATEGY_HYPOTHESIS_REGISTER.md
├── scripts/                # fetch_daily_history.py, universe_test.py
├── backend/                # FastAPI Modular Monolith
│   ├── app/
│   │   ├── api/            # REST & WebSocket Endpoints
│   │   ├── brain/          # Central Brain State Machine
│   │   ├── domain/         # Clean Architecture Entities & Models
│   │   ├── risk/           # CPPI Engine, Risk Limits, Circuit Breakers
│   │   ├── simulation/     # Historical & Monte Carlo Simulation Runners
│   │   └── strategies/     # daily_trend_v1 (current), DualTimeframeTrendV2 (superseded)
│   └── tests/              # Pytest Test Suites (Unit, Integration, Simulation)
├── frontend/               # Next.js 14 / TypeScript Web Application
│   ├── app/                # App Router Layouts & Pages
│   │   └── (dashboard)/
│   │       ├── live-markets/   # Live Market & Agent dashboard (home)
│   │       └── command-center/ # Legacy explainer (superseded V2 figures)
│   ├── components/         # Modular Atomic UI Components
│   └── lib/                # API Clients, Zustand Stores, Type Definitions
└── storage/                # Persistent Local Parquet & SQLite Data (Git-ignored)
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python 3.12+**
- **Node.js 20+**
- **Git**

### 1. Clone & Configure
```bash
git clone https://github.com/hossaintaufiq/Trading_Bot.git
cd Trading_Bot

# Copy environment template
cp .env.example .env
```

### 2. Start the Backend API
```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
*API Swagger Documentation available at:* `http://127.0.0.1:8000/docs`

### 3. Start the Frontend Command Center
```bash
cd frontend
npm install
npm run dev
```
*Open your browser at:* `http://localhost:3000` (Live Market & Agent) — also `/command-center`

### 4. Download data and run the research
```bash
# Daily history (public Binance market data, no keys) -> storage/research/daily/
python scripts/fetch_daily_history.py

# Decimal-accounted backtest of daily_trend_v1 (train 2018-23, test 2024-26)
cd backend && python -m app.simulation.daily_trend_backtest && cd ..

# 36-coin robustness check
python scripts/universe_test.py

# Full test suite (run from the repo root)
python -m pytest backend/tests/unit -c backend/pytest.ini --rootdir=.
```

---

## 🛡️ Absolute Safety & Engineering Rules

In accordance with [AGENTS.md](AGENTS.md):

| Rule ID | Mandate | Rationale |
|:---:|---|---|
| **S-01** | **Paper Trading Only** | No real-money exchange APIs or wallet connections in v1. |
| **S-02** | **Credential Protection** | Zero secrets, private keys, or real API credentials committed or logged. |
| **S-04** | **Unbypasable Risk Gate** | Every single paper order must be validated and authorized by the Risk Manager. |
| **S-05** | **Zero Look-Ahead Bias** | Strictly closed candles consumed; no future data used in backtests or simulations. |
| **S-08** | **SQLite + Parquet Only** | No heavy distributed database or external cloud dependencies in v1. |
| **A-01** | **Decimal Precision** | Monetary calculations use Python `Decimal` or integer cents, never `float`. |
| **A-06** | **Central Brain Mediation** | Agents never communicate directly; all signals flow through the Central Brain. |

---

## 📜 Research & Legal Disclaimer

*NEPTUNE is an open-source quantitative research and educational platform. Simulated historical backtests and paper-trading performance are non-predictive of future financial returns. Cryptocurrency markets involve significant risk of total capital loss. This software does not provide financial, investment, legal, or tax advice.*

---

<p align="center">
  <b>Built for rigorous quantitative research and capital preservation.</b><br>
  <sub>Designed and engineered in 2026.</sub>
</p>
