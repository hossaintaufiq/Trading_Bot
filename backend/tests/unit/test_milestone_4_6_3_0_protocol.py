"""
Unit tests for Milestone 4.6.3.0: News-Gated Experiment Design, Baseline Freeze & Research Protocol.
"""
import copy
import hashlib
import json
import os
import pytest
from decimal import Decimal

from app.data.news.models import (
    EventCategory,
    RelevanceClassification,
    SourceVerificationStatus,
)
from app.simulation.models import ExecutionPolicy
from app.simulation.research_protocol import (
    ChronologicalPartition,
    ChronologicalSplitManifest,
    ExperimentReproducibilityFingerprint,
    ExperimentalGroup,
    ExperimentalGroupDefinition,
    ExposureMatchingEngine,
    FrequencyMatchingEngine,
    FrozenBaselineConfig,
    MatchingMethodology,
    NewsVetoContract,
    PartitionType,
    ResearchTaxonomyRegistry,
    StatisticalAnalysisPlanConfig,
)


class TestMilestone4630BaselineFreeze:
    """Verifies that the deterministic technical baseline configuration is frozen and parameter-accurate."""

    def test_baseline_parameters_strict_compliance(self):
        cfg = FrozenBaselineConfig()

        # Virtual capital & spot leverage
        assert cfg.initial_virtual_capital_usdt == Decimal("1000.00")
        assert cfg.leverage_allowed is False
        assert cfg.max_spot_leverage == Decimal("1.0")

        # Risk parameters
        assert cfg.max_concurrent_positions == 2
        assert cfg.max_risk_per_trade_pct == Decimal("0.005") # 0.5%
        assert cfg.daily_simulated_loss_limit_pct == Decimal("0.02") # 2.0%
        assert cfg.max_drawdown_circuit_breaker_pct == Decimal("0.05") # 5.0%
        assert cfg.min_reward_risk_ratio == Decimal("1.5")
        assert cfg.min_notional_order_usdt == Decimal("10.00")

        # Execution policy
        assert cfg.execution_policy == ExecutionPolicy.NEXT_ELIGIBLE_PRICE
        assert cfg.max_execution_gap_bars_15m == 1
        assert cfg.max_execution_gap_bars_htf == 3

        # Cost & Friction Model
        assert cfg.maker_fee_pct == Decimal("0.001") # 0.10%
        assert cfg.taker_fee_pct == Decimal("0.001") # 0.10%
        assert cfg.adverse_slippage_pct == Decimal("0.0005") # 0.05%
        assert cfg.bid_ask_spread_bps == Decimal("2.0") # 2 bps
        assert cfg.half_spread_pct == Decimal("0.0001") # 0.01%
        assert cfg.round_trip_friction_pct == Decimal("0.0032") # 0.32%

        # Protective mechanics
        assert cfg.exit_policy == "BALANCED"
        assert cfg.stop_loss_atr_multiplier == Decimal("2.0")
        assert cfg.trailing_stop_atr_multiplier == Decimal("2.0")
        assert cfg.trailing_activation_threshold_r == Decimal("1.0")
        assert cfg.conservative_ambiguous_bars is True

    def test_baseline_fingerprint_deterministic_stability(self):
        cfg1 = FrozenBaselineConfig()
        cfg2 = FrozenBaselineConfig()
        fp1 = cfg1.compute_configuration_fingerprint()
        fp2 = cfg2.compute_configuration_fingerprint()

        assert fp1 == fp2
        assert len(fp1) == 64 # SHA-256

        # Modifying any single parameter must mutate the fingerprint
        cfg_mutated = copy.deepcopy(cfg1)
        cfg_mutated.initial_virtual_capital_usdt = Decimal("1000.01")
        assert cfg_mutated.compute_configuration_fingerprint() != fp1

        cfg_mutated2 = copy.deepcopy(cfg1)
        cfg_mutated2.taker_fee_pct = Decimal("0.0011")
        assert cfg_mutated2.compute_configuration_fingerprint() != fp1


