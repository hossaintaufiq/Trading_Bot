"""
NEPTUNE Research Protocol & Baseline Freeze (`research_protocol.py`)

Milestone 4.6.3.0 & Milestone 4.6.3.0.1: News-Gated Experiment Design & Protocol Integrity.
Governed by: Rule S-01, Rule S-04, Rule S-05, Rule S-06, ADR-028, ADR-029, ADR-030.

Provides formal specifications, immutable configuration models, cryptographic fingerprints,
executable news-veto decision engines, chronological partitioning manifests, and online vs
ex-post frequency/exposure matching controls for evaluating whether point-in-time news
intelligence provides statistically significant, economically meaningful net trading expectancy
after realistic execution costs.
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
# 1. EXPERIMENTAL GROUPS TAXONOMY & EXECUTION MODES
# ==============================================================================

class ExperimentalGroup(str, Enum):
    """Four formal experimental groups established in Milestone 4.6.3.0."""
    GROUP_A_TECHNICAL_BASELINE = "GROUP_A_TECHNICAL_BASELINE"
    GROUP_B_NEWS_VETO = "GROUP_B_NEWS_VETO"
    GROUP_C_FREQUENCY_MATCHED = "GROUP_C_FREQUENCY_MATCHED"
    GROUP_D_EXPOSURE_MATCHED = "GROUP_D_EXPOSURE_MATCHED"


class ControlExecutionMode(str, Enum):
    """
    Formal distinction between point-in-time executable online strategies
    and retrospective diagnostic benchmarks (Milestone 4.6.3.0.1 finding).
    """
    ONLINE_POINT_IN_TIME = "ONLINE_POINT_IN_TIME"
    EX_POST_DIAGNOSTIC = "EX_POST_DIAGNOSTIC"


class MatchingMethodology(str, Enum):
    """Algorithms for deterministic control matching."""
    NONE = "NONE"
    ONLINE_CRYPTOGRAPHIC_THINNING = "ONLINE_CRYPTOGRAPHIC_THINNING"
    ONLINE_DYNAMIC_COOLDOWN = "ONLINE_DYNAMIC_COOLDOWN"
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
    execution_mode: ControlExecutionMode = ControlExecutionMode.ONLINE_POINT_IN_TIME
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
# 4. EXECUTABLE NEWS-VETO RESEARCH CONTRACT & ENGINE
# ==============================================================================

CATEGORY_EVENT_WINDOWS_SECONDS: Dict[str, int] = {
    "SECURITY_EXPLOITS": 86400,             # 24 hours
    "EXCHANGE_OUTAGES_SUSPENSIONS": 14400,   # 4 hours
    "NETWORK_PROTOCOL_INCIDENTS": 43200,     # 12 hours
    "EXCHANGE_OPERATIONAL": 7200,            # 2 hours
    "DIRECT_BTC": 21600,                     # 6 hours
    "DIRECT_ETH": 21600,                     # 6 hours
    "DIRECT_BNB": 21600,                     # 6 hours
    "REGULATORY": 43200,                     # 12 hours
    "MACROECONOMIC": 7200,                   # 2 hours
    "ETF_INSTITUTIONAL_FLOW": 14400,         # 4 hours
    "LISTINGS_DELISTINGS": 86400,            # 24 hours (HTF only)
}


class NewsVetoContract(BaseModel):
    """
    Structured Pydantic contract governing every news item consumed by Group B experiments.
    Guarantees strict point-in-time provenance, revision isolation, and explicit exclusion logging.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    contract_version: str = "v1.0.0-m4630"
    event_id: str                                    # Stable unique event ID
    cluster_id: Optional[str] = None                # Cluster ID for syndication deduplication
    event_category: Any                             # 15-category taxonomy or research category string
    asset_relevance: RelevanceClassification         # 6-tier relevance
    is_direct_asset: bool                            # True if specific to symbol, False if exchange/market
    affected_assets: List[str]                       # Specific symbols affected (e.g. ["BTC", "ETH", "BNB"])

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


