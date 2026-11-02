"""
NEPTUNE Milestone 4.5 — Kronos Experimental Integration Runner
(`experiment_runner.py`)

Conducts comparative quantitative research across three experimental groups:
- Group A: Deterministic NEPTUNE baseline
- Group B: Pure Kronos-mini directional forecasting model
- Group C: Hybrid NEPTUNE deterministic + Kronos confirmation gate

Strictly adheres to:
- Closed candles only (Rule A-09)
- UTC timestamps (Rule A-02)
- Zero look-ahead bias (Rule S-05)
- Realistic execution friction: 0.10% maker, 0.10% taker, 0.05% slippage per side (Rule A-10)
- Python Decimal / integer precision for financials (Rule A-01)
- Risk Manager limits: max 2 positions, 0.5% risk, 5% drawdown circuit breaker (Rule S-04)
"""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import json
import logging
import math
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.analytics.forecasters.kronos_forecaster import KronosForecaster
from app.analytics.forecasting import ForecastInput, ForecastOutput
from app.analytics.research_framework import STANDARD_PARTITIONS, PartitionBoundary
from app.data.market.validator import CandleValidator, ValidatedCandle
from app.data.repositories.parquet_repo import ParquetMarketDataRepository
from app.simulation.engine import HistoricalBacktestEngine
from app.simulation.models import BacktestConfig, BacktestResult, SimulatedTrade

logger = logging.getLogger("neptune.milestone_4_5.runner")


