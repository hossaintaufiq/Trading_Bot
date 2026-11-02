"""
NEPTUNE Model-Agnostic Financial Forecasting Contract (`forecasting.py`)

Architectural preparation for future integration of pre-trained financial forecasting models
(e.g., Kronos, Chronos, TimesFM) per ADR-021.

Principles:
- Strict model independence: No hardcoded dependencies on Kronos or proprietary libraries.
- Strict look-ahead bias prevention: ForecastInput requires past closed candles and input fingerprint.
- Research isolation: Forecasts cannot directly authorize paper orders (Rule S-01, S-04).
- Deterministic validation and distribution uncertainty modeling.
"""
from abc import abstractmethod
from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, List, Optional, Protocol
from pydantic import BaseModel, Field, field_validator

from app.data.market.validator import ValidatedCandle


class ForecastCandle(BaseModel):
    """Single forecasted forward OHLCV observation."""
    step: int = Field(ge=1, description="Step index ahead into horizon (1, 2, ...)")
    timestamp: str = Field(description="Projected ISO 8601 UTC timestamp")
    open: float = Field(gt=0.0)
    high: float = Field(gt=0.0)
    low: float = Field(gt=0.0)
    close: float = Field(gt=0.0)
    volume: float = Field(ge=0.0)
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None


class ForecastInput(BaseModel):
    """
    Standardized, model-independent forecasting request payload.
    """
    symbol: str
    timeframe: str
    historical_sequence: List[ValidatedCandle]
    sequence_length: int = Field(ge=10, description="Number of past bars provided")
    dataset_id: str = Field(description="Provenance ID of the input dataset")
    forecast_horizon: int = Field(ge=1, le=100, description="Number of future bars to forecast")
    model_identifier: str = Field(description="e.g. 'kronos-base', 'mock-random-walk'")
    model_version: str = Field(description="e.g. 'v1.0.0'")

    @field_validator("historical_sequence")
    @classmethod
    def validate_sequence_not_empty(cls, v: List[ValidatedCandle]) -> List[ValidatedCandle]:
        if not v:
            raise ValueError("historical_sequence must contain at least 1 validated candle.")
        return v

    def compute_input_fingerprint(self) -> str:
        """Compute cryptographic hash of the input sequence to prove no look-ahead tampering."""
        raw_str = f"{self.dataset_id}:{self.symbol}:{self.timeframe}:" + ";".join(
            f"{c.timestamp}:{c.open}:{c.high}:{c.low}:{c.close}:{c.volume}"
            for c in self.historical_sequence
        )
        return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


class ForecastOutput(BaseModel):
    """
    Standardized, model-independent forecasting response payload.
    """
    symbol: str
    timeframe: str
    forecasted_sequence: List[ForecastCandle]
    forecast_horizon: int
    model_identifier: str
    model_version: str
    input_dataset_fingerprint: str
    generation_timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    uncertainty_distribution: Optional[Dict[str, Any]] = None
    validation_metadata: Dict[str, Any] = Field(default_factory=dict)


class IForecaster(Protocol):
    """Protocol for financial time-series forecasters."""

    @abstractmethod
    async def forecast(self, input_payload: ForecastInput) -> ForecastOutput:
        """Generate forward forecast for the given historical sequence."""
        ...


class MockAgnosticForecaster:
    """
    Lightweight, model-free deterministic stub for testing forecasting contracts
    and research pipelines without downloading weights or installing heavy PyTorch runtimes.
    """

    def __init__(self, model_identifier: str = "mock-linear-extrapolation", model_version: str = "v1.0.0"):
        self.model_identifier = model_identifier
        self.model_version = model_version

    async def forecast(self, input_payload: ForecastInput) -> ForecastOutput:
        fingerprint = input_payload.compute_input_fingerprint()
        last_candle = input_payload.historical_sequence[-1]
        last_close = last_candle.close

        forecasted_bars: List[ForecastCandle] = []
        for step in range(1, input_payload.forecast_horizon + 1):
            projected_close = last_close * (1.0 + 0.0005 * step)
            forecasted_bars.append(ForecastCandle(
                step=step,
                timestamp=f"projected-T+{step}",
                open=last_close,
                high=projected_close * 1.002,
                low=last_close * 0.998,
                close=projected_close,
                volume=last_candle.volume,
                confidence_lower=projected_close * 0.99,
                confidence_upper=projected_close * 1.01,
            ))

        return ForecastOutput(
            symbol=input_payload.symbol,
            timeframe=input_payload.timeframe,
            forecasted_sequence=forecasted_bars,
            forecast_horizon=input_payload.forecast_horizon,
            model_identifier=self.model_identifier,
            model_version=self.model_version,
            input_dataset_fingerprint=fingerprint,
            uncertainty_distribution={"distribution": "gaussian", "std_dev": 0.01},
            validation_metadata={"mock": True, "input_len": len(input_payload.historical_sequence)},
        )

