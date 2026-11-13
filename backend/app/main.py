"""
NEPTUNE Backend — Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import get_settings

settings = get_settings()

app = FastAPI(
    title="NEPTUNE — Autonomous Market Intelligence",
    description=(
        "Paper trading and market research platform. "
        "No real-money execution. No real credentials."
    ),
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", tags=["System"])
async def health() -> dict:
    """System health check endpoint."""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "paper_trading_only": True,
        "real_money_trading": False,
    }



# ---- Simulation results (read-only, served from exported research artifacts) ----
import json as _json
from pathlib import Path as _Path

_EXPORT_ROOT = _Path(__file__).resolve().parents[2] / "storage" / "exports"
_SIM_RUNS = {
    "2024": "dual_timeframe_v2_dev_experiment",
    "2025": "dual_timeframe_v2_val2025_experiment",
    "2026": "dual_timeframe_v2_oos2026_experiment",
}


def _load_export(run: str, name: str):
    path = _EXPORT_ROOT / _SIM_RUNS[run] / name
    if not path.exists():
        return None
    return _json.loads(path.read_text(encoding="utf-8"))


@app.get("/api/v1/simulation/{run}", tags=["Simulation"])
async def simulation_results(run: str) -> dict:
    """Return summary, equity curve and trade ledger of a completed paper simulation."""
    if run not in _SIM_RUNS:
        return {"error": f"unknown run '{run}'", "available": list(_SIM_RUNS)}
    return {
        "run": run,
        "summary": _load_export(run, "summary_metrics.json"),
        "equity_curve": _load_export(run, "equity_curve.json"),
        "trades": _load_export(run, "trade_ledger.json"),
    }


# ---- Daily trend strategy (ADR-037): backtest summary + current paper state ----
@app.get("/api/v1/daily-trend", tags=["Simulation"])
async def daily_trend_status() -> dict:
    from app.simulation.daily_trend_backtest import buy_and_hold, load_daily, run_portfolio
    from app.strategies.daily_trend import DailyTrendStrategy

    syms = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
    strat = DailyTrendStrategy()
    out = {"strategy_id": strat.strategy_id, "paper_only": True, "periods": {}, "current": []}
    for label, a, b in [("train_2018_2023", "2018-01-01", "2023-12-31"), ("test_2024_2026", "2024-01-01", "2026-12-31")]:
        r = run_portfolio(syms, a, b)
        curve = r["equity_curve"]
        out["periods"][label] = {
            "net_return_pct": float(r["net_return_pct"]), "max_drawdown_pct": float(r["max_drawdown_pct"]),
            "trades": len(r["trades"]), "wins": sum(1 for t in r["trades"] if t.net_pnl > 0),
            "fees": float(r["total_fees"]), "buy_hold_pct": float(buy_and_hold(syms, a, curve[-1][0])),
            "equity_curve": [{"date": d, "equity": float(e)} for d, e in curve[:: max(1, len(curve) // 400)]],
        }
    for s in syms:
        df = load_daily(s)
        out["current"].append({"symbol": s, "as_of": df["timestamp"].iloc[-1].strftime("%Y-%m-%d"),
                               "last_close": float(df["close"].iloc[-1]),
                               "position": "LONG" if strat.position_state(df) == 1 else "FLAT"})
    return out


# ---- Agent trade markers + trigger levels for the chart (ADR-037) ----
_AGENT_CACHE: dict = {}


@app.get("/api/v1/daily-trend/agent/{symbol}", tags=["Simulation"])
async def daily_trend_agent(symbol: str) -> dict:
    """Every BUY/SELL the daily_trend_v1 paper agent made on `symbol`, plus its next trigger levels."""
    from decimal import Decimal

    from app.simulation.daily_trend_backtest import FEE, load_daily, run_sleeve
    from app.strategies.daily_trend import DailyTrendConfig, compute_positions

    import asyncio

    from app.data.market.daily_history import refresh_if_stale

    symbol = symbol.upper()
    if symbol not in ("BTCUSDT", "ETHUSDT", "BNBUSDT"):
        return {"error": "unsupported symbol"}
    await asyncio.get_running_loop().run_in_executor(None, refresh_if_stale, symbol)  # pick up new closed candles
    df = load_daily(symbol)
    key = (symbol, str(df["timestamp"].iloc[-1]))
    if key not in _AGENT_CACHE:
        cfg = DailyTrendConfig()
        res = run_sleeve(symbol, df, Decimal("1000"), cfg)
        closes = [float(x) for x in df["close"]]
        pos = compute_positions(closes, cfg.entry_lookback, cfg.exit_lookback)
        markers = []
        for t in res.trades:
            markers.append({"time": t.entry_time, "side": "BUY", "price": float(t.entry_price)})
            markers.append({"time": t.exit_time, "side": "SELL", "price": float(t.exit_price),
                            "pct": float((t.exit_price / t.entry_price * (1 - FEE) / (1 + FEE) - 1) * 100)})
        # open position (bought, not yet sold): last flat->long flip, filled at the following open
        if pos[-1] == 1:
            j = len(pos) - 1
            while j > 0 and pos[j - 1] == 1:
                j -= 1
            if j + 1 < len(df):
                markers.append({"time": df["timestamp"].iloc[j + 1].strftime("%Y-%m-%d"), "side": "BUY",
                                "price": float(df["open"].iloc[j + 1]), "open": True})
        _AGENT_CACHE.clear()
        _AGENT_CACHE[key] = {
            "symbol": symbol, "as_of": df["timestamp"].iloc[-1].strftime("%Y-%m-%d"),
            "position": "LONG" if pos[-1] == 1 else "FLAT", "last_close": closes[-1],
            "buy_above": max(closes[-cfg.entry_lookback:]), "sell_below": min(closes[-cfg.exit_lookback:]),
            "markers": markers,
        }
    return _AGENT_CACHE[key]


@app.get("/api/v1/daily-trend/account", tags=["Simulation"])
async def daily_trend_account(start: str = "2024-01-01") -> dict:
    """Paper-money account: cash, coins and total value after every agent trade, opened flat on `start`."""
    from decimal import Decimal

    from app.simulation.daily_trend_backtest import run_account

    if start not in ("2024-01-01", "2025-01-01", "2026-01-01"):
        return {"error": "start must be 2024-01-01, 2025-01-01 or 2026-01-01"}
    return run_account(["BTCUSDT", "ETHUSDT", "BNBUSDT"], start, Decimal("1000"))
