# NEPTUNE

**Autonomous Market Intelligence & Paper Trading Platform**

> ⚠️ **Paper Trading Only.** This platform does not execute real trades, manage real funds, or connect to any live exchange account. It is a research and educational tool.

---

## What Is NEPTUNE?

NEPTUNE is an advanced market research and paper-trading platform that coordinates ten specialist AI agents through a central intelligence brain to analyze cryptocurrency markets, generate trading signals, simulate outcomes, and execute paper trades — all without touching real money.

Built for serious research, NEPTUNE provides institutional-quality tooling including:

- Multi-timeframe market analysis (15m / 1h / 4h)
- Ten coordinated specialist agents
- A central brain with a traceable decision state machine
- A Time Machine simulation engine generating 1,000 scenario paths per signal
- Four independent trading strategies with isolated performance tracking
- Realistic paper trading with fees, slippage, and bid/ask spread
- A premium dark-mode dashboard with real-time updates

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js, React, TypeScript, Tailwind CSS, Framer Motion, TradingView Lightweight Charts, Zustand, Zod |
| Backend | Python, FastAPI, Pydantic, asyncio, NumPy, Pandas, SciPy |
| Database | SQLite (transactions) + Parquet (historical data & simulations) |
| Infrastructure | Docker, Docker Compose |
| Testing | Pytest (backend) + Vitest/RTL (frontend) |

---

## Project Structure

```
NEPTUNE/
├── frontend/          # Next.js App Router application
├── backend/           # FastAPI Python application
├── storage/           # Persistent data (excluded from git)
│   ├── historical/    # Parquet candle files
│   ├── simulations/   # Parquet simulation outputs
│   └── db/            # SQLite database files
├── docs/              # Full technical documentation
├── infrastructure/    # Docker configurations
├── scripts/           # Utility and automation scripts
├── .agents/rules/     # Persistent engineering rules
├── AGENTS.md          # Engineering rules (primary reference)
├── .env.example       # Environment configuration template
└── docker-compose.yml # Local orchestration
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker Desktop (Windows)
- Git

### Development Setup

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd Trading_bot

# 2. Copy and configure environment
cp .env.example .env
# Edit .env with your local settings (no API keys needed for paper trading)

# 3. Start the backend
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# 4. Start the frontend (new terminal)
cd frontend
npm install
npm run dev
# Open http://localhost:3000

# 5. Or use Docker Compose
docker-compose up --build
```

---

## Documentation

| Document | Description |
|----------|-------------|
| [PRD](docs/PRD.md) | Product requirements and user stories |
| [System Architecture](docs/SYSTEM_ARCHITECTURE.md) | Full system design and data flow |
| [Frontend Architecture](docs/FRONTEND_ARCHITECTURE.md) | UI structure, stores, design system |
| [Backend Architecture](docs/BACKEND_ARCHITECTURE.md) | FastAPI structure, brain state machine |
| [Agent Specification](docs/AGENT_SPECIFICATION.md) | All 10 agent contracts |
| [Data Architecture](docs/DATA_ARCHITECTURE.md) | SQLite schema, Parquet layout, repositories |
| [Time Machine Spec](docs/TIME_MACHINE_SPECIFICATION.md) | Simulation engine design |
| [Risk Management](docs/RISK_MANAGEMENT.md) | Risk rules and position sizing |
| [API Specification](docs/API_SPECIFICATION.md) | REST and WebSocket API contracts |
| [Development Roadmap](docs/DEVELOPMENT_ROADMAP.md) | 10 milestones from foundation to release |
| [Testing Strategy](docs/TESTING_STRATEGY.md) | Test pyramid and coverage requirements |
| [Architecture Decisions](docs/ARCHITECTURE_DECISIONS.md) | ADR log for all major decisions |

---

## Engineering Rules

Read [AGENTS.md](AGENTS.md) before contributing. Key absolutes:

- 🚫 No real-money trading — ever in v1
- 🚫 No API credentials committed
- 🚫 No PostgreSQL in v1 (SQLite only)
- 🚫 No agent can bypass the Risk Manager
- 🚫 No fabricated data or cherry-picked results
- ✅ Every paper fill has traceable execution assumptions
- ✅ Every strategy is independently evaluated
- ✅ All monetary math uses Decimal, not float

---

## Ten Specialist Agents

| # | Agent | Responsibility |
|---|-------|---------------|
| 1 | Market Scanner | Symbol scanning, regime detection |
| 2 | Trend Analyst | EMA stack, ADX, trend strength |
| 3 | Momentum Analyst | RSI, MACD, momentum scoring |
| 4 | Volume Analyst | Volume profile, VWAP, anomaly detection |
| 5 | News Analyst | Sentiment scoring (deterministic v1) |
| 6 | Strategy Analyst | Strategy evaluation, raw signal generation |
| 7 | Signal Validator | Multi-timeframe validation, quality scoring |
| 8 | Risk Manager | Sole authorization authority for all orders |
| 9 | Execution Manager | Paper order lifecycle, fill simulation |
| 10 | Performance Auditor | Trade metrics, anomaly detection, reporting |

---

## Paper Trading Parameters (Defaults)

| Parameter | Default |
|-----------|---------|
| Starting equity | 1,000 USDT |
| Leverage | Disabled |
| Max concurrent positions | 2 |
| Max risk per trade | 0.5% of equity |
| Daily loss limit | 2% |
| Drawdown circuit breaker | 5% |
| Minimum R:R ratio | 1.5:1 |

> These are experimental research defaults, not investment recommendations.

---

## Status

🏗️ **Foundation Phase** — Architecture established, implementation begins next.

See [Development Roadmap](docs/DEVELOPMENT_ROADMAP.md) for milestones.

---

*NEPTUNE is a research tool. Past simulated performance does not predict future results. This software does not provide financial advice.*
