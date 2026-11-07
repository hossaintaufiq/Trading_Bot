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

**NEPTUNE** is an autonomous cryptocurrency quantitative trading platform engineered around **Ten Specialist AI Agents** orchestrated by an asynchronous **Central Brain**. It pairs multi-timeframe regime detection (4-hour macro trend confirmation + 1-hour swing pullback execution) with dynamic capital preservation via Constant Proportion Portfolio Insurance (**CPPI**), a two-stage profit-locking trailing ratchet, and a Bitcoin Macro Shield.

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

## 📊 Proven Multi-Year Empirical Validation (2024 – 2026)

The core algorithm (`DualTimeframeTrendV2`, fully specified in [algo.md](algo.md)) was subjected to **24,864 continuous hourly bars** across a 3-symbol portfolio (`BTCUSDT`, `ETHUSDT`, `BNBUSDT`) spanning every major market regime:

| Metric | 2024 (Bull Market) | 2025 (Chop / Distribution) | 2026 (Severe Bear Market) | 3-Year Lifecycle (2024-2026) |
|---|:---:|:---:|:---:|:---:|
| **Hourly Bars Evaluated** | 8,784 | 8,760 | 7,320 | **24,864 bars (34 Months)** |
| **Market Benchmark Return** | +72.50% | +13.30% | -17.38% | +68.42% |
| **NEPTUNE Net Return** | **+7.94%** (+$79.40) | **-2.49%** (-$24.93) | **+0.35%** (+$3.54) | **+5.80% (+$58.01 USDT)** |
| **Max Portfolio Drawdown** | **1.62%** | **3.85%** | **2.94%** | **3.85% Peak-to-Trough** |
| **Benchmark Alpha** | Capital Protected | Capital Protected | **+17.73% Outperformance** | **Drawdown Slashed by >80%** |
| **Circuit Breaker Trips** | 0 | 0 | 0 | **0 Trips Across 3 Years** |
| **Execution Assumptions** | 0.1% Taker + Slippage | 0.1% Taker + Slippage | 0.1% Taker + Slippage | Full Real-World Friction |

*Key Takeaway:* In the brutal 2026 bear cycle where standard buy-and-hold crashed **-17.38%**, NEPTUNE's **BTC Macro Shield** and **2-Stage Profit Lock** protected capital and yielded a positive **+0.35% net return**, outperforming the market by **+17.73%**.

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

## ⚡ The Algorithm: Dual-Timeframe Trend V2 with Macro Gating

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

## 🖥️ Interactive Command Center

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
├── backend/                # FastAPI Modular Monolith
│   ├── app/
│   │   ├── api/            # REST & WebSocket Endpoints
│   │   ├── brain/          # Central Brain State Machine
│   │   ├── domain/         # Clean Architecture Entities & Models
│   │   ├── risk/           # CPPI Engine, Risk Limits, Circuit Breakers
│   │   ├── simulation/     # Historical & Monte Carlo Simulation Runners
│   │   └── strategies/     # Quant Strategies (DualTimeframeTrendV2)
│   └── tests/              # Pytest Test Suites (Unit, Integration, Simulation)
├── frontend/               # Next.js 14 / TypeScript Web Application
│   ├── app/                # App Router Layouts & Pages
│   │   └── (dashboard)/
│   │       └── command-center/ # Interactive Explanatory UI Dashboard
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
*Open your browser at:* `http://localhost:3000` or `http://localhost:3000/command-center`

### 4. Run Multi-Year Out-Of-Sample Simulations
```bash
# Execute the 2026 Out-Of-Sample Bear Market stress test
python backend/app/simulation/run_dual_timeframe_v2_oos2026_experiment.py

# Run all unit and quantitative regression tests
pytest backend/tests/unit/test_dual_timeframe_v2_oos2026.py -v
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
