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
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
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


@app.post("/api/bot/manual-buy")
async def manual_buy():
    """Manually trigger an immediate test buy order."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    res = await engine.manual_buy()
    return res


@app.post("/api/bot/time-machine/run")
async def run_time_machine():
    """Trigger on-demand Monte Carlo Time Machine simulation."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine initializing")
    engine._run_skills_scan()
    return {
        "success": True,
        "plan": engine.latest_plan.__dict__ if engine.latest_plan else None,
        "timemachine": engine.latest_timemachine.__dict__ if engine.latest_timemachine else None
    }


class ConfigPayload(BaseModel):
    mode: str = "PAPER"
    symbol: str = "BTC/USDT"
    timeframe: str = "1m"
    active_strategy: str = "ema_rsi"
    trade_amount_usdt: float = 500.0
    stop_loss_pct: float = 1.5
    take_profit_pct: float = 3.0
    trailing_stop_enabled: bool = False
    trailing_stop_pct: float = 1.0
    binance_testnet: Dict[str, str] = {}
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
