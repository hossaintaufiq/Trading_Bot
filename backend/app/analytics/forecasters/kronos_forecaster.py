"""
Kronos Foundation Model Forecaster (`kronos_forecaster.py`)

Implements `IForecaster` interface for the Kronos Foundation Model family
(NeoQuasar/Kronos-mini and NeoQuasar/Kronos-Tokenizer-2k).

Principles:
- Strict look-ahead bias prevention: Rejects in-progress candles, validates chronological order.
- Research isolation: Model outputs provide probabilistic intelligence only; cannot execute orders.
- Reproducibility: Cryptographic fingerprinting of inputs and deterministic random seeds.
- Device resilience: Automatic CPU execution on Windows 11 with optional CUDA acceleration.
"""
from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
import torch

from app.analytics.forecasting import ForecastCandle, ForecastInput, ForecastOutput, IForecaster
from app.data.market.validator import CandleValidator, ValidatedCandle
from .kronos_model import Kronos, KronosPredictor, KronosTokenizer

logger = logging.getLogger("neptune.forecasting.kronos")


class KronosForecaster:
    """
    Kronos-mini financial time-series forecaster.
    Encapsulates tokenization, transformer generation, and uncertainty projection.
    """

    def __init__(
        self,
        model_name: str = "NeoQuasar/Kronos-mini",
        tokenizer_name: str = "NeoQuasar/Kronos-Tokenizer-2k",
        device: Optional[str] = "cpu",
        max_context: int = 512,
        temperature: float = 0.8,
        top_p: float = 0.9,
        sample_count: int = 3,
        seed: Optional[int] = 42,
    ):
        self.model_name = model_name
        self.tokenizer_name = tokenizer_name
        self.device = device or ("cuda:0" if torch.cuda.is_available() else "cpu")
        self.max_context = max_context
        self.temperature = temperature
        self.top_p = top_p
        self.sample_count = max(1, sample_count)
        self.seed = seed

        self._model: Optional[Kronos] = None
        self._tokenizer: Optional[KronosTokenizer] = None
        self._predictor: Optional[KronosPredictor] = None
        self._is_loaded: bool = False

    def is_available(self) -> bool:
        """Check if weights are available locally or downloadable."""
        try:
            self._ensure_loaded()
            return True
        except Exception as e:
            logger.warning(f"Kronos model is unavailable: {e}")
            return False

    def _ensure_loaded(self) -> None:
        if self._is_loaded and self._predictor is not None:
            return

        logger.info(f"Loading Kronos tokenizer ({self.tokenizer_name}) and model ({self.model_name}) on {self.device}...")
        self._tokenizer = KronosTokenizer.from_pretrained(self.tokenizer_name)
        self._model = Kronos.from_pretrained(self.model_name)
        self._predictor = KronosPredictor(
            model=self._model,
            tokenizer=self._tokenizer,
            device=self.device,
            max_context=self.max_context,
        )
        self._is_loaded = True
        logger.info("Kronos successfully loaded into memory.")

    def _get_timeframe_delta(self, timeframe: str) -> timedelta:
        minutes = CandleValidator.TIMEFRAME_MINUTES.get(timeframe)
        if minutes is None:
            # Fallback for common patterns
            if timeframe.endswith("m"):
                minutes = int(timeframe[:-1])
            elif timeframe.endswith("h"):
                minutes = int(timeframe[:-1]) * 60
            elif timeframe.endswith("d"):
                minutes = int(timeframe[:-1]) * 1440
            else:
                minutes = 60
        return timedelta(minutes=minutes)

    def _build_future_timestamps(
        self,
        last_dt: datetime,
        delta: timedelta,
        horizon: int,
    ) -> List[datetime]:
        future = []
        cur = last_dt
        for _ in range(horizon):
            cur = cur + delta
            future.append(cur)
        return future

    async def forecast(self, input_payload: ForecastInput) -> ForecastOutput:
        """
        Execute forward forecast on closed historical candle sequence.
        """
        # 1. Look-ahead bias prevention & validation checks
        if not input_payload.historical_sequence:
            raise ValueError("Historical sequence cannot be empty.")

        for i, candle in enumerate(input_payload.historical_sequence):
            if not candle.is_closed:
                raise ValueError(
                    f"Look-ahead violation: Candle index {i} ({candle.timestamp}) is marked incomplete (is_closed=False)."
                )

        # 2. Chronological order check
        timestamps_dt = [c.dt_utc for c in input_payload.historical_sequence]
        for i in range(1, len(timestamps_dt)):
            if timestamps_dt[i] <= timestamps_dt[i - 1]:
                raise ValueError(
                    f"Chronological ordering violation: Candle {timestamps_dt[i]} does not strictly follow {timestamps_dt[i-1]}."
                )

        input_fingerprint = input_payload.compute_input_fingerprint()

        # 3. Model lazy load
        self._ensure_loaded()
        assert self._predictor is not None

        # 4. Set deterministic seed if requested
        if self.seed is not None:
            torch.manual_seed(self.seed)
            np.random.seed(self.seed)

        # 5. Build input DataFrame
        candles = input_payload.historical_sequence
        df_data = {
            "open": [float(c.open) for c in candles],
            "high": [float(c.high) for c in candles],
            "low": [float(c.low) for c in candles],
            "close": [float(c.close) for c in candles],
            "volume": [float(c.volume) for c in candles],
        }
        df_input = pd.DataFrame(df_data)

        # Compute synthetic amount if quote_volume is absent
        quote_vols = [float(c.quote_volume) if c.quote_volume is not None else -1.0 for c in candles]
        if any(qv < 0 for qv in quote_vols):
            df_input["amount"] = df_input["volume"] * (df_input["open"] + df_input["close"]) / 2.0
        else:
            df_input["amount"] = quote_vols

        # 6. Build timestamps
        x_timestamps = pd.Series(timestamps_dt)
        tf_delta = self._get_timeframe_delta(input_payload.timeframe)
        future_dts = self._build_future_timestamps(timestamps_dt[-1], tf_delta, input_payload.forecast_horizon)
        y_timestamps = pd.Series(future_dts)

        # 7. Predict using KronosPredictor
        pred_df = self._predictor.predict(
            df=df_input,
            x_timestamp=x_timestamps,
            y_timestamp=y_timestamps,
            pred_len=input_payload.forecast_horizon,
            T=self.temperature,
            top_p=self.top_p,
            sample_count=self.sample_count,
            verbose=False,
        )

        # 8. Post-process predictions into ForecastCandle
        last_close = float(candles[-1].close)
        forecasted_bars: List[ForecastCandle] = []

        for step_idx in range(len(pred_df)):
            row = pred_df.iloc[step_idx]
            dt_step = future_dts[step_idx]
            ts_str = dt_step.strftime("%Y-%m-%dT%H:%M:%S.000Z")

            o = float(max(1e-4, row["open"]))
            h = float(max(1e-4, row["high"]))
            l = float(max(1e-4, row["low"]))
            c = float(max(1e-4, row["close"]))
            v = float(max(0.0, row["volume"]))

            # Ensure mathematical invariants for OHLC
            h_clean = max(h, o, c)
            l_clean = min(l, o, c)

            # Approximate confidence bands (+- 1.5% volatility scaling per horizon step)
            step_num = step_idx + 1
            vol_spread = 0.008 * np.sqrt(step_num)
            conf_lower = c * (1.0 - vol_spread)
            conf_upper = c * (1.0 + vol_spread)

            forecasted_bars.append(
                ForecastCandle(
                    step=step_num,
                    timestamp=ts_str,
                    open=round(o, 4),
                    high=round(h_clean, 4),
                    low=round(l_clean, 4),
                    close=round(c, 4),
                    volume=round(v, 4),
                    confidence_lower=round(conf_lower, 4),
                    confidence_upper=round(conf_upper, 4),
                )
            )

        # 9. Compute summary uncertainty distribution and metrics
        final_predicted_close = forecasted_bars[-1].close
        predicted_return_pct = round(((final_predicted_close - last_close) / last_close) * 100.0, 4)
        direction = "LONG" if predicted_return_pct > 0 else ("SHORT" if predicted_return_pct < 0 else "FLAT")

        uncertainty_info = {
            "distribution": "autoregressive_token_sample",
            "sample_count": self.sample_count,
            "temperature": self.temperature,
            "last_closed_price": last_close,
            "predicted_final_price": final_predicted_close,
            "predicted_return_pct": predicted_return_pct,
            "predicted_direction": direction,
            "confidence_score": round(min(1.0, abs(predicted_return_pct) / 2.0), 4),
        }

        return ForecastOutput(
            symbol=input_payload.symbol,
            timeframe=input_payload.timeframe,
            forecasted_sequence=forecasted_bars,
            forecast_horizon=input_payload.forecast_horizon,
            model_identifier=self.model_name,
            model_version="kronos-mini-v1",
            input_dataset_fingerprint=input_fingerprint,
            uncertainty_distribution=uncertainty_info,
            validation_metadata={
                "device": str(self.device),
                "input_candle_count": len(candles),
                "last_candle_timestamp": candles[-1].timestamp,
                "first_forecast_timestamp": forecasted_bars[0].timestamp,
                "last_forecast_timestamp": forecasted_bars[-1].timestamp,
                "look_ahead_verified": True,
            },
        )

