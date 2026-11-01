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
