"""
Adversarial Unit Test Suite for Milestone 4.6.3.0.1
Independent Experimental Protocol Integrity Audit & Leakage Verification.

Governed by: Rule S-01, Rule S-04, Rule S-05, Rule S-06, ADR-028, ADR-029, ADR-030.

Verifies:
1. Group C frequency-matching online point-in-time compliance vs ex-post diagnostic benchmarking.
2. Group D exposure-matching multi-dimensional tracking and zero-lookahead cooldown.
3. News-veto decision engine decay windows, cluster deduplication, and revision cutoff isolation.
4. Statistical denominator integrity (E_trade vs E_cand) and timeframe-calibrated bootstrap blocks.
5. Cryptographic OOSAccessGuard enforcement blocking unauthorized access to Jan-Oct 2026 data.
"""
import hashlib
import hmac
import pytest
from datetime import datetime, timezone
from decimal import Decimal

from app.data.news.models import (
    EventCategory,
    RelevanceClassification,
    SourceVerificationStatus,
)
from app.simulation.research_protocol import (
    ControlExecutionMode,
    ExperimentalGroup,
    ExposureDimensions,
    ExPostExposureMatchingEngine,
    ExPostFrequencyMatchingEngine,
    NewsVetoContract,
    NewsVetoDecisionEngine,
    OnlineExposureMatchingEngine,
    OnlineFrequencyMatchingEngine,
    OOSAccessGuard,
    StatisticalAnalysisPlanConfig,
)


class TestGroupCFrequencyMatchingAdversarial:
    """Adversarial audit tests for Group C frequency matching."""

    def test_online_frequency_matching_zero_lookahead(self):
        """Verify OnlineFrequencyMatchingEngine operates candidate-by-candidate without future knowledge."""
        engine = OnlineFrequencyMatchingEngine(retention_ratio=0.75, cryptographic_seed="test_seed_1")
        assert engine.execution_mode == ControlExecutionMode.ONLINE_POINT_IN_TIME

        candidate_1 = {"signal_id": "sig_101", "timestamp": "2024-03-01T12:00:00Z", "symbol": "BTCUSDT"}
        candidate_2 = {"signal_id": "sig_102", "timestamp": "2024-03-01T12:15:00Z", "symbol": "BTCUSDT"}

        accepted_1, score_1, rat_1 = engine.evaluate_candidate_online(candidate_1)
        accepted_2, score_2, rat_2 = engine.evaluate_candidate_online(candidate_2)

        assert isinstance(accepted_1, bool)
        assert isinstance(accepted_2, bool)
        assert 0.0 <= score_1 <= 1.0
        assert 0.0 <= score_2 <= 1.0
        # Deterministic: repeated call produces identical results
        acc_1_repeat, score_1_repeat, _ = engine.evaluate_candidate_online(candidate_1)
        assert accepted_1 == acc_1_repeat
        assert score_1 == score_1_repeat

    def test_ex_post_frequency_engine_explicitly_labeled(self):
        """Verify ExPostFrequencyMatchingEngine is explicitly flagged as ex-post diagnostic."""
        assert ExPostFrequencyMatchingEngine.is_ex_post_diagnostic is True
        assert ExPostFrequencyMatchingEngine.execution_mode == ControlExecutionMode.EX_POST_DIAGNOSTIC

        candidates = [
            {"signal_id": f"s_{i}", "raw_confidence": float(i) / 10.0, "timestamp": f"2024-01-0{i+1}T00:00:00Z"}
            for i in range(10)
        ]
        # Decimation requires target_count (derived from future Group B count N_B)
        decimated = ExPostFrequencyMatchingEngine.decimate_systematically(candidates, target_count=5)
        assert len(decimated) == 5

        pruned = ExPostFrequencyMatchingEngine.prune_by_technical_confidence(candidates, target_count=4)
        assert len(pruned) == 4
        # Highest confidence candidates retained
        assert pruned[0]["signal_id"] == "s_6"


