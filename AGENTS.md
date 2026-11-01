# NEPTUNE — Persistent Engineering Rules

> Version 1.0 — 2026-11-01
> These rules govern every contributor and every AI agent working on this project.
> They may not be changed without an Architecture Decision Record entry.

---

## Purpose

NEPTUNE is an Autonomous Market Intelligence and Paper Trading Platform.
It is a research and educational product. It does not execute real trades.
It does not manage real funds. It does not promise profitability.

---

## Absolute Safety Rules

| ID | Rule | Rationale |
|----|------|-----------|
| S-01 | **Never implement real-money exchange execution.** Paper trading only in v1. | Safety |
| S-02 | **Never expose API keys, secrets, or credentials in code or logs.** | Security |
| S-03 | **Never commit `.env` files.** Use `.env.example` as the template. | Security |
| S-04 | **Never bypass the Risk Manager.** All paper orders must be authorized by the Risk Manager agent. | Integrity |
| S-05 | **Never use future data in simulations or backtests.** Strict look-ahead bias prevention. | Validity |
| S-06 | **Never fabricate market data, agent decisions, or performance metrics.** | Honesty |
| S-07 | **Never claim profitability without validated, reproducible evidence.** | Honesty |
| S-08 | **Never add PostgreSQL in v1.** SQLite only. See ADR-001. | Architecture |
| S-09 | **Never introduce Redis, Kafka, or Kubernetes in v1.** | Architecture |
| S-10 | **Never implement microservices in v1.** Modular monolith only. | Architecture |

---

## Architecture Rules

| ID | Rule |
|----|------|
| A-01 | All monetary calculations use Python `Decimal` or integer cents internally, never `float`. |
| A-02 | All timestamps are stored and processed in UTC. No local time in the database. |
| A-03 | Business logic must not directly depend on SQLite or filesystem implementations. Use repository interfaces. |
| A-04 | Frontend and backend data contracts must be kept in sync. TypeScript types must match Pydantic models. |
| A-05 | Every important architectural decision must be recorded in `docs/ARCHITECTURE_DECISIONS.md`. |
| A-06 | Agents must communicate through the Central Brain. No direct agent-to-agent calls. |
| A-07 | Every agent must implement a structured input and output contract. |
| A-08 | Strategies are independently evaluated. No strategy is assumed profitable without backtest evidence. |
| A-09 | Candle-close strategies must only consume fully closed candles. Never use an in-progress candle for entry signals. |
| A-10 | Paper fills must record execution assumptions: price used, fee applied, slippage applied, timestamp. |

---

## Engineering Standards

| ID | Rule |
|----|------|
| E-01 | Prefer small, single-responsibility modules over large files. Target < 300 lines per module. |
| E-02 | All critical calculations (monetary, risk, simulation) must have unit tests before implementation. |
| E-03 | Use typed Python models (Pydantic) and TypeScript interfaces. No untyped `any` in production code. |
| E-04 | Log errors with enough context to reproduce them: agent ID, signal ID, timestamp, input values. |
| E-05 | Follow clean architecture: separate concerns across API, service, domain, and persistence layers. |
| E-06 | Every paper trade must be fully traceable from signal → validation → simulation → risk approval → fill → close → audit. |
| E-07 | Do not silently change the approved architecture. Document deviations before implementing. |
| E-08 | Keep dependencies minimal. Add a new dependency only when it provides significant value over writing the code directly. |
| E-09 | Use structured logging (JSON format) in production. Human-readable in development. |
| E-10 | Pin all dependency versions in requirements files. |

---

## Forbidden Patterns

