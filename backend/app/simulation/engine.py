"""
NEPTUNE Historical Backtesting Engine (`engine.py`)

Event-driven, deterministic replay engine evaluating NEPTUNE specialist agents
and strategies against historical candle data without look-ahead bias (Rule S-05).

Event Replay Lifecycle (per candle step):
1. Advance historical clock to timestamp T.
2. Provide strictly past and current closed candles available at T.
3. Update open positions against bracket stops/targets (conservative intrabar resolution).
4. Run specialist analysis agents (Market Scanner, Trend, Momentum, Volume).
5. Generate candidate setups via Strategy Analyst.
6. Pass candidates through Risk Manager invariant checks (Rule S-04).
7. Simulate hypothetical paper fills with realistic slippage, spread, and fees (Rule A-10).
8. Record portfolio mark-to-market equity snapshot.
9. Persist execution results to SQLite summary and Parquet trade ledger.
"""
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.agents.market_scanner import MarketScannerAgent, MarketScannerInput
from app.agents.momentum_analyst import MomentumAnalystAgent, MomentumAnalystInput
from app.agents.strategy_analyst import StrategyAnalystAgent, StrategyAnalystInput
from app.agents.trend_analyst import TrendAnalystAgent, TrendAnalystInput
from app.agents.volume_analyst import VolumeAnalystAgent, VolumeAnalystInput
from app.analytics.indicators import calculate_atr
from app.config.settings import get_settings
from app.data.market.validator import CandleValidator, ValidatedCandle
from app.data.repositories.parquet_repo import ParquetMarketDataRepository
from app.risk.risk_manager import RiskManager
from app.simulation.execution import PaperExecutionSimulator
from app.simulation.metrics import calculate_backtest_metrics
from app.simulation.models import (
    ActivePosition,
    BacktestConfig,
    BacktestResult,
    EquityPoint,
    SimulatedTrade,
)
from app.simulation.reversal import MultiFactorReversalDetector


