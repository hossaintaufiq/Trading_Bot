"""
FastAPI Server & WebSocket Gateway for Binance Trading Bot.
Serves the modern frontend dashboard and provides real-time bi-directional
telemetry via WebSockets.
"""

import asyncio
from contextlib import asynccontextmanager
import json
import logging
import os
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from bot_engine import BotEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("server")

# Global Engine instance
engine: BotEngine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine
    engine = BotEngine(config_path="config.json")
    # Launch engine initialization in background
    asyncio.create_task(engine.initialize())
    logger.info("Bot Engine startup initiated.")
    yield
    if engine and engine.binance_service:
        await engine.binance_service.stop_websocket()
    logger.info("Server shutdown complete.")


app = FastAPI(title="Binance Trading Bot & Dashboard", lifespan=lifespan)

# Mount static web directory
app.mount("/static", StaticFiles(directory="web"), name="static")


@app.get("/")
async def get_index():
    """Serve the single page application dashboard."""
    index_path = os.path.join("web", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"status": "UI loading..."})


@app.get("/api/status")
async def get_status():
    """Retrieve current bot status, portfolio metrics, and indicators."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    return engine.get_telemetry_snapshot()


@app.post("/api/bot/start")
async def start_bot():
    """Activate trading bot execution."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    engine.start_bot()
    return {"success": True, "status": engine.status}


@app.post("/api/bot/stop")
async def stop_bot():
    """Pause trading bot execution."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    engine.stop_bot()
    return {"success": True, "status": engine.status}


@app.post("/api/bot/panic")
async def panic_exit():
    """Emergency liquidate active position and pause bot."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    await engine.panic_exit()
    return {"success": True, "status": engine.status}


@app.post("/api/bot/reset-paper")
async def reset_paper():
    """Reset paper trading balance to initial amount."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    engine.reset_paper_wallet()
    return {"success": True, "message": "Paper wallet successfully reset."}


class ManualBuyPayload(BaseModel):
    symbol: Optional[str] = None
    amount: Optional[float] = None


@app.post("/api/bot/manual-buy")
async def manual_buy(payload: Optional[ManualBuyPayload] = None):
    """Manually trigger an immediate test buy order for a specific symbol or active symbol."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    sym = payload.symbol if payload else None
    amt = payload.amount if payload else None
    res = await engine.manual_buy(symbol=sym, amount_usdt=amt)
    return res


class SwitchMarketPayload(BaseModel):
    symbol: str


@app.post("/api/market/switch")
async def switch_market(payload: SwitchMarketPayload):
    """Switch active display chart and market focus."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    await engine.switch_market(payload.symbol)
    return {"success": True, "symbol": engine.symbol}


class ClosePositionPayload(BaseModel):
    symbol: str


@app.post("/api/bot/close-position")
async def close_position(payload: ClosePositionPayload):
    """Liquidate a specific position in the basket."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    px = engine.markets.get(payload.symbol, {}).get("current_price", engine.current_price)
    await engine._execute_sell(payload.symbol, px, "MANUAL POSITION CLOSE")
    return {"success": True, "symbol": payload.symbol}


class TimeMachinePayload(BaseModel):
    symbol: Optional[str] = None
    replays: Optional[int] = 1000
    horizon: Optional[int] = 30
    target_mode: Optional[str] = "2R"


@app.post("/api/bot/time-machine/run")
async def run_time_machine(payload: Optional[TimeMachinePayload] = None):
    """Trigger dynamic Monte Carlo Time Machine simulation with customizable parameters."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    sym = payload.symbol if payload else None
    replays = payload.replays if payload and payload.replays else 1000
    horizon = payload.horizon if payload and payload.horizon else 30
    target_mode = payload.target_mode if payload and payload.target_mode else "2R"

    res = engine.run_custom_time_machine(
        symbol=sym,
        replays=replays,
        horizon=horizon,
        target_mode=target_mode
    )
    return res


class MoneyManagementPayload(BaseModel):
    total_budget_limit_usd: Optional[float] = None
    budget_allocation_mode: Optional[str] = None
    max_open_positions: Optional[int] = None
    max_session_loss_usd: Optional[float] = None
    breakeven_lock_enabled: Optional[bool] = None
    breakeven_trigger_pct: Optional[float] = None


@app.post("/api/money-management/update")
async def update_money_management(payload: MoneyManagementPayload):
    """Update dynamic money management parameters (total budget, slot division, loss limit)."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")

    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    engine.config.update(updates)
    engine.money_manager.update_config(engine.config)
    engine.max_open_positions = engine.money_manager.max_open_positions
    engine.save_config()

    summary = engine.money_manager.get_summary(engine.paper_exchange.positions, engine.paper_exchange.usdt_balance)
    engine.log("INFO", f"💰 Money Management updated: Total Budget ${summary['total_budget_limit_usd']:,.2f} | Mode: {summary['allocation_mode']} | Slots: {summary['max_open_positions']} (${summary['per_slot_budget_usd']:,.2f}/slot)")
    return {"success": True, "money_management": summary}