```python
# FORBIDDEN: float for monetary calculations
price = 100.1 + 0.2  # floating point error

# CORRECT: use Decimal
from decimal import Decimal
price = Decimal("100.1") + Decimal("0.2")

# FORBIDDEN: using partial/incomplete candles for entry signals
signal = evaluate(df.iloc[-1])  # last candle may be incomplete

# CORRECT: only use confirmed closed candles
closed_candles = df[df["is_closed"] == True]
signal = evaluate(closed_candles.iloc[-1])

# FORBIDDEN: agent calling another agent directly
class TrendAnalyst:
    def execute(self):
        volume = VolumeAnalyst().execute()  # WRONG

# CORRECT: brain mediates all agent communication
class CentralBrain:
    async def orchestrate(self):
        trend = await self.run_agent("trend_analyst", context)
        volume = await self.run_agent("volume_analyst", context)
```

---

## Ten Specialist Agents

| Agent | ID | Trigger | Primary Responsibility |
|-------|----|---------|----------------------|
| Market Scanner | `market_scanner` | Every closed candle | Scan symbols, detect regime, feed context to brain |
| Trend Analyst | `trend_analyst` | On brain request | EMA stack analysis, trend strength (ADX) |
| Momentum Analyst | `momentum_analyst` | On brain request | RSI, MACD, momentum score |
| Volume Analyst | `volume_analyst` | On brain request | Volume profile, VWAP deviation, anomaly |
| News Analyst | `news_analyst` | On brain request | Sentiment scoring (deterministic v1) |
| Strategy Analyst | `strategy_analyst` | On brain request | Evaluate strategies, generate raw signals |
| Signal Validator | `signal_validator` | On new raw signal | Multi-timeframe validation, quality scoring |
| Risk Manager | `risk_manager` | On validated signal | Position sizing, risk checks, authorization |
| Execution Manager | `execution_manager` | On approved signal | Paper order lifecycle, fill simulation |
| Performance Auditor | `performance_auditor` | On trade close | Metrics calculation, anomaly detection |

---

## Central Brain Decision Flow

```
OBSERVING
   └─► ANALYZING          (market scanner triggered)
         └─► SIGNAL_DETECTED   (strategy analyst found setup)
               └─► VALIDATING  (signal validator checks)
                     ├─► REJECTED (signal invalid)
                     └─► SIMULATING   (time machine runs 1000 paths)
                           └─► RISK_REVIEW    (risk manager evaluates)
                                 ├─► REJECTED (risk limits breached)
                                 └─► APPROVED
                                       └─► PAPER_ORDER_CREATED
                                             └─► POSITION_MONITORING
                                                   └─► CLOSED
                                                         └─► AUDITED
```

Every state transition is persisted to `brain_decisions` in SQLite with timestamp, reason, and agent outputs.

---

## Data Rules

| Rule |
|------|
| Historical candles stored in Parquet: `storage/historical/{symbol}/{timeframe}/YYYY/YYYY-MM.parquet` |
| SQLite for all transactional and relational data |
| Simulation outputs stored in Parquet: `storage/simulations/{simulation_id}.parquet` |
| Research exports: `storage/exports/` |
| Never query Parquet files inside a request handler. Load to memory first. |

---

## Paper Trading Defaults (Configurable via .env)

| Parameter | Default | Note |
|-----------|---------|------|
| Starting equity | 1,000 USDT | Experimental default |
| Leverage | Disabled | v1 only |
| Max concurrent positions | 2 | Configurable |
| Max risk per trade | 0.5% of equity | Configurable |
| Daily loss limit | 2% | Configurable |
| Max drawdown circuit breaker | 5% | Configurable |
| Minimum R:R ratio | 1.5:1 | Configurable |
| Maker fee | 0.1% | Binance approximation |
| Taker fee | 0.1% | Binance approximation |
| Slippage | 0.05% per side | Configurable |

These are research defaults. They are not investment recommendations.

---

## Working on This Project

1. Read this file before making changes.
2. Read the relevant `docs/` file for the component you are changing.
3. Write tests before changing any calculation involving money, risk, or position sizing.
4. Record any architectural deviation in `docs/ARCHITECTURE_DECISIONS.md`.
5. Do not commit `.env`, `*.db`, or `*.parquet` files.
6. Do not introduce new dependencies without justification.
7. Run `pytest` before committing backend changes.
8. Run `npm test` before committing frontend changes.

