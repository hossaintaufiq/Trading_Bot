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
