"""
NEPTUNE News Domain Models (`models.py`)

Defines Pydantic models, enums, and data contracts for immutable news articles,
version revisions, event clusters, and ingestion runs.
Governed by: Rule S-05, Rule S-08, ADR-023.
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


class ReviewStatus(str, Enum):
    """Cluster editorial audit state."""
    UNREVIEWED = "UNREVIEWED"
    VERIFIED = "VERIFIED"
    FLAGGED = "FLAGGED"


class NewsArticle(BaseModel):
    """Immutable identity of a news article."""
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

    def to_dict(self) -> Dict[str, Any]:
        d = self.model_dump()
        d["source"] = self.source.value
        d["source_verification_status"] = self.source_verification_status.value
        return d


class NewsArticleVersion(BaseModel):
    """Immutable version record of a news article."""
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