@app.post("/api/money-management/reset-circuit-breaker")
async def reset_circuit_breaker():
    """Reset session loss circuit breaker and allow new entries."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    engine.money_manager.reset_session_loss()
    if engine.status == "CIRCUIT_BREAKER_HALTED":
        engine.status = "RUNNING"
        engine.is_running = True
    engine.log("INFO", "🔄 Circuit breaker manually reset by user. Trading resumed.")
    return {"success": True, "status": engine.status}


@app.get("/api/reports/sub-bots")
async def get_sub_bots_report():
    """Get performance analytics breakdown for all 6 sub-bots and equity history."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    report = engine.paper_exchange.get_daily_report()
    summary = engine.paper_exchange.get_portfolio_summary({engine.symbol: engine.current_price})
    bots_dict = report.get("bot_breakdown", {})
    regime = getattr(engine, "current_regime", {
        "regime": "RANGING_CHOP",
        "adx": 18.0,
        "description": "Sideways market consolidation"
    })
    return {
        "success": True,
        "sub_bots": bots_dict,
        "bot_breakdown": bots_dict,
        "market_regime": regime,
        "equity_history": summary.get("equity_history", []),
        "win_rate_pct": summary.get("win_rate_pct", 0.0),
        "total_realized_pnl": summary.get("total_realized_pnl", 0.0)
    }


@app.get("/api/reports/daily-summary")
async def get_daily_summary():
    """Get comprehensive 24-hour test session analytics for review before real money."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    return engine.paper_exchange.get_daily_report()


@app.get("/api/reports/trades.csv")
async def export_trades_csv():
    """Export complete trade audit log to CSV spreadsheet format."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    csv_content = engine.paper_exchange.generate_trades_csv()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=neptune_trades_report.csv"}
    )


@app.get("/api/learning/insights")
async def get_learning_insights():
    """Retrieve local autonomous learning memory and adaptive strategy weights."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    return engine.paper_exchange.learning_engine.get_learning_insights()


@app.post("/api/learning/reset")
async def reset_learning_memory():
    """Reset local learning memory to default prior weights."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    engine.paper_exchange.learning_engine.reset_learning_memory()
    return {"success": True, "message": "Local learning memory reset."}


class ValidateBinancePayload(BaseModel):
    api_key: str
    api_secret: str
    is_testnet: bool = False


@app.post("/api/binance/validate")
async def validate_binance_credentials(payload: ValidateBinancePayload):
    """Verify Binance API credentials and check balance before live activation."""
    from binance_service import BinanceService
    res = await BinanceService.validate_credentials(
        api_key=payload.api_key,
        api_secret=payload.api_secret,
        is_testnet=payload.is_testnet
    )
    return res


class ConfigPayload(BaseModel):
    mode: str = "PAPER"
    symbol: str = "BTC/USDT"
    timeframe: str = "1m"
    active_strategy: str = "neptune_fleet"
    trade_amount_usdt: float = 100.0
    total_budget_limit_usd: Optional[float] = 200.0
    budget_allocation_mode: Optional[str] = "EQUAL_SPLIT"
    max_open_positions: Optional[int] = 4
    max_session_loss_usd: Optional[float] = 25.0
    breakeven_lock_enabled: Optional[bool] = True
    stop_loss_pct: float = 1.5
    take_profit_pct: float = 3.0
    trailing_stop_enabled: bool = False
    trailing_stop_pct: float = 1.0
    binance_testnet: Dict[str, str] = {}
    binance_live: Dict[str, str] = {}
    strategies: Dict[str, Any] = {}


@app.post("/api/config")
async def update_config(payload: ConfigPayload):
    """Update runtime configuration."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    await engine.update_config(payload.model_dump())
    return {"success": True, "config": engine.config}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """High-frequency real-time WebSocket connection for telemetry and charts."""
    await websocket.accept()
    queue = asyncio.Queue(maxsize=100)

    if engine:
        engine.ws_subscribers.append(queue)
        # Send initial full state immediately upon connection
        snapshot = engine.get_telemetry_snapshot()
        await websocket.send_text(json.dumps({"type": "INITIAL_STATE", "data": snapshot}))

    async def sender():
        try:
            while True:
                msg = await queue.get()
                await websocket.send_text(json.dumps(msg))
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass

    sender_task = asyncio.create_task(sender())

    try:
        while True:
            # Handle messages from the UI (pings, quick actions)
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
                action = data.get("action")
                if action == "PING":
                    await websocket.send_text(json.dumps({"type": "PONG", "time": data.get("time")}))
                elif action == "START_BOT":
                    engine.start_bot()
                elif action == "STOP_BOT":
                    engine.stop_bot()
                elif action == "PANIC":
                    await engine.panic_exit()
            except Exception:
                pass
    except WebSocketDisconnect:
        pass
    finally:
        sender_task.cancel()
        if engine and queue in engine.ws_subscribers:
            engine.ws_subscribers.remove(queue)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=False)