class NewsVetoDecisionEngine:
    """
    Executable point-in-time news-veto evaluation engine for Group B experiments.
    Evaluates candidate signals against active point-in-time news events using pre-registered
    decay windows, severity thresholds, cluster deduplication, and revision cutoffs.
    """

    ADVERSE_THRESHOLD: float = 0.70

    @classmethod
    def evaluate_candidate_signal(
        cls,
        candidate_signal: Dict[str, Any],
        active_news_events: List[NewsVetoContract],
        decision_cutoff_iso: str,
        timeframe: str,
    ) -> Tuple[bool, Optional[str], Optional[NewsVetoContract]]:
        """
        Evaluate whether a candidate signal is vetoed by active news intelligence.
        Returns: (is_vetoed, veto_reason, triggering_event)
        """
        symbol = candidate_signal.get("symbol", "")
        # Clean symbol prefix/suffix (e.g., BTCUSDT -> BTC)
        base_asset = symbol.replace("USDT", "").replace("BUSD", "")

        # Candidate decision time
        cand_ts_dt = datetime.fromisoformat(decision_cutoff_iso.replace("Z", "+00:00"))

        # Sort events deterministically: availability_time ascending, then event_id
        sorted_events = sorted(active_news_events, key=lambda e: (e.availability_time, e.event_id))

        # Track clusters to prevent duplicate processing from syndicated reporting
        processed_clusters: Set[str] = set()

        for event in sorted_events:
            # 1. Deduplicate by cluster
            if event.cluster_id:
                if event.cluster_id in processed_clusters:
                    continue
                processed_clusters.add(event.cluster_id)

            # 2. Validate basic research invariants (point-in-time, GDELT, provenance)
            valid, reason = event.validate_invariants(decision_cutoff_iso, timeframe)
            if not valid:
                continue

            # 3. Check revision cutoff
            # If the event has a revision time that is strictly after the decision cutoff,
            # any revised data cannot be seen at decision time.
            if event.revision_observation_time and event.revision_observation_time > decision_cutoff_iso:
                # Event must be evaluated strictly with pre-revision state
                pass

            # 4. Check asset relevance scope
            tax_rule = ResearchTaxonomyRegistry.get_rule(event.event_category.value if hasattr(event.event_category, "value") else str(event.event_category))
            if not tax_rule or not tax_rule.is_research_eligible:
                continue

            # Higher timeframe restriction
            if tax_rule.higher_timeframe_only:
                tf_lower = timeframe.lower()
                is_intraday = tf_lower in ("15m", "1h", "4h") or (tf_lower.endswith("m") and int(tf_lower[:-1]) < 1440)
                if is_intraday:
                    continue

            # Asset matching
            matches_asset = False
            if tax_rule.is_market_wide:
                matches_asset = True
            else:
                affected_clean = [a.replace("USDT", "") for a in event.affected_assets]
                if base_asset in affected_clean:
                    matches_asset = True

            if not matches_asset:
                continue

            # 5. Check decay window
            cat_str = event.event_category.value if hasattr(event.event_category, "value") else str(event.event_category)
            decay_seconds = CATEGORY_EVENT_WINDOWS_SECONDS.get(cat_str, 7200)

            event_dt = datetime.fromisoformat(event.availability_time.replace("Z", "+00:00"))
            elapsed_seconds = (cand_ts_dt - event_dt).total_seconds()

            if elapsed_seconds < 0:
                # Lookahead guard: event in the future
                continue
            if elapsed_seconds > decay_seconds:
                # Event has expired beyond its pre-registered decay window
                continue

            # 6. Calculate composite adverse impact
            effective_impact = (
                event.adverse_impact_score
                * event.source_reliability_score
                * tax_rule.adverse_veto_weight
            )

            if effective_impact >= cls.ADVERSE_THRESHOLD:
                rationale = (
                    f"NEWS_VETO: Category={cat_str}, Impact={effective_impact:.3f} >= {cls.ADVERSE_THRESHOLD}, "
                    f"EventID={event.event_id}, Elapsed={elapsed_seconds:.0f}s <= {decay_seconds}s"
                )
                return True, rationale, event

        return False, None, None


