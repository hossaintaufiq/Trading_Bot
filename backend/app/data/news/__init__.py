"""
NEPTUNE News Data Ingestion & Storage Package
"""
from app.data.news.binance_client import BinanceNewsClient
from app.data.news.deduplication import NewsEventClusterer, are_articles_event_duplicates, canonicalize_url, compute_simhash_64, normalize_title
from app.data.news.gdelt_client import GdeltGkgClient
from app.data.news.manifest import NewsDatasetManifestGenerator
from app.data.news.models import (
    NewsArticle,
    NewsArticleVersion,
    NewsEventCluster,
    NewsIngestionRun,
    NewsSourceType,
    ReviewStatus,
    SourceVerificationStatus,
    TimestampPrecision,
)
from app.data.news.parquet_exporter import NewsParquetExporter
from app.data.news.quality_reporter import NewsQualityReporter
from app.data.news.service import NewsDataService
from app.data.news.temporal import (
    is_eligible_at_candle_close,
    parse_epoch_ms,
    parse_gdelt_date,
    parse_iso_utc,
    resolve_temporal_coordinates,
    to_iso_utc,
)

__all__ = [
    "NewsArticle",
    "NewsArticleVersion",
    "NewsEventCluster",
    "NewsIngestionRun",
    "NewsSourceType",
    "SourceVerificationStatus",
    "TimestampPrecision",
    "ReviewStatus",
    "BinanceNewsClient",
    "GdeltGkgClient",
    "NewsEventClusterer",
    "NewsDataService",
    "NewsParquetExporter",
    "NewsQualityReporter",
    "NewsDatasetManifestGenerator",
    "canonicalize_url",
    "normalize_title",
    "compute_simhash_64",
    "are_articles_event_duplicates",
    "resolve_temporal_coordinates",
    "is_eligible_at_candle_close",
    "parse_epoch_ms",
    "parse_gdelt_date",
    "parse_iso_utc",
    "to_iso_utc",
]
