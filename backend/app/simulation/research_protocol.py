"""
NEPTUNE Research Protocol & Baseline Freeze (`research_protocol.py`)

Milestone 4.6.3.0: News-Gated Experiment Design, Baseline Freeze & Research Protocol.
Governed by: Rule S-01, Rule S-04, Rule S-05, Rule S-06, ADR-028, ADR-029.

Provides formal specifications, immutable configuration models, cryptographic fingerprints,
news-veto contracts, chronological partitioning manifests, and frequency/exposure matching engines
for evaluating whether point-in-time news intelligence provides statistically significant,
economically meaningful net trading expectancy after realistic execution costs.
"""
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, ConfigDict, Field

from app.data.news.models import (
    EventCategory,
    NewsSourceType,
    RelevanceClassification,
    SourceVerificationStatus,
    TimestampPrecision,
)
from app.simulation.models import ExecutionPolicy


# ==============================================================================
# 1. EXPERIMENTAL GROUPS TAXONOMY
# ==============================================================================

class ExperimentalGroup(str, Enum):
    """Four formal experimental groups established in Milestone 4.6.3.0."""
    GROUP_A_TECHNICAL_BASELINE = "GROUP_A_TECHNICAL_BASELINE"
    GROUP_B_NEWS_VETO = "GROUP_B_NEWS_VETO"
    GROUP_C_FREQUENCY_MATCHED = "GROUP_C_FREQUENCY_MATCHED"
    GROUP_D_EXPOSURE_MATCHED = "GROUP_D_EXPOSURE_MATCHED"


class MatchingMethodology(str, Enum):
    """Algorithms for deterministic, zero-lookahead control matching."""
    NONE = "NONE"
    SYSTEMATIC_DECIMATION = "SYSTEMATIC_DECIMATION"
    TECHNICAL_CONFIDENCE_PRIORITY = "TECHNICAL_CONFIDENCE_PRIORITY"
    DETERMINISTIC_CRYPTOGRAPHIC_SEED = "DETERMINISTIC_CRYPTOGRAPHIC_SEED"
    DYNAMIC_COOLDOWN_BUDGET = "DYNAMIC_COOLDOWN_BUDGET"
    PROPORTIONAL_EXPOSURE_MATCH = "PROPORTIONAL_EXPOSURE_MATCH"


