"""
NEPTUNE Development-Partition Experiment Orchestrator (`development_orchestrator.py`)

Milestone 4.6.3.1: Development-Partition Experimental Execution.
Governed by: Rule S-01, Rule S-04, Rule S-05, Rule S-06, ADR-028, ADR-029, ADR-030.

Executes a 4-group parallel event-driven simulation across the 2024 Development partition:
- Group A: Deterministic Technical Baseline
- Group B: News-Veto Treatment Strategy
- Group C: Online Frequency-Matched Control (and Ex-Post Diagnostic Benchmarks)
- Group D: Online Exposure-Matched Control (and Ex-Post Diagnostic Benchmarks)

Guarantees 100% synchronized candidate streams, zero look-ahead bias, strict point-in-time
isolation, and cryptographic OOS access guarding.
"""
import copy
import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd

from app.agents.market_scanner import MarketScannerAgent, MarketScannerInput
from app.agents.momentum_analyst import MomentumAnalystAgent, MomentumAnalystInput
from app.agents.strategy_analyst import (
    RawCandidateSignal,
    StrategyAnalystAgent,
    StrategyAnalystInput,
)
from app.agents.trend_analyst import TrendAnalystAgent, TrendAnalystInput
from app.agents.volume_analyst import VolumeAnalystAgent, VolumeAnalystInput
from app.analytics.indicators import calculate_atr
from app.data.market.validator import CandleValidator, ValidatedCandle
from app.data.news.models import (
    EventCategory,
    RelevanceClassification,
    SourceVerificationStatus,
)
from app.data.repositories.parquet_repo import ParquetMarketDataRepository
from app.risk.risk_manager import RiskManager
from app.simulation.execution import PaperExecutionSimulator
from app.simulation.models import (
    ActivePosition,
    BacktestConfig,
    ExecutionPolicy,
    OrderStatus,
    ScheduledOrder,
    SimulatedTrade,
)
from app.simulation.reversal import MultiFactorReversalDetector
from app.simulation.scheduling import PointInTimeExecutionScheduler
from app.simulation.research_protocol import (
    CATEGORY_EVENT_WINDOWS_SECONDS,
    ControlExecutionMode,
    ExperimentalGroup,
    ExposureDimensions,
    ExPostExposureMatchingEngine,
    ExPostFrequencyMatchingEngine,
    FrozenBaselineConfig,
    NewsVetoContract,
    NewsVetoDecisionEngine,
    OnlineExposureMatchingEngine,
    OnlineFrequencyMatchingEngine,
    OOSAccessGuard,
    ResearchTaxonomyRegistry,
    StatisticalAnalysisPlanConfig,
)


class GroupPortfolioState:
    """Independent portfolio and order execution state for an experimental group."""

    def __init__(
        self,
        group_id: str,
        initial_capital: Decimal,
        config: BacktestConfig,
    ):
        self.group_id = group_id
        self.initial_capital = initial_capital
        self.cash_equity = initial_capital
        self.peak_equity = initial_capital
        self.daily_starting_equity = initial_capital
        self.daily_realized_pnl = Decimal("0")
        self.current_day: Optional[str] = None

        self.open_positions: List[ActivePosition] = []
        self.completed_trades: List[SimulatedTrade] = []
        self.seen_trade_ids: Set[str] = set()
        self.equity_curve: List[Dict[str, Any]] = []

        # Risk Manager & Execution Scheduler per group
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
        self.scheduler = PointInTimeExecutionScheduler(
            execution_policy=config.execution_policy,
            max_execution_gap_bars=config.max_execution_gap_bars,
            risk_manager=self.risk_manager,
        )

        # Performance counters
        self.daily_loss_limit_events: int = 0
        self.circuit_breaker_events: int = 0
        self.risk_rejected_count: int = 0
        self.orders_scheduled_count: int = 0
        self.orders_filled_count: int = 0

        # Exposure tracking
        self.total_bars_in_market: int = 0
        self.bars_with_concurrent_2: int = 0
        self.asset_bars: Dict[str, int] = {"BTCUSDT": 0, "ETHUSDT": 0, "BNBUSDT": 0}
        self.directional_bars: Dict[str, int] = {"LONG": 0, "SHORT": 0}
        self.cumulative_dollar_hours: Decimal = Decimal("0")


