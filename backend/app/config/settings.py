"""
NEPTUNE Backend Configuration
All settings loaded from environment variables / .env file.
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    app_name: str = "NEPTUNE"
    app_version: str = "0.1.0"
    log_level: str = "DEBUG"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    backend_reload: bool = True
    backend_workers: int = 1

    # Storage
    database_url: str = "sqlite+aiosqlite:///./storage/db/neptune.db"
    historical_data_dir: str = "./storage/historical"
    simulation_data_dir: str = "./storage/simulations"

    # Market Data
    binance_rest_base_url: str = "https://api.binance.com"
    binance_ws_base_url: str = "wss://stream.binance.com:9443/ws"
    tracked_symbols: str = "BTCUSDT,ETHUSDT,BNBUSDT"
    tracked_timeframes: str = "15m,1h,4h"
    historical_backfill_limit: int = 1000

    # Paper Trading
    paper_starting_equity: float = 1000.0
    paper_maker_fee: float = 0.001
    paper_taker_fee: float = 0.001
    paper_slippage_pct: float = 0.0005

    # Risk Manager
    risk_max_concurrent_positions: int = 2
    risk_max_risk_per_trade_pct: float = 0.005
    risk_daily_loss_limit_pct: float = 0.02
    risk_max_drawdown_pct: float = 0.05
    risk_min_reward_risk_ratio: float = 1.5

    # Simulation
    sim_num_paths: int = 1000
    sim_default_method: str = "block_bootstrap"
    sim_max_horizon_candles: int = 96

    # Central Brain
    brain_scan_interval_seconds: int = 15
    brain_signal_expiry_seconds: int = 3600

    # Security
    secret_key: str = "CHANGE_ME_IN_PRODUCTION"
    cors_origins: List[str] = ["http://localhost:3000"]

    # Exchange API — MUST remain empty in v1
    exchange_api_key: str = ""
    exchange_api_secret: str = ""

    @field_validator("exchange_api_key", "exchange_api_secret")
    @classmethod
    def must_be_empty_in_v1(cls, v: str) -> str:
        """Guard rail: real exchange credentials are forbidden in v1."""
        if v and v.strip():
            raise ValueError(
                "Real exchange API credentials are forbidden in v1. "
                "NEPTUNE is a paper-trading platform only."
            )
        return v

    @property
    def symbols_list(self) -> List[str]:
        return [s.strip() for s in self.tracked_symbols.split(",")]

    @property
    def timeframes_list(self) -> List[str]:
        return [t.strip() for t in self.tracked_timeframes.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