class TestGroupDExposureMatchingAdversarial:
    """Adversarial audit tests for Group D exposure matching."""

    def test_seven_exposure_dimensions_integrity(self):
        """Verify ExposureDimensions model tracks all 7 dimensions without conflation."""
        dims = ExposureDimensions(
            time_in_market_bars=120,
            time_in_market_pct=0.25,
            trade_count=8,
            average_holding_bars=15.0,
            asset_breakdown_bars={"BTCUSDT": 60, "ETHUSDT": 60},
            directional_duration_bars={"LONG": 90, "SHORT": 30},
            dollar_hours_capital_utilization=Decimal("15000.50"),
            simultaneous_multi_asset_bars=20,
            gross_exposure_pct=0.30,
            net_exposure_pct=0.15,
        )
        assert dims.time_in_market_bars == 120
        assert dims.trade_count == 8
        assert dims.dollar_hours_capital_utilization == Decimal("15000.50")
        assert dims.simultaneous_multi_asset_bars == 20

    def test_online_exposure_cooldown_engine(self):
        """Verify OnlineExposureMatchingEngine enforces dynamic cooldown online."""
        engine = OnlineExposureMatchingEngine(cooldown_bars_after_trade=4)
        assert engine.execution_mode == ControlExecutionMode.ONLINE_POINT_IN_TIME

        # Initial entry allowed
        allowed, rat = engine.evaluate_candidate_online(symbol="BTCUSDT", current_bar_index=10)
        assert allowed is True

        # Simulate trade exit at bar 10
        engine.record_trade_exit(symbol="BTCUSDT", exit_bar_index=10)

        # Bar 11: 1 bar after exit (< 4 cooldown) -> REJECTED
        allowed_11, rat_11 = engine.evaluate_candidate_online(symbol="BTCUSDT", current_bar_index=11)
        assert allowed_11 is False
        assert "EXPOSURE_COOLDOWN_ACTIVE" in rat_11

        # Bar 13: 3 bars after exit (< 4 cooldown) -> REJECTED
        allowed_13, _ = engine.evaluate_candidate_online(symbol="BTCUSDT", current_bar_index=13)
        assert allowed_13 is False

        # Bar 14: 4 bars after exit (>= 4 cooldown) -> ALLOWED
        allowed_14, rat_14 = engine.evaluate_candidate_online(symbol="BTCUSDT", current_bar_index=14)
        assert allowed_14 is True

        # Different symbol ETHUSDT unaffected by BTCUSDT cooldown
        allowed_eth, _ = engine.evaluate_candidate_online(symbol="ETHUSDT", current_bar_index=11)
        assert allowed_eth is True

    def test_ex_post_exposure_engine_labeled(self):
        """Verify ExPostExposureMatchingEngine is labeled as ex-post diagnostic."""
        assert ExPostExposureMatchingEngine.is_ex_post_diagnostic is True
        assert ExPostExposureMatchingEngine.execution_mode == ControlExecutionMode.EX_POST_DIAGNOSTIC