class TestMilestone4630ExperimentalGroupsParity:
    """Verifies the four experimental groups definition and operational parity."""

    def test_four_groups_exist(self):
        assert len(ExperimentalGroup) == 4
        assert ExperimentalGroup.GROUP_A_TECHNICAL_BASELINE in ExperimentalGroup
        assert ExperimentalGroup.GROUP_B_NEWS_VETO in ExperimentalGroup
        assert ExperimentalGroup.GROUP_C_FREQUENCY_MATCHED in ExperimentalGroup
        assert ExperimentalGroup.GROUP_D_EXPOSURE_MATCHED in ExperimentalGroup

    def test_non_negotiable_group_invariants(self):
        groups = [
            ExperimentalGroupDefinition(
                group_id=ExperimentalGroup.GROUP_A_TECHNICAL_BASELINE,
                group_name="Group A",
                description="Baseline",
                is_reference_group=True,
                uses_news_intelligence=False,
            ),
            ExperimentalGroupDefinition(
                group_id=ExperimentalGroup.GROUP_B_NEWS_VETO,
                group_name="Group B",
                description="News Veto",
                uses_news_intelligence=True,
            ),
            ExperimentalGroupDefinition(
                group_id=ExperimentalGroup.GROUP_C_FREQUENCY_MATCHED,
                group_name="Group C",
                description="Frequency-Matched",
                uses_news_intelligence=False,
                matching_methodology=MatchingMethodology.DETERMINISTIC_CRYPTOGRAPHIC_SEED,
            ),
            ExperimentalGroupDefinition(
                group_id=ExperimentalGroup.GROUP_D_EXPOSURE_MATCHED,
                group_name="Group D",
                description="Exposure-Matched",
                uses_news_intelligence=False,
                matching_methodology=MatchingMethodology.DYNAMIC_COOLDOWN_BUDGET,
            ),
        ]

        for g in groups:
            # Rule S-01, Rule S-04: No group may independently trade news or override Risk Manager
            assert g.allows_directional_news_signals is False
            assert g.overrides_risk_manager is False
            assert g.execution_policy == ExecutionPolicy.NEXT_ELIGIBLE_PRICE


class TestMilestone4630TaxonomyAndVetoContract:
    """Verifies the 13-category research taxonomy and NewsVetoContract validation rules."""

    def test_thirteen_categories_present(self):
        rules = ResearchTaxonomyRegistry.RULES
        assert len(rules) == 13

        # Check all required categories from specification
        expected_keys = [
            "EXCHANGE_OPERATIONAL",
            "DIRECT_BTC",
            "DIRECT_ETH",
            "DIRECT_BNB",
            "NETWORK_PROTOCOL_INCIDENTS",
            "SECURITY_EXPLOITS",
            "EXCHANGE_OUTAGES_SUSPENSIONS",
            "REGULATORY",
            "MACROECONOMIC",
            "ETF_INSTITUTIONAL_FLOW",
            "LISTINGS_DELISTINGS",
            "GENERAL_MARKET_COMMENTARY",
            "PROMOTIONAL_LOW_RELEVANCE",
        ]
        for k in expected_keys:
            assert k in rules
            assert rules[k].category_id == k

    def test_excluded_categories_enforcement(self):
        comm_rule = ResearchTaxonomyRegistry.get_rule("GENERAL_MARKET_COMMENTARY")
        promo_rule = ResearchTaxonomyRegistry.get_rule("PROMOTIONAL_LOW_RELEVANCE")

        assert comm_rule.is_research_eligible is False
        assert comm_rule.exclusion_reason == "EXCLUDED_UNVERIFIED_OPINION_AND_NOISE"
        assert comm_rule.adverse_veto_weight == 0.0

        assert promo_rule.is_research_eligible is False
        assert promo_rule.exclusion_reason == "EXCLUDED_RETAIL_MARKETING_NO_ECONOMIC_SIGNAL"
        assert promo_rule.adverse_veto_weight == 0.0

    def test_news_veto_contract_lookahead_validation(self):
        contract = NewsVetoContract(
            event_id="evt_001",
            event_category=EventCategory.SECURITY_INCIDENT,
            asset_relevance=RelevanceClassification.MARKET_WIDE,
            is_direct_asset=False,
            affected_assets=["BTCUSDT", "ETHUSDT"],
            source_id="binance_announcements",
            source_reliability_score=1.0,
            first_observed_time="2024-06-15T12:00:00Z",
            collection_time="2024-06-15T12:00:01Z",
            availability_time="2024-06-15T12:00:00Z",
            classifier_version="v1.1.0-deterministic",
            classification_confidence=1.0,
            provenance_status=SourceVerificationStatus.POINT_IN_TIME_VERIFIED,
            is_veto_eligible=True,
        )

        # Available at 12:00:00, decision cutoff is 12:15:00 -> Valid
        valid, reason = contract.validate_invariants("2024-06-15T12:15:00Z", "15m")
        assert valid is True
        assert reason is None

        # Available at 12:00:00, decision cutoff is 11:45:00 -> Lookahead violation!
        valid_fut, reason_fut = contract.validate_invariants("2024-06-15T11:45:00Z", "15m")
        assert valid_fut is False
        assert "LOOKAHEAD_VIOLATION" in reason_fut

    def test_gdelt_intraday_restriction_enforcement(self):
        contract = NewsVetoContract(
            event_id="evt_gdelt_001",
            event_category=EventCategory.REGULATORY,
            asset_relevance=RelevanceClassification.MARKET_WIDE,
            is_direct_asset=False,
            affected_assets=["BTCUSDT"],
            source_id="gdelt_gkg",
            source_reliability_score=0.5,
            first_observed_time="2024-06-15T12:00:00Z",
            collection_time="2024-06-15T12:00:01Z",
            availability_time="2024-06-15T12:00:00Z",
            classifier_version="v1.1.0-deterministic",
            classification_confidence=0.8,
            provenance_status=SourceVerificationStatus.PARTIALLY_VERIFIED,
            is_veto_eligible=True,
        )

        # Prohibited for 15m, 1h, 4h
        for tf in ["15m", "1h", "4h"]:
            valid, reason = contract.validate_invariants("2024-06-15T12:30:00Z", tf)
            assert valid is False
            assert reason == "GDELT_SUB_DAILY_INTRADAY_PROHIBITED"

        # Permitted for 1d (higher timeframe)
        valid_1d, reason_1d = contract.validate_invariants("2024-06-15T23:59:59Z", "1d")
        assert valid_1d is True
        assert reason_1d is None