class HistoricalBacktestEngine:
    """
    Event-driven deterministic historical backtest runner.
    """

    def __init__(
        self,
        config: BacktestConfig,
        market_repo: Optional[ParquetMarketDataRepository] = None,
    ):
        self.config = config
        self.market_repo = market_repo or ParquetMarketDataRepository()
        self.settings = get_settings()

        # Specialist analysis agents
        self.market_scanner = MarketScannerAgent()
        self.trend_analyst = TrendAnalystAgent()
        self.momentum_analyst = MomentumAnalystAgent()
        self.volume_analyst = VolumeAnalystAgent()
        self.strategy_analyst = StrategyAnalystAgent()

        # Risk Manager and Execution Simulator
        self.risk_manager = RiskManager(
            max_concurrent_positions=config.max_concurrent_positions,
            risk_per_trade_pct=config.risk_per_trade_pct,
            daily_loss_limit_pct=config.daily_loss_limit_pct,
            max_drawdown_pct=config.max_drawdown_pct,
            min_reward_risk_ratio=config.min_reward_risk_ratio,
        )
        self.execution_simulator = PaperExecutionSimulator(
            taker_fee_pct=config.taker_fee_pct,
            maker_fee_pct=config.maker_fee_pct,
            slippage_pct=config.slippage_pct,
            spread_bps=config.spread_bps,
            conservative_ambiguity=config.conservative_ambiguous_bars,
        )

    async def run(
        self,
        candles_by_symbol: Optional[Dict[str, List[ValidatedCandle]]] = None,
    ) -> BacktestResult:
        """
        Execute event-driven backtest.
        If candles_by_symbol is omitted, data is loaded from ParquetMarketDataRepository.
        """
        backtest_id = f"bkt_{uuid.uuid4().hex[:12]}"

        # 1. Load or validate historical dataset
        candles_map = candles_by_symbol or await self._load_data_from_repo()

        # Validate each symbol's series using CandleValidator and duplicate detection
        for sym, candles in candles_map.items():
            if not candles:
                continue
            seen_ts = set()
            for c in candles:
                if c.timestamp in seen_ts:
                    raise ValueError(f"Duplicate timestamp detected for symbol {sym}: {c.timestamp}")
                seen_ts.add(c.timestamp)

            _, issues = CandleValidator.validate_sequence(candles, self.config.timeframe, allow_duplicates=False)
            error_issues = [i for i in issues if i.severity == "ERROR"]
            if error_issues:
                raise ValueError(f"Candle sequence validation failed for {sym}: {error_issues[0].message}")

        # Collect all unique timestamps in chronological order
        all_timestamps = sorted(
            list({c.timestamp for candles in candles_map.values() for c in candles})
        )

        if not all_timestamps:
            metrics = calculate_backtest_metrics([], [], self.config.initial_capital, self.config.timeframe)
            return BacktestResult(
                backtest_id=backtest_id,
                config=self.config,
                metrics=metrics,
                trades=[],
                equity_curve=[],
            )

        # Build fast lookup map by symbol and timestamp
        candle_lookup: Dict[str, Dict[str, ValidatedCandle]] = {
            sym: {c.timestamp: c for c in c_list}
            for sym, c_list in candles_map.items()
        }
        candle_index: Dict[str, Dict[str, int]] = {
            sym: {c.timestamp: idx for idx, c in enumerate(c_list)}
            for sym, c_list in candles_map.items()
        }

        # 2. Portfolio and Accounting State
        cash_equity = self.config.initial_capital
        peak_equity = self.config.initial_capital
        daily_starting_equity = self.config.initial_capital
        daily_realized_pnl = Decimal("0")
        current_day: Optional[str] = None

        open_positions: List[ActivePosition] = []
        completed_trades: List[SimulatedTrade] = []
        equity_curve: List[EquityPoint] = []

        # 3. Main Event Loop — Step forward through time chronologically
        for step_idx, ts in enumerate(all_timestamps):
            ts_date = ts[:10]  # YYYY-MM-DD
            if current_day != ts_date:
                # 00:00:00 UTC day boundary reset
                current_day = ts_date
                # Total equity at day start
                pos_value_day_start = sum(
                    p.position_size * p.current_price for p in open_positions
                )
                daily_starting_equity = cash_equity + pos_value_day_start
                daily_realized_pnl = Decimal("0")

            # --- PHASE A: Update open positions against brackets & pending reversals ---
            positions_to_keep: List[ActivePosition] = []
            for pos in open_positions:
                curr_candle = candle_lookup.get(pos.symbol, {}).get(ts)
                if curr_candle is None:
                    positions_to_keep.append(pos)
                    continue

                c_open = Decimal(str(curr_candle.open))
                trade = None

                # 1. If reversal exit was confirmed on previous candle close (T-1),
                # check priority at candle T open:
                if pos.reversal_exit_pending:
                    # Protective stop loss takes precedence if breached at/before open
                    stop_breached_at_open = False
                    if pos.direction == "LONG" and c_open <= pos.stop_loss:
                        stop_breached_at_open = True
                    elif pos.direction == "SHORT" and c_open >= pos.stop_loss:
                        stop_breached_at_open = True

                    if stop_breached_at_open:
                        pos.reversal_superseded = True
                        exit_reason = "TRAILING_STOP" if (
                            pos.stop_loss > pos.initial_stop_loss if pos.direction == "LONG"
                            else pos.stop_loss < pos.initial_stop_loss
                        ) else "STOP_LOSS"
                        exit_price_raw = min(pos.stop_loss, c_open) if pos.direction == "LONG" else max(pos.stop_loss, c_open)
                        trade = self.execution_simulator._finalize_trade(pos, exit_price_raw, curr_candle.timestamp, exit_reason)
                    else:
                        pos.reversal_superseded = False
                        trade = self.execution_simulator.execute_pending_reversal(pos, curr_candle)

                # 2. If no pending reversal executed, evaluate standard/trailing bracket
                if trade is None:
                    trade = self.execution_simulator.evaluate_candle_bracket(pos, curr_candle)

                if trade is not None:
                    # Trade closed: credit actual cash proceeds (executed exit notional - exit fee)
                    exit_notional = pos.position_size * trade.exit_price
                    exit_fee = exit_notional * self.config.taker_fee_pct
                    cash_inflow = exit_notional - exit_fee
                    cash_equity += cash_inflow
                    daily_realized_pnl += trade.net_pnl
                    completed_trades.append(trade)
                else:
                    positions_to_keep.append(pos)

            open_positions = positions_to_keep

            # --- PHASE B: Update trailing stops & evaluate reversals on surviving positions ---
            for pos in open_positions:
                curr_candle = candle_lookup.get(pos.symbol, {}).get(ts)
                if curr_candle is None:
                    continue

                sym_candles = candles_map.get(pos.symbol, [])
                c_idx = candle_index.get(pos.symbol, {}).get(ts)
                if c_idx is None:
                    continue
                # Lookback window capped at 300 candles for constant-time indicator evaluation
                start_idx = max(0, c_idx + 1 - 300)
                sub_candles = sym_candles[start_idx : c_idx + 1]

                # Compute current ATR for trailing stop calculation
                curr_atr = None
                if len(sub_candles) >= 15:
                    atr_vals = calculate_atr(
                        [c.high for c in sub_candles],
                        [c.low for c in sub_candles],
                        [c.close for c in sub_candles],
                        period=14,
                    )
                    if atr_vals and atr_vals[-1] is not None:
                        curr_atr = Decimal(str(atr_vals[-1]))

                # Ratchet trailing stop if activated (in-place one-way ratchet)
                self.execution_simulator.update_trailing_stop(
                    position=pos,
                    candle=curr_candle,
                    atr_value=curr_atr,
                    atr_multiplier=self.config.trailing_atr_multiplier,
                    activation_threshold_r=self.config.trailing_activation_threshold_r,
                )

                # Multi-Factor Reversal Detection at candle close (requires >= 30 candles)
                if pos.exit_policy == "BALANCED" and not pos.reversal_exit_pending and len(sub_candles) >= 30:
                    reg_out = await self.market_scanner.run(
                        MarketScannerInput(
                            timestamp=ts,
                            symbols=[pos.symbol],
                            timeframe=self.config.timeframe,
                            candles_by_symbol={pos.symbol: sub_candles},
                        )
                    )
                    sym_regime = reg_out.output.regimes.get(pos.symbol)
                    if sym_regime:
                        trend_out = await self.trend_analyst.run(
                            TrendAnalystInput(
                                timestamp=ts,
                                symbol=pos.symbol,
                                timeframe=self.config.timeframe,
                                candles=sub_candles,
                            )
                        )
                        mom_out = await self.momentum_analyst.run(
                            MomentumAnalystInput(
                                timestamp=ts,
                                symbol=pos.symbol,
                                timeframe=self.config.timeframe,
                                candles=sub_candles,
                            )
                        )
                        vol_out = await self.volume_analyst.run(
                            VolumeAnalystInput(
                                timestamp=ts,
                                symbol=pos.symbol,
                                timeframe=self.config.timeframe,
                                candles=sub_candles,
                            )
                        )

                        rev_dec = MultiFactorReversalDetector.evaluate(
                            position=pos,
                            trend_data=trend_out.output,
                            momentum_data=mom_out.output,
                            volume_data=vol_out.output,
                            regime_data=sym_regime,
                            evaluation_timestamp=ts,
                        )
                        if rev_dec.reversal_detected:
                            pos.reversal_exit_pending = True
                            pos.reversal_detection_timestamp = ts
                            pos.reversal_reason_codes = rev_dec.reason_codes

            # --- PHASE C: Evaluate Strategy Candidates for Available Symbols ---
            newly_opened_positions: List[ActivePosition] = []
            for sym in self.config.symbols:
                sym_candles = candles_map.get(sym, [])
                curr_candle = candle_lookup.get(sym, {}).get(ts)
                if curr_candle is None:
                    continue

                # Rule S-05 Look-ahead protection:
                # Slice ONLY up to current candle index with capped lookback window (300 bars)
                c_idx = candle_index.get(sym, {}).get(ts)
                if c_idx is None:
                    continue
                start_idx = max(0, c_idx + 1 - 300)
                sub_candles = sym_candles[start_idx : c_idx + 1]
                if len(sub_candles) < 30:
                    continue  # Warm-up requirement

                # Check if position already open for this symbol
                sym_already_open = any(p.symbol == sym for p in open_positions) or any(p.symbol == sym for p in newly_opened_positions)
                if sym_already_open or (len(open_positions) + len(newly_opened_positions)) >= self.config.max_concurrent_positions:
                    continue

                # Run specialist analytical agents
                reg_out = await self.market_scanner.run(
                    MarketScannerInput(
                        timestamp=ts,
                        symbols=[sym],
                        timeframe=self.config.timeframe,
                        candles_by_symbol={sym: sub_candles},
                    )
                )
                sym_regime = reg_out.output.regimes.get(sym)
                if not sym_regime or sym_regime.regime == "UNCERTAIN":
                    continue

                trend_out = await self.trend_analyst.run(
                    TrendAnalystInput(
                        timestamp=ts,
                        symbol=sym,
                        timeframe=self.config.timeframe,
                        candles=sub_candles,
                    )
                )
                mom_out = await self.momentum_analyst.run(
                    MomentumAnalystInput(
                        timestamp=ts,
                        symbol=sym,
                        timeframe=self.config.timeframe,
                        candles=sub_candles,
                    )
                )
                vol_out = await self.volume_analyst.run(
                    VolumeAnalystInput(
                        timestamp=ts,
                        symbol=sym,
                        timeframe=self.config.timeframe,
                        candles=sub_candles,
                    )
                )

                strat_out = await self.strategy_analyst.run(
                    StrategyAnalystInput(
                        timestamp=ts,
                        symbol=sym,
                        timeframe=self.config.timeframe,
                        candles=sub_candles,
                        regime_data=sym_regime,
                        trend_data=trend_out.output,
                        momentum_data=mom_out.output,
                        volume_data=vol_out.output,
                        min_reward_risk_ratio=float(self.config.min_reward_risk_ratio),
                    )
                )

                if strat_out.output.evaluation_outcome in ("LONG", "SHORT") and strat_out.output.candidates:
                    cand = strat_out.output.candidates[0]

                    # Total portfolio equity for risk sizing
                    curr_pos_val = sum(p.position_size * p.current_price for p in open_positions) + sum(p.position_size * p.current_price for p in newly_opened_positions)
                    total_equity_now = cash_equity + curr_pos_val

                    # Pass through Risk Manager (Rule S-04)
                    risk_eval = self.risk_manager.evaluate_signal(
                        signal=cand,
                        current_equity=total_equity_now,
                        peak_equity=peak_equity,
                        daily_starting_equity=daily_starting_equity,
                        daily_realized_pnl=daily_realized_pnl,
                        open_positions=open_positions + newly_opened_positions,
                        timestamp=ts,
                    )

                    if risk_eval.approved and risk_eval.position_size:
                        # Simulate paper entry
                        new_pos = self.execution_simulator.simulate_entry(
                            symbol=sym,
                            timeframe=self.config.timeframe,
                            direction=cand.direction,
                            raw_price=Decimal(str(curr_candle.close)),
                            position_size=risk_eval.position_size,
                            stop_loss=Decimal(str(cand.suggested_stop_loss)),
                            take_profit=Decimal(str(cand.suggested_take_profit)),
                            signal_timestamp=cand.timestamp,
                            entry_timestamp=ts,
                            market_regime=sym_regime.regime,
                            strategy_metadata={
                                "signal_id": cand.signal_id,
                                "strategy_id": cand.strategy_id,
                                "raw_confidence": cand.raw_confidence,
                                "rr_ratio": cand.risk_reward_ratio,
                                "rationale": cand.rationale,
                            },
                            exit_policy=self.config.exit_policy,
                            theoretical_take_profit=Decimal(str(cand.suggested_take_profit)),
                        )

                        # Deduct actual cash outflow at entry (executed notional + entry fee)
                        cash_outflow = (new_pos.position_size * new_pos.entry_price) + new_pos.entry_fee
                        cash_equity -= cash_outflow
                        newly_opened_positions.append(new_pos)

            open_positions.extend(newly_opened_positions)

            # --- PHASE D: Mark-to-Market Equity Snapshot ---
            open_val = sum(p.position_size * p.current_price for p in open_positions)
            total_eq = cash_equity + open_val
            if total_eq > peak_equity:
                peak_equity = total_eq

            dd_pct = (
                float((peak_equity - total_eq) / peak_equity * Decimal("100.0"))
                if peak_equity > Decimal("0")
                else 0.0
            )

            equity_curve.append(
                EquityPoint(
                    timestamp=ts,
                    cash_equity=round(float(cash_equity), 2),
                    total_equity=round(float(total_eq), 2),
                    drawdown_pct=round(dd_pct, 2),
                    open_positions_count=len(open_positions),
                )
            )

        # 4. Post-Replay: Force-close remaining open positions at final candle
        for pos in open_positions:
            last_candle = candle_lookup.get(pos.symbol, {}).get(all_timestamps[-1])
            if last_candle:
                trade = self.execution_simulator.force_close(
                    pos, last_candle, reason="FORCE_CLOSE_END_OF_TEST"
                )
                exit_notional = pos.position_size * trade.exit_price
                exit_fee = exit_notional * self.config.taker_fee_pct
                cash_equity += (exit_notional - exit_fee)
                completed_trades.append(trade)

        open_positions.clear()

        # 5. Compute Final Quantitative Performance Metrics
        metrics = calculate_backtest_metrics(
            trades=completed_trades,
            equity_curve=equity_curve,
            initial_capital=self.config.initial_capital,
            timeframe=self.config.timeframe,
        )

        result = BacktestResult(
            backtest_id=backtest_id,
            config=self.config,
            metrics=metrics,
            trades=completed_trades,
            equity_curve=equity_curve,
        )

        # 6. Persistence to SQLite and Parquet if requested
        if self.config.save_to_parquet:
            self._save_trades_to_parquet(result)

        if self.config.save_to_db:
            self._save_summary_to_db(result)

        return result

    async def _load_data_from_repo(self) -> Dict[str, List[ValidatedCandle]]:
        """Load closed candles from Parquet storage using ParquetMarketDataRepository."""
        res: Dict[str, List[ValidatedCandle]] = {}
        start_dt = datetime.fromisoformat(self.config.start_time.replace("Z", "+00:00")) if self.config.start_time else None
        end_dt = datetime.fromisoformat(self.config.end_time.replace("Z", "+00:00")) if self.config.end_time else None

        for sym in self.config.symbols:
            df = await self.market_repo.load_candles(
                symbol=sym,
                timeframe=self.config.timeframe,
                start=start_dt,
                end=end_dt,
            )
            candles: List[ValidatedCandle] = []
            if not df.empty:
                for _, row in df.iterrows():
                    candles.append(
                        ValidatedCandle(
                            symbol=sym,
                            timeframe=self.config.timeframe,
                            timestamp=str(row["timestamp"]),
                            open=float(row["open"]),
                            high=float(row["high"]),
                            low=float(row["low"]),
                            close=float(row["close"]),
                            volume=float(row["volume"]),
                            is_closed=bool(row.get("is_closed", True)),
                        )
                    )
            res[sym] = candles
        return res

    def _save_trades_to_parquet(self, result: BacktestResult) -> str:
        """Persist trade ledger to Parquet file."""
        out_dir = self.config.output_dir or os.path.join(self.settings.historical_data_dir, "..", "backtests")
        os.makedirs(out_dir, exist_ok=True)
        file_path = os.path.join(out_dir, f"{result.backtest_id}_trades.parquet")

        if result.trades:
            trade_dicts = [t.to_dict() for t in result.trades]
            # Convert dict column to json string for parquet compatibility
            for d in trade_dicts:
                d["strategy_metadata"] = json.dumps(d["strategy_metadata"])
            df = pd.DataFrame(trade_dicts)
        else:
            df = pd.DataFrame(columns=[
                "trade_id", "symbol", "timeframe", "direction", "signal_timestamp",
                "entry_timestamp", "entry_price", "exit_timestamp", "exit_price",
                "stop_loss", "take_profit", "position_size", "gross_pnl", "fees",
                "spread_cost", "slippage_cost", "net_pnl", "exit_reason",
                "market_regime", "strategy_metadata"
            ])

        table = pa.Table.from_pandas(df)
        pq.write_table(table, file_path, compression="snappy")
        return file_path

    def _save_summary_to_db(self, result: BacktestResult) -> None:
        """Persist backtest summary record into SQLite."""
        db_path = os.path.join("storage", "db", "neptune.db")
        if not os.path.exists(db_path):
            return

        conn = sqlite3.connect(db_path)
        try:
            conn.execute("""
                INSERT OR REPLACE INTO backtest_runs (
                    backtest_id, strategy_id, symbols_json, timeframe, period_start, period_end,
                    initial_capital, final_capital, net_profit, total_trades, winning_trades,
                    losing_trades, win_rate, profit_factor, sharpe_ratio, max_drawdown_pct,
                    expectancy_per_trade, config_json, metrics_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                result.backtest_id,
                result.config.strategy_id,
                json.dumps(result.config.symbols),
                result.config.timeframe,
                result.equity_curve[0].timestamp if result.equity_curve else "",
                result.equity_curve[-1].timestamp if result.equity_curve else "",
                float(result.config.initial_capital),
                result.equity_curve[-1].total_equity if result.equity_curve else float(result.config.initial_capital),
                float(result.metrics.net_profit),
                result.metrics.total_trades,
                result.metrics.winning_trades,
                result.metrics.losing_trades,
                result.metrics.win_rate,
                result.metrics.profit_factor,
                result.metrics.sharpe_ratio,
                result.metrics.max_drawdown_pct,
                float(result.metrics.expectancy_per_trade),
                result.config.model_dump_json(),
                result.metrics.model_dump_json(),
                datetime.now(timezone.utc).isoformat(),
            ))
            conn.commit()
        except Exception:
            conn.rollback()
        finally:
            conn.close()