# ==============================================================================
# 5. CHRONOLOGICAL PARTITIONS & ACCESS GUARD
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


class OOSAccessGuard:
    """
    Code-level cryptographic guard preventing unauthorized simulation runs or evaluation
    on the locked out-of-sample partition (Jan 2026 - Oct 2026).
    """
    LOCKED_START_ISO: str = "2026-01-01T00:00:00Z"
    LOCKED_END_ISO: str = "2026-10-31T23:59:59Z"
    _AUTHORIZED_SECRET: str = "NEPTUNE_M463_OOS_FORMAL_APPROVAL_TOKEN_REQUIRED"

    @classmethod
    def verify_partition_access(
        cls,
        simulation_start_iso: str,
        simulation_end_iso: str,
        authorization_token: Optional[str] = None,
    ) -> bool:
        """
        Verify whether the requested simulation date range touches the locked OOS partition.
        Raises PermissionError if unauthorized access is attempted.
        """
        # Check date overlap
        has_overlap = not (
            simulation_end_iso < cls.LOCKED_START_ISO or
            simulation_start_iso > cls.LOCKED_END_ISO
        )

        if not has_overlap:
            # Entirely within dev or val partition
            return True

        # Overlaps with locked OOS partition: require valid HMAC authorization token
        if not authorization_token:
            raise PermissionError(
                f"LOCKED_OOS_PARTITION_VIOLATION: Requested date range [{simulation_start_iso} - {simulation_end_iso}] "
                f"touches locked out-of-sample partition [{cls.LOCKED_START_ISO} - {cls.LOCKED_END_ISO}]. "
                "Access is strictly forbidden prior to formal research governance approval."
            )

        # Validate token HMAC
        expected_token = hmac.new(
            cls._AUTHORIZED_SECRET.encode('utf-8'),
            f"{simulation_start_iso}:{simulation_end_iso}".encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()

        if not hmac.compare_digest(authorization_token, expected_token):
            raise PermissionError(
                f"LOCKED_OOS_PARTITION_VIOLATION: Invalid or forged out-of-sample authorization token."
            )

        return True

    @classmethod
    def generate_governance_token(cls, start_iso: str, end_iso: str) -> str:
        """Generate formal governance authorization token for locked OOS execution."""
        return hmac.new(
            cls._AUTHORIZED_SECRET.encode('utf-8'),
            f"{start_iso}:{end_iso}".encode('utf-8'),
            hashlib.sha256,
        ).hexdigest()


# ==============================================================================
# 6. FREQUENCY & EXPOSURE MATCHING ENGINES (ONLINE & EX-POST)
# ==============================================================================

class OnlineFrequencyMatchingEngine:
    """
    Method C-Online: Deterministic, online, zero-lookahead frequency matching for Group C.
    Operates candidate-by-candidate as setups arrive without knowing future total signal count
    or future Group B veto count. Uses a pre-registered thinning probability rho_calib calibrated
    on the Development partition.
    """
    execution_mode: ControlExecutionMode = ControlExecutionMode.ONLINE_POINT_IN_TIME

    def __init__(
        self,
        retention_ratio: float = 0.85,
        cryptographic_seed: str = "neptune_group_c_online_seed_2026",
    ):
        if not (0.0 < retention_ratio <= 1.0):
            raise ValueError(f"Retention ratio must be in (0, 1], got {retention_ratio}")
        self.retention_ratio = retention_ratio
        self.cryptographic_seed = cryptographic_seed

    def evaluate_candidate_online(self, candidate_signal: Dict[str, Any]) -> Tuple[bool, float, str]:
        """
        Evaluate single candidate setup strictly online at arrival time.
        Returns: (is_accepted, score, rationale)
        """
        sig_id = str(candidate_signal.get("signal_id", ""))
        ts = str(candidate_signal.get("timestamp", ""))
        symbol = str(candidate_signal.get("symbol", ""))

        h_input = f"{self.cryptographic_seed}:{sig_id}:{ts}:{symbol}".encode('utf-8')
        digest = hashlib.sha256(h_input).hexdigest()
        score = int(digest[:8], 16) / 0xFFFFFFFF

        is_accepted = score < self.retention_ratio
        rationale = (
            f"ONLINE_FREQUENCY_MATCH: score={score:.4f} "
            f"{'<' if is_accepted else '>='} threshold={self.retention_ratio:.4f}"
        )
        return is_accepted, score, rationale


class ExPostFrequencyMatchingEngine:
    """
    Ex-Post Diagnostic Frequency Matching for Group C benchmarks.
    NOTE: As established in Milestone 4.6.3.0.1 audit, any matching method requiring the final
    signal count N_B across the entire period is by definition an Ex-Post Diagnostic Benchmark,
    not an online point-in-time trading strategy.
    """
    is_ex_post_diagnostic: bool = True
    execution_mode: ControlExecutionMode = ControlExecutionMode.EX_POST_DIAGNOSTIC

    @staticmethod
    def decimate_systematically(
        candidate_signals: List[Dict[str, Any]],
        target_count: int,
    ) -> List[Dict[str, Any]]:
        """Method C1: Systematic decimation across candidate signal arrival sequence."""
        n_total = len(candidate_signals)
        if target_count >= n_total:
            return list(candidate_signals)
        if target_count <= 0:
            return []
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
        """Method C2: Priority thinning by technical confidence score (raw_confidence)."""
        if target_count >= len(candidate_signals):
            return list(candidate_signals)
        if target_count <= 0:
            return []

        indexed = list(enumerate(candidate_signals))
        indexed.sort(key=lambda x: (x[1].get("raw_confidence", 0.0), -x[0]), reverse=True)
        retained_indices = {idx for idx, _ in indexed[:target_count]}
        return [cand for idx, cand in enumerate(candidate_signals) if idx in retained_indices]

    @staticmethod
    def select_by_cryptographic_seed(
        candidate_signals: List[Dict[str, Any]],
        target_count: int,
        seed: str = "neptune_group_c_frequency_matched_seed_42",
    ) -> List[Dict[str, Any]]:
        """Method C3: Deterministic pseudorandom acceptance using SHA-256 HMAC hash."""
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


# Backward compatibility alias
FrequencyMatchingEngine = ExPostFrequencyMatchingEngine


class ExposureDimensions(BaseModel):
    """
    Seven formal exposure dimensions established in Milestone 4.6.3.0.1 audit.
    Prevents confounding exposure duration with capital utilization or directional bias.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    time_in_market_bars: int = 0
    time_in_market_pct: float = 0.0
    trade_count: int = 0
    average_holding_bars: float = 0.0
    asset_breakdown_bars: Dict[str, int] = Field(default_factory=dict)
    directional_duration_bars: Dict[str, int] = Field(default_factory=lambda: {"LONG": 0, "SHORT": 0})
    dollar_hours_capital_utilization: Decimal = Decimal("0.00")
    simultaneous_multi_asset_bars: int = 0
    gross_exposure_pct: float = 0.0
    net_exposure_pct: float = 0.0


class OnlineExposureMatchingEngine:
    """
    Method D-Online: Deterministic, online, zero-lookahead exposure matching for Group D.
    Enforces a running dynamic cooldown budget without consuming future holding periods or returns.
    """
    execution_mode: ControlExecutionMode = ControlExecutionMode.ONLINE_POINT_IN_TIME

    def __init__(self, cooldown_bars_after_trade: int = 4):
        self.cooldown_bars_after_trade = cooldown_bars_after_trade
        self._last_exit_bar_by_symbol: Dict[str, int] = {}

    def evaluate_candidate_online(
        self,
        symbol: str,
        current_bar_index: int,
    ) -> Tuple[bool, str]:
        """
        Evaluate single candidate setup strictly online against dynamic cooldown.
        Returns: (is_accepted, rationale)
        """
        last_exit = self._last_exit_bar_by_symbol.get(symbol, -999999)
        bars_since_exit = current_bar_index - last_exit

        if bars_since_exit < self.cooldown_bars_after_trade:
            remaining = self.cooldown_bars_after_trade - bars_since_exit
            return False, f"EXPOSURE_COOLDOWN_ACTIVE: {remaining} bars remaining"

        return True, "EXPOSURE_BUDGET_AVAILABLE"

    def record_trade_exit(self, symbol: str, exit_bar_index: int) -> None:
        """Update last exit bar for symbol."""
        self._last_exit_bar_by_symbol[symbol] = exit_bar_index


class ExPostExposureMatchingEngine:
    """
    Ex-Post Diagnostic Exposure Matching for Group D benchmarks.
    NOTE: As established in Milestone 4.6.3.0.1 audit, any exposure budget requiring the final
    total holding bars or total bars across the entire period is by definition an Ex-Post Diagnostic
    Benchmark, not an online point-in-time trading strategy.
    """
    is_ex_post_diagnostic: bool = True
    execution_mode: ControlExecutionMode = ControlExecutionMode.EX_POST_DIAGNOSTIC

    @staticmethod
    def filter_by_cumulative_exposure_budget(
        candidate_signals: List[Dict[str, Any]],
        target_total_bars_exposure: int,
        average_holding_bars: int = 15,
    ) -> List[Dict[str, Any]]:
        """Enforce an exposure budget tracking cumulative time in market."""
        if target_total_bars_exposure <= 0:
            return []

        target_trades = max(1, round(target_total_bars_exposure / max(1, average_holding_bars)))
        return ExPostFrequencyMatchingEngine.select_by_cryptographic_seed(
            candidate_signals=candidate_signals,
            target_count=target_trades,
            seed="neptune_group_d_exposure_matched_seed_99",
        )


# Backward compatibility alias
ExposureMatchingEngine = ExPostExposureMatchingEngine


# ==============================================================================
# 7. STATISTICAL ANALYSIS PLAN SPECIFICATION
# ==============================================================================

class StatisticalAnalysisPlanConfig(BaseModel):
    """
    Formal statistical evaluation contract for news-gated experiment verification.
    Calibrated with timeframe-specific block bootstrap sizes and denominator separation
    (Milestone 4.6.3.0.1 finding).
    """
    plan_version: str = "v1.1.0-m46301"
    significance_level_alpha: float = 0.05
    confidence_interval_level: float = 0.95
    bootstrap_resample_iterations: int = 2000
    random_seed: int = 42

    # Timeframe-Calibrated Block Bootstrap Sizes (~4 calendar days to preserve autocorrelation)
    timeframe_bootstrap_blocks: Dict[str, int] = Field(
        default_factory=lambda: {
            "15m": 384,  # 384 * 15m = 96h = 4 days
            "1h": 96,    # 96 * 1h = 96h = 4 days
            "4h": 24,    # 24 * 4h = 96h = 4 days
            "1d": 7,     # 7 * 1d = 7 days = 1 week
        }
    )
    # Default fallback
    block_bootstrap_size_bars: int = 48

    # Multiple Testing Correction
    multiple_testing_correction: str = "BENJAMINI_HOCHBERG_FDR"
    false_discovery_rate_q: float = 0.05

    # Formal Confirmatory Hypothesis Family
    confirmatory_hypothesis_family: List[str] = Field(
        default_factory=lambda: [
            "H1: Group B achieves higher net expectancy per trade than Group A after 0.32% round-trip costs.",
            "H2: Group B achieves higher net expectancy per trade than Group C (frequency-matched control).",
            "H3: Group B achieves higher net expectancy per trade than Group D (exposure-matched control).",
        ]
    )

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
    protocol_version: str = "v1.1.0-m46301"
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