class TestMilestone4630ChronologicalPartitions:
    """Verifies chronological dataset splits and cluster boundary isolation."""

    def test_split_manifest_boundary_integrity(self):
        manifest_path = os.path.join("storage", "exports", "milestone_4_6_3_0", "chronological_split_manifest.json")
        assert os.path.exists(manifest_path)

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        manifest = ChronologicalSplitManifest(**data)
        assert len(manifest.partitions) == 4

        dev = manifest.partitions[PartitionType.DEVELOPMENT_TRAINING.value]
        val = manifest.partitions[PartitionType.VALIDATION.value]
        oos = manifest.partitions[PartitionType.LOCKED_OUT_OF_SAMPLE.value]

        # Verify strict non-overlapping boundaries
        assert dev.start_timestamp == "2024-01-01T00:00:00Z"
        assert dev.end_timestamp == "2024-12-31T23:59:59Z"

        assert val.start_timestamp == "2025-01-01T00:00:00Z"
        assert val.end_timestamp == "2025-12-31T23:59:59Z"

        assert oos.start_timestamp == "2026-01-01T00:00:00Z"
        assert oos.end_timestamp == "2026-10-31T23:59:59Z"
        assert oos.is_locked is True

    def test_cluster_leakage_detector(self):
        manifest_path = os.path.join("storage", "exports", "milestone_4_6_3_0", "chronological_split_manifest.json")
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = ChronologicalSplitManifest(**json.load(f))

        # Test safe clusters (contained within single partition)
        safe_clusters = {
            "cluster_2024_01": ("2024-03-01T00:00:00Z", "2024-03-05T00:00:00Z"),
            "cluster_2025_01": ("2025-06-10T00:00:00Z", "2025-06-11T00:00:00Z"),
            "cluster_2026_01": ("2026-04-12T00:00:00Z", "2026-04-14T00:00:00Z"),
        }
        is_safe, violations = manifest.verify_no_cluster_leakage(safe_clusters)
        assert is_safe is True
        assert len(violations) == 0

        # Test leaking cluster (spanning 2024 and 2025)
        leaking_clusters = {
            "cluster_leaking": ("2024-12-30T10:00:00Z", "2025-01-02T10:00:00Z"),
        }
        is_safe_leak, violations_leak = manifest.verify_no_cluster_leakage(leaking_clusters)
        assert is_safe_leak is False
        assert len(violations_leak) == 1
        assert "cluster_leaking" in violations_leak[0]