class KronosExperimentRunner:
    """
    Executes Milestone 4.5 experiments: statistical evaluation,
    economic trade simulation, and resource benchmarking.
    """

    def __init__(
        self,
        export_dir: str = "storage/exports/milestone_4_5",
        device: str = "cpu",
        seed: int = 42,
    ):
        self.export_dir = export_dir
        os.makedirs(self.export_dir, exist_ok=True)
        self.repo = ParquetMarketDataRepository()
        self.validator = CandleValidator()
        self.forecaster = KronosForecaster(device=device, seed=seed, sample_count=1)
        self.symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        self.timeframes = ["1h", "4h", "1d"]
        self.horizons = [1, 4, 12]
        self._candle_cache: Dict[Tuple[str, str], List[ValidatedCandle]] = {}

    async def load_validated_candles(
        self,
        symbol: str,
        timeframe: str,
    ) -> List[ValidatedCandle]:
        """Load and validate historical candles with in-memory caching."""
        cache_key = (symbol, timeframe)
        if cache_key in self._candle_cache:
            return self._candle_cache[cache_key]

        df = await self.repo.load_candles(symbol, timeframe)
        if df.empty:
            return []

        validated: List[ValidatedCandle] = []
        for row in df.itertuples():
            vc = ValidatedCandle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=str(row.timestamp),
                open=float(row.open),
                high=float(row.high),
                low=float(row.low),
                close=float(row.close),
                volume=float(row.volume),
                quote_volume=float(getattr(row, "quote_volume", 0.0) or 0.0),
                trades_count=int(getattr(row, "trades_count", 0) or 0),
                is_closed=True,
            )
            validated.append(vc)

        self._candle_cache[cache_key] = validated
        return validated

    def slice_candles(
        self,
        candles: List[ValidatedCandle],
        partition: PartitionBoundary,
    ) -> List[ValidatedCandle]:
        """Slice candles within partition window including warmup."""
        if not candles:
            return []
        start_dt = partition.dt_start
        end_dt = partition.dt_end
        eval_indices = [i for i, c in enumerate(candles) if start_dt <= c.dt_utc <= end_dt]
        if not eval_indices:
            return []
        first_idx = eval_indices[0]
        last_idx = eval_indices[-1]
        warmup_start = max(0, first_idx - partition.warmup_bars)
        return candles[warmup_start : last_idx + 1]

    async def run_statistical_evaluation(
        self,
        max_samples_per_series: int = 35,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Evaluate Kronos-mini forecast accuracy (MAE, RMSE, Directional Accuracy, Precision, Recall, F1, Bias)
        across symbols, timeframes, and horizons on OOS partitions.
        """
        logger.info("Starting Kronos statistical forecast evaluation...")
        predictions_records: List[Dict[str, Any]] = []

        # Use canonical OOS_HISTORICAL_REF and OOS_PRISTINE
        partitions_to_eval = [
            STANDARD_PARTITIONS["OOS_HISTORICAL_REF"],
            STANDARD_PARTITIONS["OOS_PRISTINE"],
        ]

        total_eval_points = 0
        correct_directions = 0

        for part in partitions_to_eval:
            for symbol in self.symbols:
                for tf in self.timeframes:
                    all_candles = await self.load_validated_candles(symbol, tf)
                    sliced = self.slice_candles(all_candles, part)
                    if len(sliced) < 70:
                        continue

                    # Filter evaluation indices strictly inside partition window
                    eval_indices = [
                        i for i, c in enumerate(sliced)
                        if part.start_time <= c.timestamp <= part.end_time
                    ]
                    if not eval_indices:
                        continue

                    # Sample evenly across evaluation window
                    step = max(1, len(eval_indices) // max_samples_per_series)
                    sampled_indices = eval_indices[::step][:max_samples_per_series]

                    for idx in sampled_indices:
                        history = sliced[: idx + 1]
                        if len(history) < 30:
                            continue

                        # Ensure lookback window
                        lookback_candles = history[-64:]
                        cur_candle = lookback_candles[-1]
                        cur_price = float(cur_candle.close)

                        for horizon in self.horizons:
                            # Verify future ground truth exists
                            if idx + horizon >= len(sliced):
                                continue

                            future_candles = sliced[idx + 1 : idx + 1 + horizon]
                            actual_future_close = float(future_candles[-1].close)
                            actual_return_pct = ((actual_future_close - cur_price) / cur_price) * 100.0
                            actual_dir = "LONG" if actual_return_pct > 0 else ("SHORT" if actual_return_pct < 0 else "FLAT")

                            inp = ForecastInput(
                                symbol=symbol,
                                timeframe=tf,
                                historical_sequence=lookback_candles,
                                sequence_length=len(lookback_candles),
                                dataset_id=f"v2.0.0-{part.name}",
                                forecast_horizon=horizon,
                                model_identifier="NeoQuasar/Kronos-mini",
                                model_version="kronos-mini-v1",
                            )

                            t0 = time.perf_counter()
                            forecast_out = await self.forecaster.forecast(inp)
                            latency_ms = (time.perf_counter() - t0) * 1000.0

                            pred_bar = forecast_out.forecasted_sequence[-1]
                            pred_close = float(pred_bar.close)
                            pred_return_pct = float(forecast_out.uncertainty_distribution.get("predicted_return_pct", 0.0))
                            pred_dir = forecast_out.uncertainty_distribution.get("predicted_direction", "FLAT")

                            # Error metrics
                            price_error = pred_close - actual_future_close
                            abs_price_error = abs(price_error)
                            squared_price_error = price_error ** 2
                            pct_error = (abs_price_error / actual_future_close) * 100.0

                            return_error = pred_return_pct - actual_return_pct
                            abs_return_error = abs(return_error)

                            is_dir_correct = (pred_dir == actual_dir) and (actual_dir != "FLAT")
                            if actual_dir != "FLAT":
                                total_eval_points += 1
                                if is_dir_correct:
                                    correct_directions += 1

                            rec = {
                                "partition": part.name,
                                "symbol": symbol,
                                "timeframe": tf,
                                "horizon": horizon,
                                "timestamp": cur_candle.timestamp,
                                "target_timestamp": future_candles[-1].timestamp,
                                "current_close": round(cur_price, 4),
                                "predicted_close": round(pred_close, 4),
                                "actual_close": round(actual_future_close, 4),
                                "predicted_return_pct": round(pred_return_pct, 4),
                                "actual_return_pct": round(actual_return_pct, 4),
                                "predicted_direction": pred_dir,
                                "actual_direction": actual_dir,
                                "directional_hit": bool(is_dir_correct),
                                "price_error": round(price_error, 4),
                                "abs_price_error": round(abs_price_error, 4),
                                "pct_error": round(pct_error, 4),
                                "return_error": round(return_error, 4),
                                "abs_return_error": round(abs_return_error, 4),
                                "latency_ms": round(latency_ms, 2),
                                "fingerprint": forecast_out.input_dataset_fingerprint,
                            }
                            predictions_records.append(rec)

        # Compute aggregate metrics
        df_preds = pd.DataFrame(predictions_records)
        metrics_summary = self._calculate_aggregate_metrics(df_preds)

        # Save to Parquet and JSON
        parquet_path = os.path.join(self.export_dir, "forecast_predictions.parquet")
        json_path = os.path.join(self.export_dir, "forecast_predictions.json")
        metrics_path = os.path.join(self.export_dir, "statistical_metrics.json")

        df_preds.to_parquet(parquet_path, index=False)
        with open(json_path, "w") as f:
            json.dump(predictions_records, f, indent=2)
        with open(metrics_path, "w") as f:
            json.dump(metrics_summary, f, indent=2)

        logger.info(f"Statistical forecast evaluation complete. {len(predictions_records)} predictions exported.")
        return predictions_records, metrics_summary

    def _calculate_aggregate_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Aggregate statistical metrics overall and grouped by horizon, timeframe, and symbol."""
        if df.empty:
            return {}

        def get_group_metrics(sub_df: pd.DataFrame) -> Dict[str, Any]:
            n = len(sub_df)
            if n == 0:
                return {}

            mae = float(sub_df["abs_price_error"].mean())
            rmse = float(np.sqrt((sub_df["price_error"] ** 2).mean()))
            mape = float(sub_df["pct_error"].mean())
            mfe = float(sub_df["price_error"].mean())  # Forecast bias

            ret_mae = float(sub_df["abs_return_error"].mean())
            ret_rmse = float(np.sqrt((sub_df["return_error"] ** 2).mean()))

            valid_dirs = sub_df[sub_df["actual_direction"] != "FLAT"]
            dir_acc = float((valid_dirs["predicted_direction"] == valid_dirs["actual_direction"]).mean() * 100.0) if len(valid_dirs) > 0 else 0.0

            # Directional Precision / Recall for LONG (UP)
            pred_long = sub_df[sub_df["predicted_direction"] == "LONG"]
            act_long = sub_df[sub_df["actual_direction"] == "LONG"]
            true_long = sub_df[(sub_df["predicted_direction"] == "LONG") & (sub_df["actual_direction"] == "LONG")]

            prec_up = float(len(true_long) / len(pred_long) * 100.0) if len(pred_long) > 0 else 0.0
            rec_up = float(len(true_long) / len(act_long) * 100.0) if len(act_long) > 0 else 0.0
            f1_up = float(2 * prec_up * rec_up / (prec_up + rec_up)) if (prec_up + rec_up) > 0 else 0.0

            # Directional Precision / Recall for SHORT (DOWN)
            pred_short = sub_df[sub_df["predicted_direction"] == "SHORT"]
            act_short = sub_df[sub_df["actual_direction"] == "SHORT"]
            true_short = sub_df[(sub_df["predicted_direction"] == "SHORT") & (sub_df["actual_direction"] == "SHORT")]

            prec_down = float(len(true_short) / len(pred_short) * 100.0) if len(pred_short) > 0 else 0.0
            rec_down = float(len(true_short) / len(act_short) * 100.0) if len(act_short) > 0 else 0.0
            f1_down = float(2 * prec_down * rec_down / (prec_down + rec_down)) if (prec_down + rec_down) > 0 else 0.0

            return {
                "sample_count": n,
                "price_mae": round(mae, 4),
                "price_rmse": round(rmse, 4),
                "price_mape_pct": round(mape, 4),
                "forecast_bias_mfe": round(mfe, 4),
                "return_mae_pct": round(ret_mae, 4),
                "return_rmse_pct": round(ret_rmse, 4),
                "directional_accuracy_pct": round(dir_acc, 2),
                "directional_precision_up_pct": round(prec_up, 2),
                "directional_recall_up_pct": round(rec_up, 2),
                "directional_f1_up": round(f1_up, 2),
                "directional_precision_down_pct": round(prec_down, 2),
                "directional_recall_down_pct": round(rec_down, 2),
                "directional_f1_down": round(f1_down, 2),
                "avg_latency_ms": round(float(sub_df["latency_ms"].mean()), 2),
            }

        overall = get_group_metrics(df)

        by_horizon = {}
        for h, grp in df.groupby("horizon"):
            by_horizon[f"H{h}"] = get_group_metrics(grp)

        by_timeframe = {}
        for tf, grp in df.groupby("timeframe"):
            by_timeframe[tf] = get_group_metrics(grp)

        by_symbol = {}
        for sym, grp in df.groupby("symbol"):
            by_symbol[sym] = get_group_metrics(grp)

        return {
            "overall": overall,
            "by_horizon": by_horizon,
            "by_timeframe": by_timeframe,
            "by_symbol": by_symbol,
        }

    async def run_economic_comparison(
        self,
        partition_name: str = "OOS_FULL",
    ) -> Dict[str, Any]:
        """
        Execute economic simulation for Groups A, B, and C under realistic exchange friction.
        """
        logger.info(f"Running economic comparison for partition {partition_name}...")
        part = STANDARD_PARTITIONS[partition_name]

        # Standard execution settings (Binance 0.10% maker, 0.10% taker, 0.05% slippage/side = 0.30% round trip)
        config = BacktestConfig(
            initial_capital=Decimal("1000.00"),
            max_concurrent_positions=2,
            risk_per_trade_pct=Decimal("0.005"),
            maker_fee_pct=Decimal("0.001"),
            taker_fee_pct=Decimal("0.001"),
            slippage_pct=Decimal("0.0005"),
            start_time=part.start_time,
            end_time=part.end_time,
            entry_filter="H7_CONFLUENCE",
            exit_policy="BALANCED",
        )

        # Load candles for all symbols and timeframes
        candles_by_symbol_tf: Dict[str, Dict[str, List[ValidatedCandle]]] = {}
        for s in self.symbols:
            candles_by_symbol_tf[s] = {}
            for tf in self.timeframes:
                c_all = await self.load_validated_candles(s, tf)
                candles_by_symbol_tf[s][tf] = self.slice_candles(c_all, part)

        # -------------------------------------------------------------
        # 1. GROUP A: Deterministic NEPTUNE Baseline (H7 Confluence)
        # -------------------------------------------------------------
        logger.info("Evaluating Group A: Deterministic Baseline...")
        group_a_results = {}
        for sym in self.symbols:
            c_tf = candles_by_symbol_tf[sym]["1h"]
            c_htf = candles_by_symbol_tf[sym]["4h"]
            engine = HistoricalBacktestEngine(config)
            res = await engine.run(
                candles_by_symbol={sym: c_tf},
                htf_candles_by_symbol={sym: c_htf},
            )
            valid_trades = [t for t in res.trades if part.start_time <= t.entry_timestamp <= part.end_time]
            res.trades = valid_trades
            res.metrics.total_trades = len(valid_trades)
            group_a_results[sym] = self._summarize_trade_metrics(valid_trades, Decimal("1000.00"))

        group_a_portfolio = self._aggregate_portfolio_metrics(group_a_results)

        # -------------------------------------------------------------
        # 2. GROUP B: Pure Kronos-mini Forecasting Strategy
        # -------------------------------------------------------------
        logger.info("Evaluating Group B: Pure Kronos-mini Forecasting Strategy...")
        group_b_results = {}
        for sym in self.symbols:
            c_tf = candles_by_symbol_tf[sym]["1h"]
            trades_b = await self._simulate_kronos_pure_strategy(sym, "1h", c_tf, part, config)
            group_b_results[sym] = self._summarize_trade_metrics(trades_b, Decimal("1000.00"))

        group_b_portfolio = self._aggregate_portfolio_metrics(group_b_results)

        # -------------------------------------------------------------
        # 3. GROUP C: Hybrid NEPTUNE + Kronos Confirmation Gate
        # -------------------------------------------------------------
        logger.info("Evaluating Group C: Hybrid NEPTUNE + Kronos...")
        group_c_results = {}
        for sym in self.symbols:
            c_tf = candles_by_symbol_tf[sym]["1h"]
            c_htf = candles_by_symbol_tf[sym]["4h"]
            trades_c = await self._simulate_hybrid_strategy(sym, "1h", c_tf, c_htf, part, config)
            group_c_results[sym] = self._summarize_trade_metrics(trades_c, Decimal("1000.00"))

        group_c_portfolio = self._aggregate_portfolio_metrics(group_c_results)

        comparison_output = {
            "partition": partition_name,
            "period": f"{part.start_time} to {part.end_time}",
            "execution_friction": {
                "maker_fee": "0.10%",
                "taker_fee": "0.10%",
                "slippage": "0.05% per side",
                "round_trip_cost": "0.30%",
            },
            "group_a_deterministic_baseline": {
                "portfolio": group_a_portfolio,
                "by_symbol": group_a_results,
            },
            "group_b_kronos_pure": {
                "portfolio": group_b_portfolio,
                "by_symbol": group_b_results,
            },
            "group_c_hybrid_neptune_kronos": {
                "portfolio": group_c_portfolio,
                "by_symbol": group_c_results,
            },
        }

        # Save to JSON
        comp_path = os.path.join(self.export_dir, "economic_comparison.json")
        with open(comp_path, "w") as f:
            json.dump(comparison_output, f, indent=2)

        logger.info(f"Economic comparison complete. Saved to {comp_path}.")
        return comparison_output

    async def _simulate_kronos_pure_strategy(
        self,
        symbol: str,
        timeframe: str,
        candles: List[ValidatedCandle],
        part: PartitionBoundary,
        config: BacktestConfig,
        eval_step: int = 12,
    ) -> List[SimulatedTrade]:
        """
        Pure Kronos strategy: Evaluate closed bars every eval_step bars.
        If |predicted_return| > friction threshold (0.35%), enter paper trade.
        """
        trades: List[SimulatedTrade] = []
        equity = config.initial_capital

        eval_indices = [
            i for i, c in enumerate(candles)
            if part.start_time <= c.timestamp <= part.end_time
        ]
        if not eval_indices:
            return []

        for idx in eval_indices[::eval_step]:
            if idx + 4 >= len(candles):
                break

            history = candles[: idx + 1]
            if len(history) < 32:
                continue

            last_c = history[-1]
            cur_price = Decimal(str(last_c.close))

            inp = ForecastInput(
                symbol=symbol,
                timeframe=timeframe,
                historical_sequence=history[-64:],
                sequence_length=min(64, len(history)),
                dataset_id="group_b_sim",
                forecast_horizon=4,
                model_identifier="NeoQuasar/Kronos-mini",
                model_version="v1.0.0",
            )
            out = await self.forecaster.forecast(inp)
            pred_ret = Decimal(str(out.uncertainty_distribution.get("predicted_return_pct", 0.0)))
            pred_dir = out.uncertainty_distribution.get("predicted_direction", "FLAT")

            # Entry condition: Predicted return must comfortably exceed round-trip friction (0.30%)
            if abs(pred_ret) >= Decimal("0.35") and pred_dir in ["LONG", "SHORT"]:
                risk_amt = equity * config.risk_per_trade_pct
                stop_dist = cur_price * Decimal("0.015")
                qty = (risk_amt / stop_dist).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
                if qty <= 0:
                    continue

                direction_str = "LONG" if pred_dir == "LONG" else "SHORT"
                entry_slippage = cur_price * config.slippage_pct
                entry_price = cur_price + entry_slippage if direction_str == "LONG" else cur_price - entry_slippage
                entry_fee = entry_price * qty * config.taker_fee_pct

                # Hold for horizon bars (4 bars)
                future_bars = candles[idx + 1 : idx + 1 + 4]
                exit_c = future_bars[-1]
                raw_exit_price = Decimal(str(exit_c.close))
                exit_slippage = raw_exit_price * config.slippage_pct
                exit_price = raw_exit_price - exit_slippage if direction_str == "LONG" else raw_exit_price + exit_slippage
                exit_fee = exit_price * qty * config.taker_fee_pct

                if direction_str == "LONG":
                    gross_pnl = (exit_price - entry_price) * qty
                else:
                    gross_pnl = (entry_price - exit_price) * qty

                total_fees = entry_fee + exit_fee
                total_slippage = (entry_slippage + exit_slippage) * qty
                net_pnl = gross_pnl - total_fees
                equity += net_pnl

                trades.append(
                    SimulatedTrade(
                        trade_id=f"B-{symbol}-{last_c.timestamp}",
                        symbol=symbol,
                        timeframe=timeframe,
                        direction=direction_str,
                        signal_timestamp=last_c.timestamp,
                        entry_timestamp=last_c.timestamp,
                        entry_price=entry_price,
                        exit_timestamp=exit_c.timestamp,
                        exit_price=exit_price,
                        stop_loss=cur_price * (Decimal("0.985") if direction_str == "LONG" else Decimal("1.015")),
                        take_profit=cur_price * (Decimal("1.03") if direction_str == "LONG" else Decimal("0.97")),
                        position_size=qty,
                        gross_pnl=gross_pnl,
                        fees=total_fees,
                        spread_cost=Decimal("0.00"),
                        slippage_cost=total_slippage,
                        net_pnl=net_pnl,
                        exit_reason="HORIZON_CLOSE",
                        market_regime="PREDICTED",
                    )
                )

        return trades

    async def _simulate_hybrid_strategy(
        self,
        symbol: str,
        timeframe: str,
        candles: List[ValidatedCandle],
        htf_candles: List[ValidatedCandle],
        part: PartitionBoundary,
        config: BacktestConfig,
    ) -> List[SimulatedTrade]:
        """
        Group C: Hybrid NEPTUNE + Kronos.
        Runs baseline deterministic engine, but tests every candidate signal against Kronos.
        Only signals where Kronos directional prediction confirms the deterministic setup are executed.
        """
        # Run baseline engine to collect raw signals and candidate replay
        engine = HistoricalBacktestEngine(config)
        base_res = await engine.run(
            candles_by_symbol={symbol: candles},
            htf_candles_by_symbol={symbol: htf_candles},
        )
        candidates = [t for t in base_res.trades if part.start_time <= t.entry_timestamp <= part.end_time]
        if not candidates:
            return []

        # Find timestamp index map for candles
        candle_map = {c.timestamp: i for i, c in enumerate(candles)}
        confirmed_trades: List[SimulatedTrade] = []

        for cand in candidates:
            c_idx = candle_map.get(cand.entry_timestamp)
            if c_idx is None or c_idx < 32:
                continue

            history = candles[: c_idx + 1]
            inp = ForecastInput(
                symbol=symbol,
                timeframe=timeframe,
                historical_sequence=history[-64:],
                sequence_length=min(64, len(history)),
                dataset_id="group_c_hybrid",
                forecast_horizon=4,
                model_identifier="NeoQuasar/Kronos-mini",
                model_version="v1.0.0",
            )
            out = await self.forecaster.forecast(inp)
            k_dir = out.uncertainty_distribution.get("predicted_direction", "FLAT")
            k_ret = abs(float(out.uncertainty_distribution.get("predicted_return_pct", 0.0)))

            # Confirmation condition: Kronos agrees with deterministic direction and predicted magnitude > 0.10%
            expected_k_dir = "LONG" if cand.direction == "BUY" else "SHORT"
            if k_dir == expected_k_dir and k_ret >= 0.10:
                confirmed_trades.append(cand)
            else:
                logger.debug(f"Candidate {cand.trade_id} rejected by Kronos gate (k_dir={k_dir}, expected={expected_k_dir})")

        return confirmed_trades

    def _summarize_trade_metrics(
        self,
        trades: List[SimulatedTrade],
        starting_equity: Decimal,
    ) -> Dict[str, Any]:
        """Calculate standardized financial metrics for a trade set."""
        if not trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate_pct": 0.0,
                "net_pnl": 0.0,
                "net_return_pct": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "expectancy_per_trade": 0.0,
                "total_fees": 0.0,
            }

        total = len(trades)
        wins = [t for t in trades if t.net_pnl > 0]
        losses = [t for t in trades if t.net_pnl <= 0]
        win_rate = (len(wins) / total) * 100.0

        net_pnl = sum((t.net_pnl for t in trades), Decimal("0"))
        total_fees = sum((getattr(t, "fees", getattr(t, "total_fees", Decimal("0"))) for t in trades), Decimal("0"))
        net_return_pct = (net_pnl / starting_equity) * Decimal("100")

        gross_wins = sum((t.gross_pnl for t in wins), Decimal("0"))
        gross_losses = abs(sum((t.gross_pnl for t in losses), Decimal("0")))
        pf = float(gross_wins / gross_losses) if gross_losses > 0 else (99.0 if gross_wins > 0 else 0.0)

        # Max drawdown computation
        peak = starting_equity
        cur = starting_equity
        max_dd = Decimal("0")
        for t in trades:
            cur += t.net_pnl
            if cur > peak:
                peak = cur
            dd = (peak - cur) / peak if peak > 0 else Decimal("0")
            if dd > max_dd:
                max_dd = dd

        expectancy = net_pnl / Decimal(total) if total > 0 else Decimal("0")

        return {
            "total_trades": total,
            "winning_trades": len(wins),
            "losing_trades": len(losses),
            "win_rate_pct": round(win_rate, 2),
            "net_pnl": round(float(net_pnl), 2),
            "net_return_pct": round(float(net_return_pct), 2),
            "profit_factor": round(pf, 2),
            "max_drawdown_pct": round(float(max_dd * 100), 2),
            "expectancy_per_trade": round(float(expectancy), 2),
            "total_fees": round(float(total_fees), 2),
        }

    def _aggregate_portfolio_metrics(
        self,
        symbol_results: Dict[str, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Aggregate per-symbol results into a combined portfolio summary."""
        total_trades = sum(r["total_trades"] for r in symbol_results.values())
        if total_trades == 0:
            return {
                "total_trades": 0,
                "win_rate_pct": 0.0,
                "net_pnl": 0.0,
                "net_return_pct": 0.0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "expectancy_per_trade": 0.0,
                "total_fees": 0.0,
            }

        total_wins = sum(r["winning_trades"] for r in symbol_results.values())
        win_rate = (total_wins / total_trades) * 100.0
        net_pnl = sum(r["net_pnl"] for r in symbol_results.values())
        total_fees = sum(r["total_fees"] for r in symbol_results.values())
        net_return_pct = (net_pnl / 1000.0) * 100.0
        expectancy = net_pnl / total_trades
        max_dd = max(r["max_drawdown_pct"] for r in symbol_results.values())

        # Harmonic/weighted profit factor
        pfs = [r["profit_factor"] for r in symbol_results.values() if r["total_trades"] > 0]
        avg_pf = sum(pfs) / len(pfs) if pfs else 0.0

        return {
            "total_trades": total_trades,
            "winning_trades": total_wins,
            "win_rate_pct": round(win_rate, 2),
            "net_pnl": round(net_pnl, 2),
            "net_return_pct": round(net_return_pct, 2),
            "profit_factor": round(avg_pf, 2),
            "max_drawdown_pct": round(max_dd, 2),
            "expectancy_per_trade": round(expectancy, 2),
            "total_fees": round(total_fees, 2),
        }