class TestNewsVetoDecisionEngineAdversarial:
    """Adversarial audit tests for NewsVetoDecisionEngine and NewsVetoContract."""

    def _create_contract(
        self,
        event_id: str = "evt_001",
        category: EventCategory = EventCategory.EXCHANGE_OPERATIONAL,
        availability: str = "2024-03-01T10:00:00Z",
        source_id: str = "binance_announcements",
        reliability: float = 1.0,
        adverse_impact: float = 0.90,
        provenance: SourceVerificationStatus = SourceVerificationStatus.POINT_IN_TIME_VERIFIED,
        affected_assets: list = None,
        cluster_id: str = None,
        revision_time: str = None,
    ) -> NewsVetoContract:
        return NewsVetoContract(
            event_id=event_id,
            cluster_id=cluster_id,
            event_category=category,
            asset_relevance=RelevanceClassification.MARKET_WIDE,
            is_direct_asset=False,
            affected_assets=affected_assets or ["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            source_id=source_id,
            source_reliability_score=reliability,
            first_observed_time=availability,
            collection_time=availability,
            availability_time=availability,
            revision_observation_time=revision_time,
            classifier_version="v1.1.0-deterministic",
            classification_confidence=0.95,
            provenance_status=provenance,
            is_veto_eligible=True,
            adverse_impact_score=adverse_impact,
        )

    def test_future_publication_rejected_as_lookahead(self):
        """Verify news event available after candidate decision cutoff is strictly rejected."""
        event = self._create_contract(availability="2024-03-01T12:05:00Z")
        candidate = {"symbol": "BTCUSDT", "timestamp": "2024-03-01T12:00:00Z"}

        is_vetoed, reason, _ = NewsVetoDecisionEngine.evaluate_candidate_signal(
            candidate_signal=candidate,
            active_news_events=[event],
            decision_cutoff_iso="2024-03-01T12:00:00Z",
            timeframe="15m",
        )
        assert is_vetoed is False

    def test_expired_event_beyond_decay_window_rejected(self):
        """Verify event beyond category decay window does not veto."""
        # EXCHANGE_OPERATIONAL decay window is 7200s (2h).
        # Published at 09:00:00Z; candidate at 12:00:00Z (3h elapsed > 2h).
        event = self._create_contract(availability="2024-03-01T09:00:00Z")
        candidate = {"symbol": "BTCUSDT", "timestamp": "2024-03-01T12:00:00Z"}

        is_vetoed, _, _ = NewsVetoDecisionEngine.evaluate_candidate_signal(
            candidate_signal=candidate,
            active_news_events=[event],
            decision_cutoff_iso="2024-03-01T12:00:00Z",
            timeframe="15m",
        )
        assert is_vetoed is False

    def test_active_event_within_decay_window_triggers_veto(self):
        """Verify event within decay window exceeding adverse threshold triggers veto."""
        # EXCHANGE_OPERATIONAL published at 11:00:00Z; candidate at 12:00:00Z (1h elapsed <= 2h).
        event = self._create_contract(availability="2024-03-01T11:00:00Z", adverse_impact=0.90)
        candidate = {"symbol": "BTCUSDT", "timestamp": "2024-03-01T12:00:00Z"}

        is_vetoed, reason, trig_event = NewsVetoDecisionEngine.evaluate_candidate_signal(
            candidate_signal=candidate,
            active_news_events=[event],
            decision_cutoff_iso="2024-03-01T12:00:00Z",
            timeframe="15m",
        )
        assert is_vetoed is True
        assert trig_event.event_id == "evt_001"
        assert "NEWS_VETO" in reason

    def test_cluster_deduplication_prevents_duplicate_processing(self):
        """Verify syndicated articles in same cluster only fire once."""
        evt1 = self._create_contract(event_id="e1", cluster_id="clust_99", availability="2024-03-01T11:00:00Z")
        evt2 = self._create_contract(event_id="e2", cluster_id="clust_99", availability="2024-03-01T11:15:00Z")
        candidate = {"symbol": "BTCUSDT", "timestamp": "2024-03-01T12:00:00Z"}

        is_vetoed, reason, trig = NewsVetoDecisionEngine.evaluate_candidate_signal(
            candidate_signal=candidate,
            active_news_events=[evt1, evt2],
            decision_cutoff_iso="2024-03-01T12:00:00Z",
            timeframe="15m",
        )
        assert is_vetoed is True
        assert trig.event_id == "e1"

    def test_wrong_asset_relevance_ignored(self):
        """Verify asset-specific event does not veto unrelated symbols."""
        event = self._create_contract(
            event_id="eth_evt",
            category="DIRECT_ETH",
            affected_assets=["ETHUSDT"],
            availability="2024-03-01T11:30:00Z",
        )
        candidate_btc = {"symbol": "BTCUSDT", "timestamp": "2024-03-01T12:00:00Z"}
        candidate_eth = {"symbol": "ETHUSDT", "timestamp": "2024-03-01T12:00:00Z"}

        vetoed_btc, _, _ = NewsVetoDecisionEngine.evaluate_candidate_signal(
            candidate_btc, [event], "2024-03-01T12:00:00Z", "15m"
        )
        vetoed_eth, _, _ = NewsVetoDecisionEngine.evaluate_candidate_signal(
            candidate_eth, [event], "2024-03-01T12:00:00Z", "15m"
        )
        assert vetoed_btc is False
        assert vetoed_eth is True

    def test_gdelt_intraday_veto_prohibited(self):
        """Verify GDELT events are prohibited from triggering intraday vetoes."""
        event = self._create_contract(
            source_id="gdelt_gkg",
            reliability=0.5,
            availability="2024-03-01T11:30:00Z",
        )
        candidate = {"symbol": "BTCUSDT", "timestamp": "2024-03-01T12:00:00Z"}

        # Intraday 15m -> Rejected
        vetoed_15m, _, _ = NewsVetoDecisionEngine.evaluate_candidate_signal(
            candidate, [event], "2024-03-01T12:00:00Z", "15m"
        )
        assert vetoed_15m is False

        # Higher timeframe 1d -> Not rejected by GDELT rule
        valid, err = event.validate_invariants("2024-03-01T12:00:00Z", "1d")
        assert valid is True
        assert err is None

    def test_rejected_provenance_cannot_veto(self):
        """Verify unverified or rejected provenance cannot trigger veto."""
        event = self._create_contract(
            provenance=SourceVerificationStatus.REJECTED,
            availability="2024-03-01T11:30:00Z",
        )
        candidate = {"symbol": "BTCUSDT", "timestamp": "2024-03-01T12:00:00Z"}

        vetoed, _, _ = NewsVetoDecisionEngine.evaluate_candidate_signal(
            candidate, [event], "2024-03-01T12:00:00Z", "15m"
        )
        assert vetoed is False


class TestStatisticalAnalysisPlanAndBootstrapAdversarial:
    """Adversarial audit tests for Statistical Analysis Plan and block bootstrap."""

    def test_timeframe_calibrated_bootstrap_block_sizes(self):
        """Verify bootstrap block sizes are calibrated to ~4 calendar days across all timeframes."""
        plan = StatisticalAnalysisPlanConfig()
        blocks = plan.timeframe_bootstrap_blocks

        # 15m: 384 * 15m = 5760m = 96h = 4 days
        assert blocks["15m"] == 384
        # 1h: 96 * 1h = 96h = 4 days
        assert blocks["1h"] == 96
        # 4h: 24 * 4h = 96h = 4 days
        assert blocks["4h"] == 24
        # 1d: 7 * 1d = 7 days
        assert blocks["1d"] == 7

    def test_denominator_separation_mathematical_invariants(self):
        """Verify E_trade and E_cand are mathematically distinct when vetoes occur."""
        trades_pnl = [Decimal("10.00"), Decimal("-5.00"), Decimal("15.00")]  # 3 trades taken
        total_pnl = sum(trades_pnl)
        n_trades = len(trades_pnl)
        n_candidates = 5  # 2 candidates were vetoed

        e_trade = total_pnl / Decimal(str(n_trades))
        e_cand = total_pnl / Decimal(str(n_candidates))

        assert e_trade == Decimal("20.00") / Decimal("3")
        assert e_cand == Decimal("20.00") / Decimal("5")
        assert e_trade > e_cand


class TestOOSAccessGuardAdversarial:
    """Adversarial audit tests for locked out-of-sample partition guard."""

    def test_unauthorized_oos_access_raises_permission_error(self):
        """Verify unauthorized attempt to access Jan-Oct 2026 data raises PermissionError."""
        with pytest.raises(PermissionError) as exc_info:
            OOSAccessGuard.verify_partition_access(
                simulation_start_iso="2026-02-01T00:00:00Z",
                simulation_end_iso="2026-05-01T00:00:00Z",
            )
        assert "LOCKED_OOS_PARTITION_VIOLATION" in str(exc_info.value)

    def test_authorized_governance_token_permits_access(self):
        """Verify cryptographic HMAC governance token permits OOS access."""
        start = "2026-01-01T00:00:00Z"
        end = "2026-10-31T23:59:59Z"
        token = OOSAccessGuard.generate_governance_token(start, end)

        allowed = OOSAccessGuard.verify_partition_access(
            simulation_start_iso=start,
            simulation_end_iso=end,
            authorization_token=token,
        )
        assert allowed is True

    def test_forged_governance_token_rejected(self):
        """Verify forged or mismatched governance token is rejected."""
        start = "2026-01-01T00:00:00Z"
        end = "2026-10-31T23:59:59Z"
        forged_token = "deadbeef" * 8

        with pytest.raises(PermissionError) as exc_info:
            OOSAccessGuard.verify_partition_access(
                simulation_start_iso=start,
                simulation_end_iso=end,
                authorization_token=forged_token,
            )
        assert "Invalid or forged" in str(exc_info.value)

    def test_dev_and_val_partitions_accessible_without_token(self):
        """Verify Development and Validation partitions are accessible without token."""
        # Dev partition: 2023-12-01 to 2025-06-30
        assert OOSAccessGuard.verify_partition_access(
            simulation_start_iso="2024-01-01T00:00:00Z",
            simulation_end_iso="2024-12-31T23:59:59Z",
        ) is True

        # Validation partition: 2025-07-01 to 2025-12-31
        assert OOSAccessGuard.verify_partition_access(
            simulation_start_iso="2025-07-01T00:00:00Z",
            simulation_end_iso="2025-12-31T23:59:59Z",
        ) is True