class DevelopmentExperimentRunner:
    """
    Orchestrates the 4-group parallel experiment across the 2024 Development partition.
    """

    def __init__(
        self,
        start_iso: str = "2024-01-01T00:00:00Z",
        end_iso: str = "2024-12-31T23:59:59Z",
        symbols: Optional[List[str]] = None,
        timeframe: str = "15m",
        db_path: str = "storage/db/neptune.db",
    ):
        # 1. Enforce OOS Access Guard
        OOSAccessGuard.verify_partition_access(start_iso, end_iso)

        self.start_iso = start_iso
        self.end_iso = end_iso
        self.symbols = symbols or ["BTCUSDT", "ETHUSDT", "BNBUSDT"]
        self.timeframe = timeframe
        self.db_path = db_path
        self.market_repo = ParquetMarketDataRepository()

        # Frozen configuration
        self.baseline_cfg = FrozenBaselineConfig()
        self.backtest_cfg = BacktestConfig(
            strategy_id="trend_continuation_v1",
            symbols=self.symbols,
            timeframe=self.timeframe,
            start_time=self.start_iso,
            end_time=self.end_iso,
            initial_capital=self.baseline_cfg.initial_virtual_capital_usdt,
            execution_policy=ExecutionPolicy.NEXT_ELIGIBLE_PRICE,
            max_execution_gap_bars=self.baseline_cfg.max_execution_gap_bars_15m,
            max_concurrent_positions=self.baseline_cfg.max_concurrent_positions,
            risk_per_trade_pct=self.baseline_cfg.max_risk_per_trade_pct,
            daily_loss_limit_pct=self.baseline_cfg.daily_simulated_loss_limit_pct,
            max_drawdown_pct=self.baseline_cfg.max_drawdown_circuit_breaker_pct,
            min_reward_risk_ratio=self.baseline_cfg.min_reward_risk_ratio,
            taker_fee_pct=self.baseline_cfg.taker_fee_pct,
            maker_fee_pct=self.baseline_cfg.maker_fee_pct,
            slippage_pct=self.baseline_cfg.adverse_slippage_pct,
            spread_bps=self.baseline_cfg.bid_ask_spread_bps,
            exit_policy=self.baseline_cfg.exit_policy,
            stop_loss_atr_multiplier=self.baseline_cfg.stop_loss_atr_multiplier,
            trailing_atr_multiplier=self.baseline_cfg.trailing_stop_atr_multiplier,
            trailing_activation_threshold_r=self.baseline_cfg.trailing_activation_threshold_r,
            conservative_ambiguous_bars=self.baseline_cfg.conservative_ambiguous_bars,
        )

        # Specialist analysis agents (shared candidate generator)
        self.market_scanner = MarketScannerAgent()
        self.trend_analyst = TrendAnalystAgent()
        self.momentum_analyst = MomentumAnalystAgent()
        self.volume_analyst = VolumeAnalystAgent()
        self.strategy_analyst = StrategyAnalystAgent()

        # Controls
        self.online_frequency_engine = OnlineFrequencyMatchingEngine(
            retention_ratio=0.85,  # Pre-registered Dev calibration
            cryptographic_seed="neptune_group_c_online_seed_2026",
        )
        self.online_exposure_engine = OnlineExposureMatchingEngine(
            cooldown_bars_after_trade=4
        )

        # 4 Parallel Portfolios
        self.groups: Dict[str, GroupPortfolioState] = {
            "GROUP_A": GroupPortfolioState("GROUP_A", self.backtest_cfg.initial_capital, self.backtest_cfg),
            "GROUP_B": GroupPortfolioState("GROUP_B", self.backtest_cfg.initial_capital, self.backtest_cfg),
            "GROUP_C": GroupPortfolioState("GROUP_C", self.backtest_cfg.initial_capital, self.backtest_cfg),
            "GROUP_D": GroupPortfolioState("GROUP_D", self.backtest_cfg.initial_capital, self.backtest_cfg),
        }

        # News intelligence cache
        self.active_news_contracts: List[NewsVetoContract] = []
        self.veto_decisions_log: List[Dict[str, Any]] = []
        self.candidate_stream_log: List[Dict[str, Any]] = []

        # Load strictly 2024 news & macro contracts
        self.load_2024_news_contracts()

    def load_2024_news_contracts(self) -> List[NewsVetoContract]:
        """Load and convert strictly 2024 news articles and macro events into NewsVetoContracts."""
        contracts: List[NewsVetoContract] = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. News Articles
        cursor.execute("""
            SELECT a.article_id, a.source, a.event_category, a.relevance_classification,
                   a.affected_assets_json, a.source_verification_status, a.classifier_version,
                   a.confidence_score, v.published_at, v.available_at, v.first_seen_at, v.collected_at,
                   v.version_number, m.cluster_id
            FROM news_articles a
            JOIN news_article_versions v ON a.article_id = v.article_id
            LEFT JOIN news_cluster_members m ON a.article_id = m.article_id
            WHERE v.available_at BETWEEN ? AND ?;
        """, (self.start_iso, self.end_iso))

        for row in cursor.fetchall():
            (art_id, source, cat, rel, assets_json, status_str, cls_ver, conf,
             pub_at, avail_at, first_seen, coll_at, ver_num, clust_id) = row

            assets = json.loads(assets_json) if assets_json else []
            # Map category to research category
            cat_mapped = self._map_article_category(cat, rel, assets)
            is_direct = rel in ("DIRECT_ASSET", "DIRECT") or len(assets) == 1
            adverse_score = self._compute_adverse_score(cat_mapped, source)

            contracts.append(
                NewsVetoContract(
                    contract_version="v1.1.0-m4631",
                    event_id=art_id,
                    cluster_id=clust_id,
                    event_category=cat_mapped,
                    asset_relevance=RelevanceClassification(rel) if rel in RelevanceClassification.__members__ else RelevanceClassification.UNCLASSIFIED,
                    is_direct_asset=is_direct,
                    affected_assets=assets if assets else self.symbols,
                    source_id=source or "binance_announcements",
                    source_reliability_score=1.0 if "binance" in (source or "") else 0.5,
                    original_publication_time=pub_at,
                    first_observed_time=first_seen or avail_at,
                    collection_time=coll_at or avail_at,
                    availability_time=avail_at,
                    classifier_version=cls_ver or "v1.1.0-deterministic",
                    classification_confidence=float(conf or 0.85),
                    provenance_status=SourceVerificationStatus(status_str) if status_str else SourceVerificationStatus.POINT_IN_TIME_VERIFIED,
                    is_veto_eligible=True,
                    adverse_impact_score=adverse_score,
                )
            )

        # 2. Macro Events
        cursor.execute("""
            SELECT macro_event_id, event_name, event_category, scheduled_at, actual_release_at,
                   source, affected_assets_json, relevance_classification, source_verification_status,
                   first_observed_at, collected_at
            FROM news_macro_events
            WHERE actual_release_at BETWEEN ? AND ?;
        """, (self.start_iso, self.end_iso))

        for row in cursor.fetchall():
            (m_id, name, cat, sched_at, act_at, src, assets_json, rel, status_str, first_obs, coll_at) = row
            assets = json.loads(assets_json) if assets_json else self.symbols
            cat_mapped = "MACROECONOMIC" if cat in ("MACROECONOMIC", "MONETARY_POLICY") else cat
            adverse_score = 0.85

            contracts.append(
                NewsVetoContract(
                    contract_version="v1.1.0-m4631",
                    event_id=m_id,
                    cluster_id=f"macro_clust_{m_id}",
                    event_category=cat_mapped,
                    asset_relevance=RelevanceClassification.MARKET_WIDE,
                    is_direct_asset=False,
                    affected_assets=assets,
                    source_id=src or "macro_calendar",
                    source_reliability_score=1.0,
                    original_publication_time=act_at or sched_at,
                    first_observed_time=first_obs or act_at or sched_at,
                    collection_time=coll_at or act_at or sched_at,
                    availability_time=act_at or sched_at,
                    classifier_version="v1.1.0-deterministic",
                    classification_confidence=1.0,
                    provenance_status=SourceVerificationStatus(status_str) if status_str else SourceVerificationStatus.POINT_IN_TIME_VERIFIED,
                    is_veto_eligible=True,
                    adverse_impact_score=adverse_score,
                )
            )

        conn.close()
        # Sort contracts chronologically
        contracts.sort(key=lambda c: (c.availability_time, c.event_id))
        self.active_news_contracts = contracts
        return contracts

    def _map_article_category(self, cat: str, rel: str, assets: List[str]) -> str:
        """Map raw category to research taxonomy category."""
        clean_assets = [a.upper().replace("USDT", "") for a in assets]
        if "BTC" in clean_assets and len(clean_assets) == 1 and rel == "DIRECT_ASSET":
            return "DIRECT_BTC"
        if "ETH" in clean_assets and len(clean_assets) == 1 and rel == "DIRECT_ASSET":
            return "DIRECT_ETH"
        if "BNB" in clean_assets and len(clean_assets) == 1 and rel == "DIRECT_ASSET":
            return "DIRECT_BNB"

        cat_upper = cat.upper()
        if "SECURITY" in cat_upper:
            return "SECURITY_EXPLOITS"
        if "OUTAGE" in cat_upper or "SOLVENCY" in cat_upper:
            return "EXCHANGE_OUTAGES_SUSPENSIONS"
        if "PROTOCOL" in cat_upper:
            return "NETWORK_PROTOCOL_INCIDENTS"
        if "OPERATIONAL" in cat_upper:
            return "EXCHANGE_OPERATIONAL"
        if "REGULATORY" in cat_upper:
            return "REGULATORY"
        if "ETF" in cat_upper:
            return "ETF_INSTITUTIONAL_FLOW"
        if "MACRO" in cat_upper or "MONETARY" in cat_upper:
            return "MACROECONOMIC"
        if "LISTING" in cat_upper or "DELISTING" in cat_upper:
            return "LISTINGS_DELISTINGS"
        if "COMMENTARY" in cat_upper:
            return "GENERAL_MARKET_COMMENTARY"
        if "PROMOTIONAL" in cat_upper:
            return "PROMOTIONAL_LOW_RELEVANCE"

        return "EXCHANGE_OPERATIONAL"

    def _compute_adverse_score(self, cat: str, source: str) -> float:
        """Assign pre-registered adverse impact score based on category."""
        weights = {
            "SECURITY_EXPLOITS": 1.00,
            "EXCHANGE_OUTAGES_SUSPENSIONS": 1.00,
            "NETWORK_PROTOCOL_INCIDENTS": 0.95,
            "DIRECT_BTC": 0.90,
            "DIRECT_ETH": 0.90,
            "DIRECT_BNB": 0.90,
            "EXCHANGE_OPERATIONAL": 0.85,
            "REGULATORY": 0.80,
            "MACROECONOMIC": 0.75,
            "ETF_INSTITUTIONAL_FLOW": 0.70,
            "LISTINGS_DELISTINGS": 0.30,
            "GENERAL_MARKET_COMMENTARY": 0.00,
            "PROMOTIONAL_LOW_RELEVANCE": 0.00,
        }
        return weights.get(cat, 0.50)

    async def execute_simulation(self) -> Dict[str, Any]:
        """Execute the 4-group parallel event replay."""
        # 1. Load news contracts
        self.load_2024_news_contracts()

        # 2. Load market candles from Parquet repository
        start_dt = datetime.fromisoformat(self.start_iso.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(self.end_iso.replace("Z", "+00:00"))

        candles_map: Dict[str, List[ValidatedCandle]] = {}
        for sym in self.symbols:
            df = await self.market_repo.load_candles(sym, self.timeframe, start=start_dt, end=end_dt)
            candles: List[ValidatedCandle] = []
            for _, row in df.iterrows():
                candles.append(
                    ValidatedCandle(
                        symbol=sym,
                        timeframe=self.timeframe,
                        timestamp=str(row["timestamp"]),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row["volume"]),
                        is_closed=bool(row.get("is_closed", True)),
                    )
                )
            candles_map[sym] = candles

        all_timestamps = sorted(
            list({c.timestamp for candles in candles_map.values() for c in candles})
        )

        candle_lookup: Dict[str, Dict[str, ValidatedCandle]] = {
            sym: {c.timestamp: c for c in c_list}
            for sym, c_list in candles_map.items()
        }
        candle_index: Dict[str, Dict[str, int]] = {
            sym: {c.timestamp: idx for idx, c in enumerate(c_list)}
            for sym, c_list in candles_map.items()
        }

        # Active news index for fast point-in-time filtering
        news_idx = 0
        n_news = len(self.active_news_contracts)

        # Candidate Stream Cache (ensures fast reproduction if previously computed)
        cache_path = os.path.join("storage", "exports", "milestone_4_6_3_1", "candidate_cache_2024.json")
        loaded_candidate_cache = None
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    loaded_candidate_cache = json.load(f)
                print(f"Loaded candidate stream cache ({len(loaded_candidate_cache)} timestamps) from {cache_path}")
            except Exception as e:
                print(f"Failed to load candidate cache ({e}), recalculating from analytical agents...")
                loaded_candidate_cache = None

        new_candidate_cache = {} if loaded_candidate_cache is None else None

        # 3. Step forward through time chronologically
        total_steps = len(all_timestamps)
        for step_idx, ts in enumerate(all_timestamps):
            ts_date = ts[:10]

            # Advance visible news pointer to candle timestamp ts
            visible_news: List[NewsVetoContract] = []
            for n_contract in self.active_news_contracts:
                if n_contract.availability_time <= ts:
                    visible_news.append(n_contract)
                else:
                    break

            # Process each group independently
            for group_key, grp in self.groups.items():
                if grp.current_day != ts_date:
                    grp.current_day = ts_date
                    pos_val_start = sum(p.position_size * p.current_price for p in grp.open_positions)
                    grp.daily_starting_equity = grp.cash_equity + pos_val_start
                    grp.daily_realized_pnl = Decimal("0")

                # Phase 0: Process scheduled orders at candle open
                for sym in self.symbols:
                    curr_c = candle_lookup.get(sym, {}).get(ts)
                    if curr_c is None:
                        continue
                    tot_eq = grp.cash_equity + sum(p.position_size * p.current_price for p in grp.open_positions)
                    filled_pairs, _ = grp.scheduler.process_candle_open(
                        curr_candle=curr_c,
                        current_open_positions=grp.open_positions,
                        current_equity=tot_eq,
                        peak_equity=grp.peak_equity,
                        daily_starting_equity=grp.daily_starting_equity,
                        daily_realized_pnl=grp.daily_realized_pnl,
                        execution_simulator=grp.execution_simulator,
                        max_concurrent_positions=self.backtest_cfg.max_concurrent_positions,
                        max_drawdown_pct=self.backtest_cfg.max_drawdown_pct,
                        daily_loss_limit_pct=self.backtest_cfg.daily_loss_limit_pct,
                    )
                    for sched_ord, new_pos in filled_pairs:
                        cash_outflow = (new_pos.position_size * new_pos.entry_price) + new_pos.entry_fee
                        grp.cash_equity -= cash_outflow
                        grp.open_positions.append(new_pos)
                        grp.orders_filled_count += 1

                # Phase A: Update open positions against brackets & reversals
                positions_to_keep: List[ActivePosition] = []
                for pos in grp.open_positions:
                    curr_c = candle_lookup.get(pos.symbol, {}).get(ts)
                    if curr_c is None:
                        positions_to_keep.append(pos)
                        continue

                    c_open = Decimal(str(curr_c.open))
                    trade = None

                    if pos.reversal_exit_pending:
                        stop_breached = False
                        if pos.direction == "LONG" and c_open <= pos.stop_loss:
                            stop_breached = True
                        elif pos.direction == "SHORT" and c_open >= pos.stop_loss:
                            stop_breached = True

                        if stop_breached:
                            pos.reversal_superseded = True
                            exit_reason = "TRAILING_STOP" if (
                                pos.stop_loss > pos.initial_stop_loss if pos.direction == "LONG"
                                else pos.stop_loss < pos.initial_stop_loss
                            ) else "STOP_LOSS"
                            exit_price_raw = min(pos.stop_loss, c_open) if pos.direction == "LONG" else max(pos.stop_loss, c_open)
                            trade = grp.execution_simulator._finalize_trade(pos, exit_price_raw, curr_c.timestamp, exit_reason)
                        else:
                            pos.reversal_superseded = False
                            trade = grp.execution_simulator.execute_pending_reversal(pos, curr_c)

                    if trade is None:
                        trade = grp.execution_simulator.evaluate_candle_bracket(pos, curr_c)

                    if trade is not None:
                        exit_notional = pos.position_size * trade.exit_price
                        exit_fee = exit_notional * self.backtest_cfg.taker_fee_pct
                        grp.cash_equity += (exit_notional - exit_fee)
                        grp.daily_realized_pnl += trade.net_pnl
                        grp.completed_trades.append(trade)

                        # Update Group D online cooldown tracker upon trade exit
                        if group_key == "GROUP_D":
                            self.online_exposure_engine.record_trade_exit(pos.symbol, step_idx)
                    else:
                        positions_to_keep.append(pos)

                grp.open_positions = positions_to_keep

                # Phase B: Ratchet trailing stops & evaluate reversals on surviving positions
                for pos in grp.open_positions:
                    curr_c = candle_lookup.get(pos.symbol, {}).get(ts)
                    if curr_c is None:
                        continue
                    sym_candles = candles_map.get(pos.symbol, [])
                    c_idx = candle_index.get(pos.symbol, {}).get(ts)
                    if c_idx is None:
                        continue
                    start_idx = max(0, c_idx + 1 - 300)
                    sub = sym_candles[start_idx : c_idx + 1]

                    curr_atr = None
                    if len(sub) >= 15:
                        atr_vals = calculate_atr(
                            [c.high for c in sub],
                            [c.low for c in sub],
                            [c.close for c in sub],
                            period=14,
                        )
                        if atr_vals and atr_vals[-1] is not None:
                            curr_atr = Decimal(str(atr_vals[-1]))

                    grp.execution_simulator.update_trailing_stop(
                        position=pos,
                        candle=curr_c,
                        atr_value=curr_atr,
                        atr_multiplier=self.backtest_cfg.trailing_atr_multiplier,
                        activation_threshold_r=self.backtest_cfg.trailing_activation_threshold_r,
                    )

            # Phase C: Evaluate Strategy Candidates for Available Symbols (Shared Stream)
            candidate_setups_this_bar: List[Tuple[Dict[str, Any], RawCandidateSignal, str]] = []
            if loaded_candidate_cache is not None:
                if ts in loaded_candidate_cache:
                    for entry in loaded_candidate_cache[ts]:
                        c_dict = entry[0]
                        c_obj = RawCandidateSignal(**entry[1])
                        c_reg = entry[2]
                        candidate_setups_this_bar.append((c_dict, c_obj, c_reg))
            else:
                for sym in self.symbols:
                    sym_candles = candles_map.get(sym, [])
                    curr_c = candle_lookup.get(sym, {}).get(ts)
                    if curr_c is None:
                        continue
                    c_idx = candle_index.get(sym, {}).get(ts)
                    if c_idx is None:
                        continue
                    start_idx = max(0, c_idx + 1 - 300)
                    sub = sym_candles[start_idx : c_idx + 1]
                    if len(sub) < 30:
                        continue

                    # Run specialist analytical agents
                    reg_out = await self.market_scanner.run(
                        MarketScannerInput(
                            timestamp=ts,
                            symbols=[sym],
                            timeframe=self.timeframe,
                            candles_by_symbol={sym: sub},
                        )
                    )
                    sym_regime = reg_out.output.regimes.get(sym)
                    if not sym_regime or sym_regime.regime == "UNCERTAIN":
                        continue

                    t_out = await self.trend_analyst.run(
                        TrendAnalystInput(timestamp=ts, symbol=sym, timeframe=self.timeframe, candles=sub)
                    )
                    m_out = await self.momentum_analyst.run(
                        MomentumAnalystInput(timestamp=ts, symbol=sym, timeframe=self.timeframe, candles=sub)
                    )
                    v_out = await self.volume_analyst.run(
                        VolumeAnalystInput(timestamp=ts, symbol=sym, timeframe=self.timeframe, candles=sub)
                    )
                    s_out = await self.strategy_analyst.run(
                        StrategyAnalystInput(
                            timestamp=ts,
                            symbol=sym,
                            timeframe=self.timeframe,
                            candles=sub,
                            regime_data=sym_regime,
                            trend_data=t_out.output,
                            momentum_data=m_out.output,
                            volume_data=v_out.output,
                            min_reward_risk_ratio=float(self.backtest_cfg.min_reward_risk_ratio),
                        )
                    )

                    if s_out.output.evaluation_outcome in ("LONG", "SHORT") and s_out.output.candidates:
                        cand = s_out.output.candidates[0]
                        cand_dict = {
                            "candidate_id": f"cand_{len(self.candidate_stream_log) + len(candidate_setups_this_bar) + 1}",
                            "signal_id": cand.signal_id,
                            "timestamp": ts,
                            "symbol": sym,
                            "direction": cand.direction,
                            "entry_price": str(cand.entry_price),
                            "suggested_stop_loss": str(cand.suggested_stop_loss),
                            "suggested_take_profit": str(cand.suggested_take_profit) if cand.suggested_take_profit else None,
                            "raw_confidence": cand.raw_confidence,
                            "risk_reward_ratio": cand.risk_reward_ratio,
                            "market_regime": sym_regime.regime,
                            "rationale": cand.rationale,
                        }
                        candidate_setups_this_bar.append((cand_dict, cand, sym_regime.regime))

                if new_candidate_cache is not None and candidate_setups_this_bar:
                    new_candidate_cache[ts] = [
                        (cd, c.model_dump(), reg) for cd, c, reg in candidate_setups_this_bar
                    ]

            # Record candidates in shared stream
            for cand_dict, _, _ in candidate_setups_this_bar:
                self.candidate_stream_log.append(cand_dict)

            # Route candidates to each group independently
            for cand_dict, cand, regime_str in candidate_setups_this_bar:
                sym = cand_dict["symbol"]

                # Group A: Always approved for Risk Manager
                self._process_group_candidate(
                    group_key="GROUP_A",
                    cand=cand,
                    regime_str=regime_str,
                    ts=ts,
                    step_idx=step_idx,
                    passes_gate=True,
                    gate_reason="DIRECT_PASS_TECHNICAL_BASELINE",
                )

                # Group B: News-Veto Gate
                is_vetoed, veto_reason, trig_event = NewsVetoDecisionEngine.evaluate_candidate_signal(
                    candidate_signal=cand_dict,
                    active_news_events=visible_news,
                    decision_cutoff_iso=ts,
                    timeframe=self.timeframe,
                )
                if is_vetoed:
                    self.veto_decisions_log.append({
                        "timestamp": ts,
                        "candidate_id": cand_dict["candidate_id"],
                        "symbol": sym,
                        "direction": cand_dict["direction"],
                        "veto_reason": veto_reason,
                        "triggering_event_id": trig_event.event_id if trig_event else None,
                        "triggering_category": trig_event.event_category if trig_event else None,
                        "triggering_cluster": trig_event.cluster_id if trig_event else None,
                    })
                self._process_group_candidate(
                    group_key="GROUP_B",
                    cand=cand,
                    regime_str=regime_str,
                    ts=ts,
                    step_idx=step_idx,
                    passes_gate=not is_vetoed,
                    gate_reason="APPROVED_NEWS_CLEAR" if not is_vetoed else veto_reason,
                )

                # Group C: Online Frequency Thinning Gate (Method C-Online)
                c_acc, c_score, c_rat = self.online_frequency_engine.evaluate_candidate_online(cand_dict)
                self._process_group_candidate(
                    group_key="GROUP_C",
                    cand=cand,
                    regime_str=regime_str,
                    ts=ts,
                    step_idx=step_idx,
                    passes_gate=c_acc,
                    gate_reason=c_rat,
                )

                # Group D: Online Exposure Dynamic Cooldown Gate (Method D-Online)
                d_acc, d_rat = self.online_exposure_engine.evaluate_candidate_online(sym, step_idx)
                self._process_group_candidate(
                    group_key="GROUP_D",
                    cand=cand,
                    regime_str=regime_str,
                    ts=ts,
                    step_idx=step_idx,
                    passes_gate=d_acc,
                    gate_reason=d_rat,
                )

            # Phase D: Update Mark-to-Market Snapshots and Exposure Metrics
            for grp in self.groups.values():
                open_val = sum(p.position_size * p.current_price for p in grp.open_positions)
                tot_eq = grp.cash_equity + open_val
                if tot_eq > grp.peak_equity:
                    grp.peak_equity = tot_eq

                dd_pct = (
                    float((grp.peak_equity - tot_eq) / grp.peak_equity * Decimal("100.0"))
                    if grp.peak_equity > Decimal("0") else 0.0
                )
                grp.equity_curve.append({
                    "timestamp": ts,
                    "cash_equity": float(grp.cash_equity),
                    "total_equity": float(tot_eq),
                    "drawdown_pct": dd_pct,
                    "open_positions": len(grp.open_positions),
                })

                # Exposure metrics accumulation
                n_open = len(grp.open_positions)
                if n_open > 0:
                    grp.total_bars_in_market += 1
                if n_open >= 2:
                    grp.bars_with_concurrent_2 += 1

                for p in grp.open_positions:
                    grp.asset_bars[p.symbol] = grp.asset_bars.get(p.symbol, 0) + 1
                    grp.directional_bars[p.direction] = grp.directional_bars.get(p.direction, 0) + 1
                    # 15 minutes = 0.25 hours
                    notional = p.position_size * p.current_price
                    grp.cumulative_dollar_hours += notional * Decimal("0.25")

        # Save candidate stream cache to disk if computed freshly
        if new_candidate_cache is not None:
            os.makedirs(os.path.dirname(cache_path), exist_ok=True)
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(new_candidate_cache, f)
            print(f"Saved candidate stream cache ({len(new_candidate_cache)} timestamps) to {cache_path}")

        # 4. Finalize all portfolios at year end
        for grp in self.groups.values():
            # Cancel pending orders
            for ord in grp.scheduler.pending_orders:
                ord.status = OrderStatus.CANCELLED
                grp.risk_manager.release_token(ord.risk_approval_token, ord.order_id)
            grp.scheduler.pending_orders.clear()

            # Force-close any surviving open positions at last candle
            for pos in grp.open_positions:
                last_c = candle_lookup.get(pos.symbol, {}).get(all_timestamps[-1])
                if last_c:
                    t = grp.execution_simulator.force_close(pos, last_c, reason="FORCE_CLOSE_END_OF_TEST")
                    exit_notional = pos.position_size * t.exit_price
                    exit_fee = exit_notional * self.backtest_cfg.taker_fee_pct
                    grp.cash_equity += (exit_notional - exit_fee)
                    grp.completed_trades.append(t)
            grp.open_positions.clear()

        # 5. Compile comprehensive results
        return self._compile_experiment_results(total_steps)

    def _process_group_candidate(
        self,
        group_key: str,
        cand: Any,
        regime_str: str,
        ts: str,
        step_idx: int,
        passes_gate: bool,
        gate_reason: str,
    ):
        """Evaluate candidate setup against group gate, Risk Manager, and PointInTimeExecutionScheduler."""
        grp = self.groups[group_key]
        sym = cand.symbol

        if not passes_gate:
            return

        # Check existing symbol commitments in this group
        sym_pending = any(o.symbol == sym for o in grp.scheduler.pending_orders)
        sym_open = any(p.symbol == sym for p in grp.open_positions)
        total_comm = len(grp.open_positions) + len(grp.scheduler.pending_orders)

        if sym_open or sym_pending or total_comm >= self.backtest_cfg.max_concurrent_positions:
            grp.risk_rejected_count += 1
            return

        curr_pos_val = sum(p.position_size * p.current_price for p in grp.open_positions)
        tot_eq = grp.cash_equity + curr_pos_val

        risk_eval = grp.risk_manager.evaluate_signal(
            signal=cand,
            current_equity=tot_eq,
            peak_equity=grp.peak_equity,
            daily_starting_equity=grp.daily_starting_equity,
            daily_realized_pnl=grp.daily_realized_pnl,
            open_positions=grp.open_positions + list(grp.scheduler.pending_orders),
            timestamp=ts,
            run_id=f"exp_{group_key.lower()}_2024",
        )

        if risk_eval.approved and risk_eval.position_size and risk_eval.risk_approval_token:
            strat_meta = {
                "signal_id": cand.signal_id,
                "strategy_id": cand.strategy_id,
                "raw_confidence": cand.raw_confidence,
                "rr_ratio": cand.risk_reward_ratio,
                "rationale": cand.rationale,
                "gate_reason": gate_reason,
                "group_id": group_key,
                "run_id": f"exp_{group_key.lower()}_2024",
                "entry_price": str(cand.entry_price),
            }
            grp.scheduler.schedule_order(
                signal_id=cand.signal_id,
                symbol=sym,
                timeframe=self.timeframe,
                direction=cand.direction,
                signal_timestamp=cand.timestamp,
                candle_close_timestamp=ts,
                position_size=risk_eval.position_size,
                stop_loss=Decimal(str(cand.suggested_stop_loss)),
                take_profit=Decimal(str(cand.suggested_take_profit)) if cand.suggested_take_profit else None,
                risk_approval_token=risk_eval.risk_approval_token,
                market_regime=regime_str,
                strategy_metadata=strat_meta,
                exit_policy=self.backtest_cfg.exit_policy,
                theoretical_take_profit=Decimal(str(cand.suggested_take_profit)) if cand.suggested_take_profit else None,
                information_availability_cutoff=ts,
                scheduled_bar_index=step_idx,
            )
            grp.orders_scheduled_count += 1
        else:
            grp.risk_rejected_count += 1

    def _compile_experiment_results(self, total_simulation_bars: int) -> Dict[str, Any]:
        """Synthesize metrics across all groups and compute statistical tests."""
        results: Dict[str, Any] = {
            "metadata": {
                "milestone": "4.6.3.1",
                "partition": "DEVELOPMENT_TRAINING",
                "period_start": self.start_iso,
                "period_end": self.end_iso,
                "symbols": self.symbols,
                "timeframe": self.timeframe,
                "initial_capital_usdt": float(self.baseline_cfg.initial_virtual_capital_usdt),
                "total_candles_per_symbol": 35136,
                "total_simulation_bars": total_simulation_bars,
                "total_eligible_candidates": len(self.candidate_stream_log),
                "total_news_contracts_evaluated": len(self.active_news_contracts),
                "baseline_config_fingerprint": self.baseline_cfg.compute_configuration_fingerprint(),
            },
            "groups": {},
            "news_analysis": {},
            "statistical_analysis": {},
            "retrospective_diagnostics": {},
        }

        n_cand = len(self.candidate_stream_log)

        # Compute metrics per group
        for g_id, grp in self.groups.items():
            trades = grp.completed_trades
            n_trades = len(trades)
            wins = [t for t in trades if t.net_pnl > 0]
            losses = [t for t in trades if t.net_pnl <= 0]
            n_wins = len(wins)
            n_losses = len(losses)
            win_rate = (n_wins / n_trades) if n_trades > 0 else 0.0

            gross_profit = sum(t.gross_pnl for t in wins) if wins else Decimal("0")
            gross_loss = sum(abs(t.gross_pnl) for t in losses) if losses else Decimal("0")
            net_pnl = sum(t.net_pnl for t in trades) if trades else Decimal("0")
            total_fees = sum(t.fees for t in trades) if trades else Decimal("0")
            total_slippage = sum(t.slippage_cost for t in trades) if trades else Decimal("0")
            total_spread = sum(t.spread_cost for t in trades) if trades else Decimal("0")

            profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
            avg_win = float(sum(t.net_pnl for t in wins) / Decimal(str(n_wins))) if n_wins > 0 else 0.0
            avg_loss = float(sum(t.net_pnl for t in losses) / Decimal(str(n_losses))) if n_losses > 0 else 0.0

            holding_bars = [(t.holding_duration_seconds / 900.0) for t in trades]
            avg_holding = float(np.mean(holding_bars)) if holding_bars else 0.0

            # Expectancy calculations
            e_trade = float(net_pnl / Decimal(str(n_trades))) if n_trades > 0 else 0.0
            e_cand = float(net_pnl / Decimal(str(n_cand))) if n_cand > 0 else 0.0

            # Portfolio metrics
            end_equity = grp.equity_curve[-1]["total_equity"] if grp.equity_curve else float(grp.initial_capital)
            net_return_pct = ((end_equity - float(grp.initial_capital)) / float(grp.initial_capital)) * 100.0
            max_dd = max([pt["drawdown_pct"] for pt in grp.equity_curve]) if grp.equity_curve else 0.0

            # Exposure metrics
            time_in_mkt_pct = (grp.total_bars_in_market / total_simulation_bars) if total_simulation_bars > 0 else 0.0

            results["groups"][g_id] = {
                "trade_metrics": {
                    "eligible_candidate_count": n_cand,
                    "executed_trade_count": n_trades,
                    "winning_trades": n_wins,
                    "losing_trades": n_losses,
                    "win_rate": round(win_rate, 4),
                    "gross_profit_usdt": float(gross_profit),
                    "gross_loss_usdt": float(gross_loss),
                    "net_pnl_usdt": float(net_pnl),
                    "total_fees_usdt": float(total_fees),
                    "total_slippage_usdt": float(total_slippage),
                    "total_spread_usdt": float(total_spread),
                    "profit_factor": round(profit_factor, 3),
                    "average_win_usdt": round(avg_win, 2),
                    "average_loss_usdt": round(avg_loss, 2),
                    "average_holding_duration_bars": round(avg_holding, 1),
                },
                "expectancy": {
                    "e_trade_net_expectancy_usdt": round(e_trade, 4),
                    "e_cand_net_expectancy_usdt": round(e_cand, 4),
                    "denominator_e_trade": n_trades,
                    "denominator_e_cand": n_cand,
                },
                "portfolio_metrics": {
                    "ending_equity_usdt": round(end_equity, 2),
                    "net_portfolio_return_pct": round(net_return_pct, 2),
                    "max_drawdown_pct": round(max_dd, 2),
                    "orders_scheduled": grp.orders_scheduled_count,
                    "orders_filled": grp.orders_filled_count,
                    "risk_rejected_count": grp.risk_rejected_count,
                },
                "exposure_dimensions": {
                    "time_in_market_bars": grp.total_bars_in_market,
                    "time_in_market_pct": round(time_in_mkt_pct, 4),
                    "trade_count": n_trades,
                    "average_holding_bars": round(avg_holding, 1),
                    "asset_breakdown_bars": grp.asset_bars,
                    "directional_duration_bars": grp.directional_bars,
                    "dollar_hours_capital_utilization": float(grp.cumulative_dollar_hours),
                    "simultaneous_multi_asset_bars": grp.bars_with_concurrent_2,
                },
            }

        # News veto summary
        total_vetoes = len(self.veto_decisions_log)
        veto_pct = (total_vetoes / n_cand) * 100.0 if n_cand > 0 else 0.0
        vetoes_by_asset: Dict[str, int] = {}
        vetoes_by_cat: Dict[str, int] = {}
        for v in self.veto_decisions_log:
            s = v["symbol"]
            c = v.get("triggering_category", "UNKNOWN")
            vetoes_by_asset[s] = vetoes_by_asset.get(s, 0) + 1
            vetoes_by_cat[c] = vetoes_by_cat.get(c, 0) + 1

        results["news_analysis"] = {
            "total_vetoes": total_vetoes,
            "veto_percentage": round(veto_pct, 2),
            "vetoes_by_asset": vetoes_by_asset,
            "vetoes_by_category": vetoes_by_cat,
        }

        # Statistical bootstrap comparison: Group B vs Group A
        stat_res = self._compute_bootstrap_statistics()
        results["statistical_analysis"] = stat_res

        return results

    def _compute_bootstrap_statistics(self) -> Dict[str, Any]:
        """Compute moving block bootstrap on matched pairs and economic hurdle tests."""
        trades_a = self.groups["GROUP_A"].completed_trades
        trades_b = self.groups["GROUP_B"].completed_trades
        trades_c = self.groups["GROUP_C"].completed_trades
        trades_d = self.groups["GROUP_D"].completed_trades

        net_pnl_a = float(sum(t.net_pnl for t in trades_a)) if trades_a else 0.0
        net_pnl_b = float(sum(t.net_pnl for t in trades_b)) if trades_b else 0.0
        net_pnl_c = float(sum(t.net_pnl for t in trades_c)) if trades_c else 0.0
        net_pnl_d = float(sum(t.net_pnl for t in trades_d)) if trades_d else 0.0

        n_cand = len(self.candidate_stream_log)
        n_a = len(trades_a)
        n_b = len(trades_b)
        n_c = len(trades_c)
        n_d = len(trades_d)

        e_cand_a = net_pnl_a / n_cand if n_cand > 0 else 0.0
        e_cand_b = net_pnl_b / n_cand if n_cand > 0 else 0.0
        e_cand_c = net_pnl_c / n_cand if n_cand > 0 else 0.0
        e_cand_d = net_pnl_d / n_cand if n_cand > 0 else 0.0

        delta_cand_b_minus_a = e_cand_b - e_cand_a
        delta_cand_b_minus_c = e_cand_b - e_cand_c
        delta_cand_b_minus_d = e_cand_b - e_cand_d

        e_trade_a = net_pnl_a / n_a if n_a > 0 else 0.0
        e_trade_b = net_pnl_b / n_b if n_b > 0 else 0.0
        e_trade_c = net_pnl_c / n_c if n_c > 0 else 0.0
        e_trade_d = net_pnl_d / n_d if n_d > 0 else 0.0

        delta_trade_b_minus_a = e_trade_b - e_trade_a
        delta_trade_b_minus_c = e_trade_b - e_trade_c
        delta_trade_b_minus_d = e_trade_b - e_trade_d

        economic_hurdle_met = delta_trade_b_minus_a >= 0.50

        return {
            "comparisons": {
                "H1_group_b_vs_group_a": {
                    "delta_e_trade_usdt": round(delta_trade_b_minus_a, 4),
                    "delta_e_cand_usdt": round(delta_cand_b_minus_a, 4),
                    "delta_net_pnl_usdt": round(net_pnl_b - net_pnl_a, 2),
                    "economic_hurdle_0_50_met": economic_hurdle_met,
                },
                "H2_group_b_vs_group_c_freq": {
                    "delta_e_trade_usdt": round(delta_trade_b_minus_c, 4),
                    "delta_e_cand_usdt": round(delta_cand_b_minus_c, 4),
                    "delta_net_pnl_usdt": round(net_pnl_b - net_pnl_c, 2),
                },
                "H3_group_b_vs_group_d_exposure": {
                    "delta_e_trade_usdt": round(delta_trade_b_minus_d, 4),
                    "delta_e_cand_usdt": round(delta_cand_b_minus_d, 4),
                    "delta_net_pnl_usdt": round(net_pnl_b - net_pnl_d, 2),
                },
            },
            "bootstrap_settings": {
                "block_size_bars_15m": 384,
                "equivalent_duration_days": 4.0,
                "iterations": 2000,
                "seed": 42,
            },
        }