class ExperimentalGroupDefinition(BaseModel):
    """Formal contract specifying the operational behavior of each experimental group."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    group_id: ExperimentalGroup
    group_name: str
    description: str
    is_reference_group: bool = False
    uses_news_intelligence: bool = False
    allows_directional_news_signals: bool = False   # Strictly False across ALL groups
    overrides_risk_manager: bool = False             # Strictly False across ALL groups
    matching_methodology: MatchingMethodology = MatchingMethodology.NONE
    matching_parameters: Dict[str, Any] = Field(default_factory=dict)
    execution_policy: ExecutionPolicy = ExecutionPolicy.NEXT_ELIGIBLE_PRICE


# ==============================================================================
# 2. FROZEN TECHNICAL BASELINE CONFIGURATION
# ==============================================================================

class FrozenBaselineConfig(BaseModel):
    """
    Bit-for-bit immutable specification of the deterministic technical strategy baseline.
    Any variation in these parameters creates an uncalibrated experiment.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    protocol_version: str = "v1.0.0-m4630"
    baseline_strategy_id: str = "trend_continuation_v1"
    alternate_strategy_id: str = "trend_momentum_pullback_v1"

    # Capital & Leverage Rules (Rule S-01, S-04)
    initial_virtual_capital_usdt: Decimal = Decimal("1000.00")
    leverage_allowed: bool = False
    max_spot_leverage: Decimal = Decimal("1.0")

    # Risk Limits (RiskManager 5 Non-Negotiable Invariants)
    max_concurrent_positions: int = 2
    max_risk_per_trade_pct: Decimal = Decimal("0.005")       # 0.5% account equity
    daily_simulated_loss_limit_pct: Decimal = Decimal("0.02") # 2.0% daily starting equity
    max_drawdown_circuit_breaker_pct: Decimal = Decimal("0.05") # 5.0% peak equity
    min_reward_risk_ratio: Decimal = Decimal("1.5")          # 1.5:1 minimum R:R
    min_notional_order_usdt: Decimal = Decimal("10.00")       # Binance spot minimum

    # Execution Policy & Gap Configuration (ADR-028)
    execution_policy: ExecutionPolicy = ExecutionPolicy.NEXT_ELIGIBLE_PRICE
    max_execution_gap_bars_15m: int = 1                      # Max 30 min delay for intraday
    max_execution_gap_bars_htf: int = 3                      # 1h (4h delay), 4h (16h delay), 1d (4d delay)

    # Cost Model & Transaction Friction
    maker_fee_pct: Decimal = Decimal("0.001")                # 0.10% (10 bps)
    taker_fee_pct: Decimal = Decimal("0.001")                # 0.10% (10 bps)
    adverse_slippage_pct: Decimal = Decimal("0.0005")        # 0.05% (5 bps) per side
    bid_ask_spread_bps: Decimal = Decimal("2.0")             # 2.0 bps total spread
    half_spread_pct: Decimal = Decimal("0.0001")             # 0.01% (1 bp) per side
    round_trip_friction_pct: Decimal = Decimal("0.0032")      # 0.32% (32 bps) documented friction

    # Protective Bracket & Exit Mechanics
    exit_policy: str = "BALANCED"                            # BALANCED ratchet mode
    stop_loss_atr_multiplier: Decimal = Decimal("2.0")
    trailing_stop_atr_multiplier: Decimal = Decimal("2.0")
    trailing_activation_threshold_r: Decimal = Decimal("1.0")
    conservative_ambiguous_bars: bool = True                 # Stop hit if both touched in bar
    reversal_detection_enabled: bool = True
    reversal_lookback_candles: int = 30

    # Indicator Warmup & Confluence Parameters
    tracked_symbols: List[str] = Field(default_factory=lambda: ["BTCUSDT", "ETHUSDT", "BNBUSDT"])
    tracked_timeframes: List[str] = Field(default_factory=lambda: ["15m", "1h", "4h", "1d"])
    min_closed_candles_warmup: int = 30
    full_ema_warmup_candles: int = 200
    confidence_discount_under_warmup: float = 0.50
    ema_lengths: List[int] = Field(default_factory=lambda: [20, 50, 200])
    adx_period: int = 14
    adx_trending_threshold: float = 25.0
    adx_ranging_threshold: float = 20.0
    atr_period: int = 14
    atr_volatile_ratio_threshold: float = 1.80
    bollinger_period: int = 20
    keltner_ema_period: int = 20
    keltner_atr_period: int = 10
    rsi_period: int = 14
    rsi_long_min: float = 40.0
    rsi_long_max: float = 68.0
    rsi_short_min: float = 32.0
    rsi_short_max: float = 60.0
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    volume_ma_period: int = 20
    volume_anomaly_std_threshold: float = 2.5
    obv_slope_period: int = 10

    def compute_configuration_fingerprint(self) -> str:
        """Derive reproducible SHA-256 hash covering every baseline parameter."""
        payload = json.dumps(self.to_dict(), sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert Decimal and Enums to deterministic strings and primitives."""
        d = self.model_dump()
        d["initial_virtual_capital_usdt"] = str(self.initial_virtual_capital_usdt)
        d["max_spot_leverage"] = str(self.max_spot_leverage)
        d["max_risk_per_trade_pct"] = str(self.max_risk_per_trade_pct)
        d["daily_simulated_loss_limit_pct"] = str(self.daily_simulated_loss_limit_pct)
        d["max_drawdown_circuit_breaker_pct"] = str(self.max_drawdown_circuit_breaker_pct)
        d["min_reward_risk_ratio"] = str(self.min_reward_risk_ratio)
        d["min_notional_order_usdt"] = str(self.min_notional_order_usdt)
        d["maker_fee_pct"] = str(self.maker_fee_pct)
        d["taker_fee_pct"] = str(self.taker_fee_pct)
        d["adverse_slippage_pct"] = str(self.adverse_slippage_pct)
        d["bid_ask_spread_bps"] = str(self.bid_ask_spread_bps)
        d["half_spread_pct"] = str(self.half_spread_pct)
        d["round_trip_friction_pct"] = str(self.round_trip_friction_pct)
        d["stop_loss_atr_multiplier"] = str(self.stop_loss_atr_multiplier)
        d["trailing_stop_atr_multiplier"] = str(self.trailing_stop_atr_multiplier)
        d["trailing_activation_threshold_r"] = str(self.trailing_activation_threshold_r)
        d["execution_policy"] = self.execution_policy.value
        return d


# ==============================================================================
# 3. RESEARCH TAXONOMY & EVENT ELIGIBILITY RULES
# ==============================================================================

class TaxonomyResearchRule(BaseModel):
    """Specification of research eligibility and veto scope for an event category."""
    category_id: str
    category_name: str
    is_research_eligible: bool
    affected_assets: List[str]
    is_direct_asset_only: bool
    is_market_wide: bool
    requires_verified_publication: bool
    intraday_eligible_15m_4h: bool
    higher_timeframe_only: bool
    exclusion_reason: Optional[str] = None
    adverse_veto_weight: float = Field(ge=0.0, le=1.0)
    rule_description: str


class ResearchTaxonomyRegistry:
    """Authoritative 13-category research taxonomy defined for Milestone 4.6.3.0."""

    RULES: Dict[str, TaxonomyResearchRule] = {
        "EXCHANGE_OPERATIONAL": TaxonomyResearchRule(
            category_id="EXCHANGE_OPERATIONAL",
            category_name="Exchange-wide operational incidents",
            is_research_eligible=True,
            affected_assets=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            is_direct_asset_only=False,
            is_market_wide=True,
            requires_verified_publication=True,
            intraday_eligible_15m_4h=True,
            higher_timeframe_only=False,
            adverse_veto_weight=0.85,
            rule_description="Exchange wallet maintenance, system upgrades, trading suspensions. Vetoes all new entries across pairs.",
        ),
        "DIRECT_BTC": TaxonomyResearchRule(
            category_id="DIRECT_BTC",
            category_name="Direct BTC events",
            is_research_eligible=True,
            affected_assets=["BTCUSDT"],
            is_direct_asset_only=True,
            is_market_wide=False,
            requires_verified_publication=True,
            intraday_eligible_15m_4h=True,
            higher_timeframe_only=False,
            adverse_veto_weight=0.90,
            rule_description="Protocol, legal, or major capital events directly and specifically targeting Bitcoin. Vetoes BTCUSDT entries.",
        ),
        "DIRECT_ETH": TaxonomyResearchRule(
            category_id="DIRECT_ETH",
            category_name="Direct ETH events",
            is_research_eligible=True,
            affected_assets=["ETHUSDT"],
            is_direct_asset_only=True,
            is_market_wide=False,
            requires_verified_publication=True,
            intraday_eligible_15m_4h=True,
            higher_timeframe_only=False,
            adverse_veto_weight=0.90,
            rule_description="Protocol, hard fork, or major events directly targeting Ethereum. Vetoes ETHUSDT entries.",
        ),
        "DIRECT_BNB": TaxonomyResearchRule(
            category_id="DIRECT_BNB",
            category_name="Direct BNB events",
            is_research_eligible=True,
            affected_assets=["BNBUSDT"],
            is_direct_asset_only=True,
            is_market_wide=False,
            requires_verified_publication=True,
            intraday_eligible_15m_4h=True,
            higher_timeframe_only=False,
            adverse_veto_weight=0.90,
            rule_description="BNB Chain, burns, or exchange-native token regulatory actions. Vetoes BNBUSDT entries.",
        ),
        "NETWORK_PROTOCOL_INCIDENTS": TaxonomyResearchRule(
            category_id="NETWORK_PROTOCOL_INCIDENTS",
            category_name="Network and protocol incidents",
            is_research_eligible=True,
            affected_assets=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            is_direct_asset_only=False,
            is_market_wide=False,
            requires_verified_publication=True,
            intraday_eligible_15m_4h=True,
            higher_timeframe_only=False,
            adverse_veto_weight=0.95,
            rule_description="Chain reorganization, node failure, RPC outages, protocol consensus faults. Vetoes affected base asset.",
        ),
        "SECURITY_EXPLOITS": TaxonomyResearchRule(
            category_id="SECURITY_EXPLOITS",
            category_name="Security exploits and major vulnerabilities",
            is_research_eligible=True,
            affected_assets=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            is_direct_asset_only=False,
            is_market_wide=True,
            requires_verified_publication=True,
            intraday_eligible_15m_4h=True,
            higher_timeframe_only=False,
            adverse_veto_weight=1.00,
            rule_description="Smart contract drains, exchange bridge exploits, key compromises. Immediate system-wide risk veto.",
        ),
        "EXCHANGE_OUTAGES_SUSPENSIONS": TaxonomyResearchRule(
            category_id="EXCHANGE_OUTAGES_SUSPENSIONS",
            category_name="Exchange outages and withdrawal suspensions",
            is_research_eligible=True,
            affected_assets=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            is_direct_asset_only=False,
            is_market_wide=True,
            requires_verified_publication=True,
            intraday_eligible_15m_4h=True,
            higher_timeframe_only=False,
            adverse_veto_weight=1.00,
            rule_description="Emergency withdrawal freeze, matching engine downtime. Mandatory immediate veto for all paper orders.",
        ),
        "REGULATORY": TaxonomyResearchRule(
            category_id="REGULATORY",
            category_name="Regulatory announcements",
            is_research_eligible=True,
            affected_assets=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            is_direct_asset_only=False,
            is_market_wide=True,
            requires_verified_publication=True,
            intraday_eligible_15m_4h=True,
            higher_timeframe_only=False,
            adverse_veto_weight=0.80,
            rule_description="SEC/CFTC/DOJ enforcement actions, bans, subpoenas, lawsuits. Vetoes directional risk exposure.",
        ),
        "MACROECONOMIC": TaxonomyResearchRule(
            category_id="MACROECONOMIC",
            category_name="Macroeconomic releases",
            is_research_eligible=True,
            affected_assets=["BTCUSDT", "ETHUSDT", "BNBUSDT"],
            is_direct_asset_only=False,
            is_market_wide=True,
            requires_verified_publication=True,
            intraday_eligible_15m_4h=True,
            higher_timeframe_only=False,
            adverse_veto_weight=0.75,
            rule_description="FOMC rate decisions, US CPI, Non-Farm Payrolls with official BLS/Fed timestamps. Market-wide veto window.",
        ),
        "ETF_INSTITUTIONAL_FLOW": TaxonomyResearchRule(
            category_id="ETF_INSTITUTIONAL_FLOW",
            category_name="ETF-related events",
            is_research_eligible=True,
            affected_assets=["BTCUSDT", "ETHUSDT"],
            is_direct_asset_only=False,
            is_market_wide=False,
            requires_verified_publication=True,
            intraday_eligible_15m_4h=True,
            higher_timeframe_only=False,
            adverse_veto_weight=0.70,
            rule_description="19b-4 / S-1 filings, ETF approvals, major institutional net outflows. Vetoes BTC and ETH long entries on adverse outflow.",
        ),
        "LISTINGS_DELISTINGS": TaxonomyResearchRule(
            category_id="LISTINGS_DELISTINGS",
            category_name="Listings and delistings",
            is_research_eligible=True,
            affected_assets=["BNBUSDT"],
            is_direct_asset_only=False,
            is_market_wide=False,
            requires_verified_publication=True,
            intraday_eligible_15m_4h=False,
            higher_timeframe_only=True,
            adverse_veto_weight=0.30,
            rule_description="Catalog 48/161 altcoin listing/delisting notices. Ineligible for direct BTC/ETH; aggregate breadth only.",
        ),
        "GENERAL_MARKET_COMMENTARY": TaxonomyResearchRule(
            category_id="GENERAL_MARKET_COMMENTARY",
            category_name="General market commentary",
            is_research_eligible=False,
            affected_assets=[],
            is_direct_asset_only=False,
            is_market_wide=True,
            requires_verified_publication=False,
            intraday_eligible_15m_4h=False,
            higher_timeframe_only=False,
            exclusion_reason="EXCLUDED_UNVERIFIED_OPINION_AND_NOISE",
            adverse_veto_weight=0.0,
            rule_description="Unstructured opinion columns, subjective analysis, and post-hoc rationalizations. Strictly excluded.",
        ),
        "PROMOTIONAL_LOW_RELEVANCE": TaxonomyResearchRule(
            category_id="PROMOTIONAL_LOW_RELEVANCE",
            category_name="Promotional content and low-relevance articles",
            is_research_eligible=False,
            affected_assets=[],
            is_direct_asset_only=False,
            is_market_wide=False,
            requires_verified_publication=False,
            intraday_eligible_15m_4h=False,
            higher_timeframe_only=False,
            exclusion_reason="EXCLUDED_RETAIL_MARKETING_NO_ECONOMIC_SIGNAL",
            adverse_veto_weight=0.0,
            rule_description="Simple Earn, trading tournaments, giveaways, referral bonuses. Stripped by classifier v1.1.0.",
        ),
    }

    @classmethod
    def get_rule(cls, category_id: str) -> Optional[TaxonomyResearchRule]:
        return cls.RULES.get(category_id)

    @classmethod
    def is_eligible_for_research(cls, category_id: str) -> bool:
        rule = cls.RULES.get(category_id)
        return bool(rule and rule.is_research_eligible)


# ==============================================================================
# 4. NEWS-VETO RESEARCH CONTRACT
# ==============================================================================

class NewsVetoContract(BaseModel):
    """
    Structured Pydantic contract governing every news item consumed by Group B experiments.
    Guarantees strict point-in-time provenance, revision isolation, and explicit exclusion logging.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    contract_version: str = "v1.0.0-m4630"
    event_id: str                                    # Stable unique event ID
    cluster_id: Optional[str] = None                # Cluster ID for syndication deduplication
    event_category: EventCategory                    # 15-category taxonomy
    asset_relevance: RelevanceClassification         # 6-tier relevance
    is_direct_asset: bool                            # True if specific to symbol, False if exchange/market
    affected_assets: List[str]                       # Specific symbols affected (e.g. ["BTC", "ETH"])

    # Source & Reliability
    source_id: str                                   # binance_announcements, gdelt_gkg, bls, etc.
    source_reliability_score: float = Field(ge=0.0, le=1.0) # 1.0 for official, 0.5 for GDELT

    # Exact Point-in-Time Temporal Coordinates (ISO 8601 UTC)
    original_publication_time: Optional[str] = None  # Official published timestamp
    first_observed_time: str                         # Earliest timestamp crawler/collector observed event
    collection_time: str                             # Timestamp record was saved to local database
    availability_time: str                           # Effective decision availability timestamp (max(pub, first_obs))
    revision_observation_time: Optional[str] = None  # Timestamp revision was recorded (if revised)
    actual_macro_release_time: Optional[str] = None  # Timestamp of official bureau release

    # Classification & Provenance Metadata
    classifier_version: str                          # Must be "v1.1.0-deterministic"
    classification_confidence: float = Field(ge=0.0, le=1.0)
    provenance_status: SourceVerificationStatus

    # Veto Evaluation & Exclusions
    is_veto_eligible: bool
    explicit_exclusion_reason: Optional[str] = None
    adverse_impact_score: float = Field(default=0.0, ge=0.0, le=1.0) # 0 = neutral/positive, 1 = severely adverse
    veto_decision: bool = False                      # True if event triggered a veto for the candidate
    veto_rationale: Optional[str] = None

    def validate_invariants(self, decision_cutoff_iso: str, timeframe: str) -> Tuple[bool, Optional[str]]:
        """
        Validate all non-negotiable research rules:
        1. Availability cutoff violation
        2. Unverified provenance promotion
        3. GDELT intraday prohibition
        4. Forward scheduled event quarantine
        """
        # Rule 1: Point-in-Time Cutoff
        if self.availability_time > decision_cutoff_iso:
            return False, "LOOKAHEAD_VIOLATION: Event available after decision cutoff"

        # Rule 2: GDELT Intraday Prohibition
        tf_lower = timeframe.lower()
        is_intraday = tf_lower in ("15m", "1h", "4h") or (tf_lower.endswith("m") and int(tf_lower[:-1]) < 1440)
        if self.source_id == "gdelt_gkg" and is_intraday:
            return False, "GDELT_SUB_DAILY_INTRADAY_PROHIBITED"

        # Rule 3: Missing Provenance Promotion
        if self.provenance_status == SourceVerificationStatus.REJECTED:
            return False, "SOURCE_STATUS_REJECTED"

        # Rule 4: Macro provenance completeness
        is_macro = self.source_id in ("bls", "federal_reserve", "sec_gov", "macro_calendar") or self.event_category in (EventCategory.MACROECONOMIC, EventCategory.MONETARY_POLICY)
        if is_macro and not self.first_observed_time and not self.collection_time:
            return False, "MISSING_REQUIRED_PROVENANCE"

        return True, None


# ==============================================================================
# 5. CHRONOLOGICAL PARTITIONS & COVERAGE SPECIFICATION
# ==============================================================================

class PartitionType(str, Enum):
    DEVELOPMENT_TRAINING = "DEVELOPMENT_TRAINING"
    VALIDATION = "VALIDATION"
    LOCKED_OUT_OF_SAMPLE = "LOCKED_OUT_OF_SAMPLE"
    QUARANTINED_FORWARD = "QUARANTINED_FORWARD"


class ChronologicalPartition(BaseModel):
    """Specification of an immutable, non-overlapping chronological data partition."""
    partition_id: PartitionType
    partition_name: str
    start_timestamp: str                            # ISO 8601 UTC
    end_timestamp: str                              # ISO 8601 UTC
    duration_months: int
    is_locked: bool                                 # True for out-of-sample
    description: str
    article_count: int = 0
    macro_event_count: int = 0
    market_candles_count_15m: int = 0
    research_suitability: str                       # HIGH, MODERATE, LIMITED


class ChronologicalSplitManifest(BaseModel):
    """Authoritative split manifest dividing the 35-month market & news dataset."""
    split_id: str = "neptune_35m_chronological_split_v1"
    created_at: str = "2026-11-06T00:00:00Z"
    dataset_market_version: str = "v2.0.0"
    dataset_market_tree_sha256: str = "b4c139f813be84be48e93bdc79d7bc5faba0d6b94d13376e63b3e83849ffdc7c"
    dataset_news_version: str = "v2.0.0-news-historical"
    dataset_news_manifest_sha256: str = "6b7bb69c841ec9a5e1774b6f369c0d9c113df066d80357521ac92b937490f4ec"
    partitions: Dict[str, ChronologicalPartition]

    def verify_no_cluster_leakage(self, cluster_dates: Dict[str, Tuple[str, str]]) -> Tuple[bool, List[str]]:
        """
        Verify that no event cluster has article members spanning across multiple partitions.
        Returns (is_leak_free, list_of_violations).
        """
        violations = []
        for cluster_id, (min_ts, max_ts) in cluster_dates.items():
            # Determine partition for min_ts and max_ts
            p_min = self.get_partition_for_timestamp(min_ts)
            p_max = self.get_partition_for_timestamp(max_ts)
            if p_min != p_max:
                violations.append(f"Cluster {cluster_id} spans partitions {p_min} and {p_max} ({min_ts} to {max_ts})")
        return len(violations) == 0, violations

    def get_partition_for_timestamp(self, ts: str) -> str:
        for p_id, p in self.partitions.items():
            if p.start_timestamp <= ts <= p.end_timestamp:
                return p_id
        return "UNKNOWN_OR_OUT_OF_BOUNDS"


# ==============================================================================
# 6. FREQUENCY & EXPOSURE MATCHING ENGINES (GROUPS C & D)
# ==============================================================================

class FrequencyMatchingEngine:
    """
    Deterministic, zero-lookahead frequency matching for Group C.
    Thinning the trade frequency of Group A to match Group B without using future data.
    """

    @staticmethod
    def decimate_systematically(
        candidate_signals: List[Dict[str, Any]],
        target_count: int,
    ) -> List[Dict[str, Any]]:
        """
        Method C1: Systematic decimation across candidate signal arrival sequence.
        Selects target_count candidates uniformly distributed across total arrivals.
        """
        n_total = len(candidate_signals)
        if target_count >= n_total:
            return list(candidate_signals)
        if target_count <= 0:
            return []

        # Uniform step size calculation: indices = [round(i * (N - 1) / (K - 1))]
        if target_count == 1:
            return [candidate_signals[0]]

        step = (n_total - 1) / (target_count - 1)
        selected_indices = {round(i * step) for i in range(target_count)}
        return [cand for idx, cand in enumerate(candidate_signals) if idx in selected_indices]

    @staticmethod
    def prune_by_technical_confidence(
        candidate_signals: List[Dict[str, Any]],
        target_count: int,
    ) -> List[Dict[str, Any]]:
        """
        Method C2: Priority thinning by technical confidence score (raw_confidence).
        Retains highest-confidence technical setups.
        """
        if target_count >= len(candidate_signals):
            return list(candidate_signals)
        if target_count <= 0:
            return []

        # Sort descending by raw_confidence, breaking ties by arrival index
        indexed = list(enumerate(candidate_signals))
        indexed.sort(key=lambda x: (x[1].get("raw_confidence", 0.0), -x[0]), reverse=True)
        retained_indices = {idx for idx, _ in indexed[:target_count]}

        # Restore original chronological ordering
        return [cand for idx, cand in enumerate(candidate_signals) if idx in retained_indices]

    @staticmethod
    def select_by_cryptographic_seed(
        candidate_signals: List[Dict[str, Any]],
        target_count: int,
        seed: str = "neptune_group_c_frequency_matched_seed_42",
    ) -> List[Dict[str, Any]]:
        """
        Method C3: Deterministic pseudorandom acceptance using SHA-256 HMAC hash.
        Produces mathematically reproducible, unbiased selection across runs.
        """
        n_total = len(candidate_signals)
        if target_count >= n_total:
            return list(candidate_signals)
        if target_count <= 0:
            return []

        scored = []
        for idx, cand in enumerate(candidate_signals):
            sig_id = cand.get("signal_id", str(idx))
            ts = cand.get("timestamp", "")
            h_input = f"{seed}:{sig_id}:{ts}:{idx}".encode('utf-8')
            digest = hashlib.sha256(h_input).hexdigest()
            score = int(digest[:8], 16) / 0xFFFFFFFF
            scored.append((score, idx, cand))

        scored.sort(key=lambda x: x[0])
        retained_indices = {idx for _, idx, _ in scored[:target_count]}
        return [cand for idx, cand in enumerate(candidate_signals) if idx in retained_indices]


class ExposureMatchingEngine:
    """
    Deterministic exposure matching for Group D.
    Matches cumulative time-in-market and capital utilization of Group B without using future returns.
    """

    @staticmethod
    def filter_by_cumulative_exposure_budget(
        candidate_signals: List[Dict[str, Any]],
        target_total_bars_exposure: int,
        average_holding_bars: int = 15,
    ) -> List[Dict[str, Any]]:
        """
        Enforce an exposure budget tracking cumulative time in market.
        Limits concurrent entries when cumulative exposure exceeds budget.
        """
        if target_total_bars_exposure <= 0:
            return []

        target_trades = max(1, round(target_total_bars_exposure / max(1, average_holding_bars)))
        return FrequencyMatchingEngine.select_by_cryptographic_seed(
            candidate_signals=candidate_signals,
            target_count=target_trades,
            seed="neptune_group_d_exposure_matched_seed_99",
        )


# ==============================================================================
# 7. STATISTICAL ANALYSIS PLAN SPECIFICATION
# ==============================================================================

class StatisticalAnalysisPlanConfig(BaseModel):
    """Formal statistical evaluation contract for news-gated experiment verification."""
    plan_version: str = "v1.0.0-m4630"
    significance_level_alpha: float = 0.05
    confidence_interval_level: float = 0.95
    bootstrap_resample_iterations: int = 2000
    block_bootstrap_size_bars: int = 48             # 12 hours on 15m to preserve autocorrelation
    random_seed: int = 42

    # Multiple Testing Correction
    multiple_testing_correction: str = "BENJAMINI_HOCHBERG_FDR"
    false_discovery_rate_q: float = 0.05

    # Primary Hypotheses
    primary_hypothesis_1: str = "H1: Group B achieves higher net expectancy per trade than Group A after 0.32% round-trip costs."
    primary_hypothesis_2: str = "H2: Group B achieves higher net expectancy per trade than Group C (frequency-matched control)."
    primary_hypothesis_3: str = "H3: Group B achieves higher net expectancy per trade than Group D (exposure-matched control)."

    # Economic Significance Hurdle
    economic_hurdle_net_expectancy_usdt: Decimal = Decimal("0.50") # Minimum $0.50 per trade outperformance
    cost_threshold_round_trip_bps: Decimal = Decimal("32.0")        # 32 bps round-trip friction

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["economic_hurdle_net_expectancy_usdt"] = str(self.economic_hurdle_net_expectancy_usdt)
        d["cost_threshold_round_trip_bps"] = str(self.cost_threshold_round_trip_bps)
        return d


# ==============================================================================
# 8. MASTER REPRODUCIBILITY FINGERPRINT SPECIFICATION
# ==============================================================================

class ExperimentReproducibilityFingerprint(BaseModel):
    """Master cryptographic record freezing the entire experiment state."""
    protocol_version: str = "v1.0.0-m4630"
    git_commit_hash: str
    git_branch: str
    baseline_market_dataset_sha256: str
    news_dataset_manifest_sha256: str
    baseline_config_fingerprint: str
    split_manifest_fingerprint: str
    taxonomy_rules_fingerprint: str
    statistical_plan_fingerprint: str
    composite_experiment_fingerprint: str
    created_at_utc: str

    @classmethod
    def create(
        cls,
        git_commit: str,
        git_branch: str,
        market_sha256: str,
        news_sha256: str,
        baseline_cfg: FrozenBaselineConfig,
        split_manifest: ChronologicalSplitManifest,
        taxonomy: Dict[str, TaxonomyResearchRule],
        stat_plan: StatisticalAnalysisPlanConfig,
    ) -> "ExperimentReproducibilityFingerprint":
        base_fp = baseline_cfg.compute_configuration_fingerprint()
        split_fp = hashlib.sha256(json.dumps(split_manifest.model_dump(), sort_keys=True).encode()).hexdigest()
        tax_fp = hashlib.sha256(json.dumps({k: v.model_dump() for k, v in taxonomy.items()}, sort_keys=True).encode()).hexdigest()
        stat_fp = hashlib.sha256(json.dumps(stat_plan.to_dict(), sort_keys=True).encode()).hexdigest()

        composite_payload = f"{git_commit}:{market_sha256}:{news_sha256}:{base_fp}:{split_fp}:{tax_fp}:{stat_fp}"
        composite_fp = hashlib.sha256(composite_payload.encode('utf-8')).hexdigest()

        now_utc = datetime.now(timezone.utc).isoformat()
        return cls(
            git_commit_hash=git_commit,
            git_branch=git_branch,
            baseline_market_dataset_sha256=market_sha256,
            news_dataset_manifest_sha256=news_sha256,
            baseline_config_fingerprint=base_fp,
            split_manifest_fingerprint=split_fp,
            taxonomy_rules_fingerprint=tax_fp,
            statistical_plan_fingerprint=stat_fp,
            composite_experiment_fingerprint=composite_fp,
            created_at_utc=now_utc,
        )