class TestMilestone4630MatchingEngines:
    """Verifies deterministic frequency and exposure matching algorithms."""

    def test_frequency_matching_systematic_decimation(self):
        # 10 synthetic candidate signals
        candidates = [{"signal_id": f"sig_{i}", "timestamp": f"2024-01-0{i+1}T12:00:00Z"} for i in range(10)]

        # Target 5 trades
        selected_5 = FrequencyMatchingEngine.decimate_systematically(candidates, target_count=5)
        assert len(selected_5) == 5
        # Verify deterministic uniform distribution
        ids = [c["signal_id"] for c in selected_5]
        assert ids == ["sig_0", "sig_2", "sig_4", "sig_7", "sig_9"]

        # Target 1 trade
        selected_1 = FrequencyMatchingEngine.decimate_systematically(candidates, target_count=1)
        assert len(selected_1) == 1
        assert selected_1[0]["signal_id"] == "sig_0"

        # Target > total
        selected_all = FrequencyMatchingEngine.decimate_systematically(candidates, target_count=15)
        assert len(selected_all) == 10

    def test_frequency_matching_technical_confidence_priority(self):
        candidates = [
            {"signal_id": "sig_low", "raw_confidence": 0.40},
            {"signal_id": "sig_high_1", "raw_confidence": 0.85},
            {"signal_id": "sig_med", "raw_confidence": 0.60},
            {"signal_id": "sig_high_2", "raw_confidence": 0.90},
        ]
        # Target 2 trades
        selected = FrequencyMatchingEngine.prune_by_technical_confidence(candidates, target_count=2)
        assert len(selected) == 2
        selected_ids = {c["signal_id"] for c in selected}
        assert selected_ids == {"sig_high_1", "sig_high_2"}

    def test_frequency_matching_cryptographic_seed_reproducibility(self):
        candidates = [{"signal_id": f"sig_{i}", "timestamp": f"2024-01-0{i+1}T12:00:00Z"} for i in range(20)]

        # Identical runs with same seed must yield identical selections
        res_a = FrequencyMatchingEngine.select_by_cryptographic_seed(candidates, target_count=8, seed="test_seed_1")
        res_b = FrequencyMatchingEngine.select_by_cryptographic_seed(candidates, target_count=8, seed="test_seed_1")
        assert len(res_a) == 8
        assert [c["signal_id"] for c in res_a] == [c["signal_id"] for c in res_b]

        # Different seed yields different selection
        res_c = FrequencyMatchingEngine.select_by_cryptographic_seed(candidates, target_count=8, seed="test_seed_2")
        assert [c["signal_id"] for c in res_a] != [c["signal_id"] for c in res_c]

    def test_exposure_matching_engine_budget(self):
        candidates = [{"signal_id": f"sig_{i}", "timestamp": f"2024-01-0{i+1}T12:00:00Z"} for i in range(20)]
        # Target 60 bars exposure with 15 average holding bars -> ~4 trades
        matched = ExposureMatchingEngine.filter_by_cumulative_exposure_budget(
            candidates,
            target_total_bars_exposure=60,
            average_holding_bars=15,
        )
        assert len(matched) == 4


class TestMilestone4630StatisticalPlanAndFingerprint:
    """Verifies statistical analysis plan parameters and experiment reproducibility fingerprint."""

    def test_statistical_plan_defaults(self):
        plan = StatisticalAnalysisPlanConfig()
        assert plan.significance_level_alpha == 0.05
        assert plan.confidence_interval_level == 0.95
        assert plan.bootstrap_resample_iterations == 2000
        assert plan.block_bootstrap_size_bars == 48
        assert plan.multiple_testing_correction == "BENJAMINI_HOCHBERG_FDR"
        assert plan.false_discovery_rate_q == 0.05
        assert plan.economic_hurdle_net_expectancy_usdt == Decimal("0.50")
        assert plan.cost_threshold_round_trip_bps == Decimal("32.0")

    def test_master_reproducibility_fingerprint_integrity(self):
        fp_path = os.path.join("storage", "exports", "milestone_4_6_3_0", "reproducibility_fingerprint_specification.json")
        assert os.path.exists(fp_path)

        with open(fp_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        fp_obj = ExperimentReproducibilityFingerprint(**data)
        assert len(fp_obj.composite_experiment_fingerprint) == 64
        assert fp_obj.baseline_market_dataset_sha256 == "b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c"
        assert fp_obj.news_dataset_manifest_sha256 == "6b7bb69c841ec9a5e1774b6f369c0d9c113df066d80357521ac92b937490f4ec"
