"""
NEPTUNE News Domain Models (`models.py`)

Defines Pydantic models, enums, and data contracts for immutable news articles,
version revisions, event clusters, macro calendar records, and ingestion runs.
Governed by: Rule S-05, Rule S-08, ADR-023, ADR-024.
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SourceVerificationStatus(str, Enum):
    """Point-in-time verification taxonomy for historical news data."""
    POINT_IN_TIME_VERIFIED = "POINT_IN_TIME_VERIFIED"
    PARTIALLY_VERIFIED = "PARTIALLY_VERIFIED"
    HISTORICAL_TIMESTAMP_UNVERIFIED = "HISTORICAL_TIMESTAMP_UNVERIFIED"
    REJECTED = "REJECTED"


class TimestampPrecision(str, Enum):
    """Temporal resolution of timestamps."""
    MILLISECOND = "millisecond"
    SECOND = "second"
    FIFTEEN_MINUTE = "15_minute"
    DAY = "day"


class NewsSourceType(str, Enum):
    """Approved candidate news sources."""
    BINANCE_ANNOUNCEMENTS = "binance_announcements"
    GDELT_GKG = "gdelt_gkg"
    MACRO_CALENDAR = "macro_calendar"


class ReviewStatus(str, Enum):
    """Cluster editorial audit state."""
    UNREVIEWED = "UNREVIEWED"
    VERIFIED = "VERIFIED"
    FLAGGED = "FLAGGED"


class EventCategory(str, Enum):
    """15-Category Event Taxonomy per Milestone 4.6.2 Section 4."""
    SECURITY_INCIDENT = "SECURITY_INCIDENT"
    REGULATORY = "REGULATORY"
    MONETARY_POLICY = "MONETARY_POLICY"
    MACROECONOMIC = "MACROECONOMIC"
    ETF_INSTITUTIONAL_FLOW = "ETF_INSTITUTIONAL_FLOW"
    EXCHANGE_SOLVENCY = "EXCHANGE_SOLVENCY"
    EXCHANGE_OPERATIONAL = "EXCHANGE_OPERATIONAL"
    PROTOCOL_UPGRADE = "PROTOCOL_UPGRADE"
    NETWORK_OUTAGE = "NETWORK_OUTAGE"
    ASSET_LISTING = "ASSET_LISTING"
    ASSET_DELISTING = "ASSET_DELISTING"
    MARKET_STRUCTURE = "MARKET_STRUCTURE"
    LARGE_CAPITAL_FLOW = "LARGE_CAPITAL_FLOW"
    OTHER = "OTHER"
    UNCLASSIFIED = "UNCLASSIFIED"


class RelevanceClassification(str, Enum):
    """6-Tier Asset Relevance Classification per Milestone 4.6.2 Section 4."""
    DIRECT_ASSET = "DIRECT_ASSET"
    EXCHANGE_WIDE = "EXCHANGE_WIDE"
    MARKET_WIDE = "MARKET_WIDE"
    MACRO = "MACRO"
    OTHER_ASSET = "OTHER_ASSET"
    UNCLASSIFIED = "UNCLASSIFIED"


class NewsArticle(BaseModel):
    """Immutable identity of a news article with event & relevance classification."""
    article_id: str
    source: NewsSourceType
    source_record_id: Optional[str] = None
    url: str
    canonical_url: str
    domain: str
    title: str
    normalized_title: str
    language: str = "en"
    entities: List[str] = Field(default_factory=list)
    source_verification_status: SourceVerificationStatus
    raw_payload_sha256: str
    created_at: str

    # Classification fields (Milestone 4.6.2)
    event_category: EventCategory = EventCategory.UNCLASSIFIED
    relevance_classification: RelevanceClassification = RelevanceClassification.UNCLASSIFIED
    affected_assets: List[str] = Field(default_factory=list)
    classification_evidence: Dict[str, Any] = Field(default_factory=dict)
    classifier_version: Optional[str] = None
    confidence_score: float = 1.0
    classified_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["source"] = self.source.value
        d["source_verification_status"] = self.source_verification_status.value
        d["event_category"] = self.event_category.value
        d["relevance_classification"] = self.relevance_classification.value
        return d


class NewsArticleVersion(BaseModel):
    """Immutable version record of a news article with separate temporal coordinates."""
    version_id: str
    article_id: str
    version_number: int = 1
    title: str
    body_text: Optional[str] = None
    category: Optional[str] = None
    pairs: List[str] = Field(default_factory=list)
    raw_payload: str
    raw_payload_sha256: str
    published_at: Optional[str] = None
    updated_at: Optional[str] = None
    provider_seen_at: Optional[str] = None
    first_seen_at: str
    collected_at: str
    available_at: Optional[str] = None
    archive_available_at: Optional[str] = None
    research_available_at: Optional[str] = None
    timestamp_precision: TimestampPrecision
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["timestamp_precision"] = self.timestamp_precision.value
        return d


class NewsEventCluster(BaseModel):
    """Clustered real-world event grouping multiple syndicated articles."""
    cluster_id: str
    cluster_title: str
    primary_symbol: Optional[str] = None
    earliest_available_at: str
    article_count: int = 1
    clustering_algorithm: str = "simhash_v1_entity_matched"
    confidence_score: float = 1.0
    matching_evidence: Dict[str, Any] = Field(default_factory=dict)
    review_status: ReviewStatus = ReviewStatus.UNREVIEWED
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["review_status"] = self.review_status.value
        return d


class MacroEventRecord(BaseModel):
    """Source C: Authoritative historical macroeconomic or protocol calendar record."""
    macro_event_id: str
    event_name: str
    event_category: EventCategory
    scheduled_at: str
    actual_release_at: str
    source: str
    source_url: str
    source_record_id: Optional[str] = None
    affected_assets: List[str] = Field(default_factory=list)
    relevance_classification: RelevanceClassification
    source_verification_status: SourceVerificationStatus = SourceVerificationStatus.POINT_IN_TIME_VERIFIED
    timestamp_precision: TimestampPrecision = TimestampPrecision.SECOND
    description: Optional[str] = None
    raw_payload_sha256: str
    first_observed_at: Optional[str] = None
    collected_at: Optional[str] = None
    revision_observed_at: Optional[str] = None
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["event_category"] = self.event_category.value
        d["relevance_classification"] = self.relevance_classification.value
        d["source_verification_status"] = self.source_verification_status.value
        d["timestamp_precision"] = self.timestamp_precision.value
        return d


class NewsIngestionRun(BaseModel):
    """Execution checkpoint for resumable news ingestion runs."""
    run_id: str
    source: NewsSourceType
    target_asset: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    status: str = "RUNNING"
    records_ingested: int = 0
    unique_articles: int = 0
    failed_records: int = 0
    cursor_state: Optional[Dict[str, Any]] = None
    started_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["source"] = self.source.value
        return d
