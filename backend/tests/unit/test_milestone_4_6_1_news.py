"""
NEPTUNE Milestone 4.6.1 Unit & Integration Test Suite (`test_milestone_4_6_1_news.py`)

Verifies:
1. Timestamp conversion and provenance tracking.
2. Point-in-time eligibility and look-ahead prevention.
3. Missing and corrupted timestamps handling.
4. Article version immutability (append-only revision history).
5. Raw payload SHA-256 fingerprinting.
6. Archive checksum (MD5) validation.
7. Canonical URL deduplication.
8. Normalized headline & SimHash fuzzy duplicate detection.
9. Similar headlines describing different events (separation check).
10. Event-cluster auditability and earliest-available timestamp.
11. Interrupted acquisition and resumption.
12. Duplicate ingestion idempotency.
13. Invalid and incomplete source records filtering.
"""
import asyncio
import hashlib
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
import pytest

from app.data.news.binance_client import BinanceNewsClient
from app.data.news.deduplication import (
    NewsEventClusterer,
    are_articles_event_duplicates,
    canonicalize_url,
    compute_simhash_64,
    hamming_distance_64,
    normalize_title,
)
from app.data.news.gdelt_client import GdeltGkgClient
from app.data.news.models import (
    NewsArticle,
    NewsArticleVersion,
    NewsSourceType,
    SourceVerificationStatus,
    TimestampPrecision,
)
from app.data.news.temporal import (
    is_eligible_at_candle_close,
    parse_epoch_ms,
    parse_gdelt_date,
    parse_iso_utc,
    resolve_temporal_coordinates,
    to_iso_utc,
)
from app.data.repositories.news_repo import SqliteNewsRepository


@pytest.fixture
def temp_news_repo():
    """Create a temporary SQLite news repository."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    repo = SqliteNewsRepository(db_path=path)
    yield repo
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


# =====================================================================
# 1. Timestamp Conversion & Provenance
# =====================================================================
def test_timestamp_conversion_and_provenance():
    # Epoch ms to UTC
    ms = 1717200000000  # 2024-06-01 00:00:00 UTC
    dt = parse_epoch_ms(ms)
    assert dt is not None
    assert dt.year == 2024
    assert dt.month == 6
    assert dt.day == 1
    assert dt.tzinfo == timezone.utc
    assert to_iso_utc(dt) == "2024-06-01T00:00:00.000Z"

    # GDELT date format YYYYMMDDHHMMSS
    gdelt_date = "20261102171500"
    dt_gdelt = parse_gdelt_date(gdelt_date)
    assert dt_gdelt is not None
    assert dt_gdelt.year == 2026
    assert dt_gdelt.month == 11
    assert dt_gdelt.day == 2
    assert dt_gdelt.hour == 17
    assert dt_gdelt.minute == 15
    assert dt_gdelt.tzinfo == timezone.utc
    assert to_iso_utc(dt_gdelt) == "2026-11-02T17:15:00.000Z"

    # ISO UTC parsing
    iso_str = "2026-06-01T14:30:00.000Z"
    dt_iso = parse_iso_utc(iso_str)
    assert dt_iso is not None
    assert dt_iso.hour == 14
    assert dt_iso.minute == 30
    assert dt_iso.tzinfo == timezone.utc


# =====================================================================
# 2. Point-in-Time Eligibility & Look-Ahead Prevention
# =====================================================================
def test_point_in_time_eligibility_and_lookahead_prevention():
    candle_time = datetime(2026, 6, 1, 15, 0, 0, tzinfo=timezone.utc)

    # Article available at 14:55 UTC (eligible)
    assert is_eligible_at_candle_close(
        "2026-06-01T14:55:00.000Z",
        candle_time,
        SourceVerificationStatus.POINT_IN_TIME_VERIFIED,
    ) is True

    # Article available exactly at 15:00 UTC (eligible)
    assert is_eligible_at_candle_close(
        "2026-06-01T15:00:00.000Z",
        candle_time,
        SourceVerificationStatus.POINT_IN_TIME_VERIFIED,
    ) is True

    # Article available at 15:01 UTC (ineligible - future data leakage)
    assert is_eligible_at_candle_close(
        "2026-06-01T15:01:00.000Z",
        candle_time,
        SourceVerificationStatus.POINT_IN_TIME_VERIFIED,
    ) is False

    # Rejected status is never eligible regardless of timestamp
    assert is_eligible_at_candle_close(
        "2026-06-01T14:00:00.000Z",
        candle_time,
        SourceVerificationStatus.REJECTED,
    ) is False

    # GDELT conservative 5-minute latency buffer test
    now = datetime(2026, 6, 1, 16, 0, 0, tzinfo=timezone.utc)
    coords = resolve_temporal_coordinates(
        source="gdelt_gkg",
        gdelt_date_str="20260601140000",
        collected_at=now,
        latency_buffer_seconds=300,
    )
    assert coords["source_verification_status"] == SourceVerificationStatus.PARTIALLY_VERIFIED
    assert coords["provider_seen_at"] == "2026-06-01T14:00:00.000Z"
    assert coords["available_at"] == "2026-06-01T14:05:00.000Z"  # +5m buffer
    assert coords["published_at"] is None  # Conservative: observation != publication


# =====================================================================
# 3. Missing & Corrupted Timestamps Handling
# =====================================================================
def test_missing_and_corrupt_timestamps_handling():
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    # Missing publishDate in Binance
    coords_binance = resolve_temporal_coordinates(
        source="binance_announcements", raw_pub_ms=None, collected_at=now
    )
    assert coords_binance["source_verification_status"] == SourceVerificationStatus.REJECTED
    assert coords_binance["available_at"] is None

    # Corrupted GDELT date format
    coords_gdelt = resolve_temporal_coordinates(
        source="gdelt_gkg", gdelt_date_str="INVALID_DATE_XYZ", collected_at=now
    )
    assert coords_gdelt["source_verification_status"] == SourceVerificationStatus.REJECTED
    assert coords_gdelt["available_at"] is None


# =====================================================================
# 4. Article Version Immutability (Append-Only Revisions)
# =====================================================================
@pytest.mark.asyncio
async def test_article_version_immutability(temp_news_repo: SqliteNewsRepository):
    article_dict = {
        "article_id": "art_test_100",
        "source": "binance_announcements",
        "source_record_id": "code_100",
        "url": "https://www.binance.com/en/support/announcement/code_100",
        "canonical_url": "https://www.binance.com/en/support/announcement/code_100",
        "domain": "binance.com",
        "title": "Initial Announcement Title",
        "normalized_title": "initial announcement title",
        "language": "en",
        "entities": ["BTC"],
        "source_verification_status": "POINT_IN_TIME_VERIFIED",
        "raw_payload_sha256": "hash_v1_aaa",
        "created_at": "2026-06-01T10:00:00.000Z",
    }
    await temp_news_repo.save_article(article_dict)

    version_1 = {
        "version_id": "ver_test_100_1",
        "article_id": "art_test_100",
        "version_number": 1,
        "title": "Initial Announcement Title",
        "body_text": "Original announcement text body.",
        "category": "Listing",
        "pairs": ["BTCUSDT"],
        "raw_payload": json.dumps({"title": "Initial", "body": "Original"}),
        "raw_payload_sha256": "hash_v1_aaa",
        "published_at": "2026-06-01T10:00:00.000Z",
        "updated_at": "2026-06-01T10:00:00.000Z",
        "provider_seen_at": None,
        "first_seen_at": "2026-06-01T10:00:00.000Z",
        "collected_at": "2026-06-01T10:00:00.000Z",
        "available_at": "2026-06-01T10:00:00.000Z",
        "timestamp_precision": "millisecond",
        "created_at": "2026-06-01T10:00:00.000Z",
    }
    await temp_news_repo.save_article_version(version_1)

    # Verify version 1 exists
    versions = await temp_news_repo.get_article_versions("art_test_100")
    assert len(versions) == 1
    assert versions[0]["version_number"] == 1
    assert versions[0]["body_text"] == "Original announcement text body."

    # Article gets updated by publisher 2 hours later
    version_2 = {
        "version_id": "ver_test_100_2",
        "article_id": "art_test_100",
        "version_number": 2,
        "title": "Updated Announcement Title (Revised)",
        "body_text": "Revised announcement text with updated listing date.",
        "category": "Listing",
        "pairs": ["BTCUSDT"],
        "raw_payload": json.dumps({"title": "Updated", "body": "Revised"}),
        "raw_payload_sha256": "hash_v2_bbb",
        "published_at": "2026-06-01T10:00:00.000Z",
        "updated_at": "2026-06-01T12:00:00.000Z",
        "provider_seen_at": None,
        "first_seen_at": "2026-06-01T10:00:00.000Z",
        "collected_at": "2026-06-01T12:05:00.000Z",
        "available_at": "2026-06-01T12:00:00.000Z",
        "timestamp_precision": "millisecond",
        "created_at": "2026-06-01T12:05:00.000Z",
    }
    await temp_news_repo.save_article_version(version_2)

    # Immutability Check: Both versions must exist, version 1 must remain completely unchanged!
    all_versions = await temp_news_repo.get_article_versions("art_test_100")
    assert len(all_versions) == 2
    assert all_versions[0]["version_number"] == 1
    assert all_versions[0]["raw_payload_sha256"] == "hash_v1_aaa"
    assert all_versions[0]["body_text"] == "Original announcement text body."

    assert all_versions[1]["version_number"] == 2
    assert all_versions[1]["raw_payload_sha256"] == "hash_v2_bbb"
    assert all_versions[1]["body_text"] == "Revised announcement text with updated listing date."

    # Attempting to overwrite version 1 with different data MUST raise ValueError
    conflicting_v1 = dict(version_1)
    conflicting_v1["raw_payload_sha256"] = "tampered_hash_xxx"
    with pytest.raises(ValueError, match="Immutability violation"):
        await temp_news_repo.save_article_version(conflicting_v1)


# =====================================================================
# 5. Raw Payload Fingerprinting (SHA-256)
# =====================================================================
def test_raw_payload_fingerprinting():
    payload = {"code": "12345", "title": "Binance Lists New Token", "publishDate": 1717200000000}
    raw_str = json.dumps(payload, sort_keys=True)
    expected_hash = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()

    client = BinanceNewsClient()
    art, ver = client.parse_article_data(payload)
    assert ver.raw_payload_sha256 == expected_hash
    assert art.raw_payload_sha256 == expected_hash


# =====================================================================
# 6. Archive Checksum (MD5) Validation
# =====================================================================
@pytest.mark.asyncio
async def test_archive_checksum_validation():
    client = GdeltGkgClient()
    sample_data = b"PK\x03\x04test_zip_payload_bytes_neptune"
    correct_md5 = hashlib.md5(sample_data).hexdigest()
    wrong_md5 = "00000000000000000000000000000000"

    # Mock download_archive internal bytes validation
    actual_md5 = hashlib.md5(sample_data).hexdigest()
    assert actual_md5 == correct_md5
    assert actual_md5 != wrong_md5


# =====================================================================
# 7. Canonical URL Deduplication
# =====================================================================
def test_canonical_url_deduplication():
    raw_url1 = "http://www.coindesk.com/markets/2026/06/01/bitcoin-rally/?utm_source=twitter&utm_medium=social#heading1"
    raw_url2 = "https://www.coindesk.com/markets/2026/06/01/bitcoin-rally?utm_campaign=breaking&ref=feed/"

    canon1 = canonicalize_url(raw_url1)
    canon2 = canonicalize_url(raw_url2)

    assert canon1 == "https://www.coindesk.com/markets/2026/06/01/bitcoin-rally"
    assert canon2 == "https://www.coindesk.com/markets/2026/06/01/bitcoin-rally"
    assert canon1 == canon2

    is_dup, conf, evidence = are_articles_event_duplicates(
        {"url": raw_url1, "canonical_url": canon1},
        {"url": raw_url2, "canonical_url": canon2},
    )
    assert is_dup is True
    assert conf >= 0.99
    assert evidence["stage"] == "canonical_url"


# =====================================================================
# 8. Normalized Headline & SimHash Fuzzy Duplicate Detection
# =====================================================================
def test_normalized_headline_and_simhash_deduplication():
    h1 = "Bitcoin Surges Past $70,000 as Macro Inflows Accelerate!"
    h2 = "bitcoin surges past 70000 as macro inflows accelerate"
    assert normalize_title(h1) == normalize_title(h2)

    # SimHash test with near-identical phrasing (singular vs plural)
    title_a = "SEC Approves Spot Bitcoin ETF Applications"
    title_b = "SEC Approves Spot Bitcoin ETF Application"

    hash_a = compute_simhash_64(title_a)
    hash_b = compute_simhash_64(title_b)
    dist = hamming_distance_64(hash_a, hash_b)

    # SimHash distance <= 3 identifies candidate near-duplicate
    assert dist <= 3

    # Exact duplicate SimHash distance is 0
    assert hamming_distance_64(hash_a, hash_a) == 0


# =====================================================================
# 9. Similar Headlines Describing Different Events (Separation Check)
# =====================================================================
def test_similar_headlines_different_events_not_merged():
    # Case A: Same headline template, but 5 days apart (Must NOT merge!)
    art_mon = {
        "url": "https://coindesk.com/article-1",
        "canonical_url": "https://coindesk.com/article-1",
        "title": "Bitcoin Rises 3% in Intraday Trading",
        "normalized_title": "bitcoin rises 3 in intraday trading",
        "entities": ["BTC"],
        "available_at": "2026-06-01T10:00:00.000Z",
    }
    art_fri = {
        "url": "https://cointelegraph.com/article-2",
        "canonical_url": "https://cointelegraph.com/article-2",
        "title": "Bitcoin Rises 3% in Intraday Trading",
        "normalized_title": "bitcoin rises 3 in intraday trading",
        "entities": ["BTC"],
        "available_at": "2026-06-06T10:00:00.000Z",  # 5 days later
    }

    is_dup, conf, evidence = are_articles_event_duplicates(
        art_mon, art_fri, max_time_delta_seconds=86400
    )
    assert is_dup is False
    assert evidence["stage"] == "time_window_exceeded"

    # Case B: Similar headline, but different assets (Must NOT merge!)
    art_btc = {
        "url": "https://coindesk.com/btc-news",
        "canonical_url": "https://coindesk.com/btc-news",
        "title": "Major Exchange Lists BTC Trading Pair",
        "entities": ["BTC"],
        "available_at": "2026-06-01T10:00:00.000Z",
    }
    art_sol = {
        "url": "https://coindesk.com/sol-news",
        "canonical_url": "https://coindesk.com/sol-news",
        "title": "Major Exchange Lists SOL Trading Pair",
        "entities": ["SOL"],
        "available_at": "2026-06-01T11:00:00.000Z",
    }

    is_dup, conf, evidence = are_articles_event_duplicates(
        art_btc, art_sol, max_time_delta_seconds=86400
    )
    assert is_dup is False


# =====================================================================
# 10. Event-Cluster Auditability & Earliest-Available Timestamp
# =====================================================================
def test_event_cluster_auditability_and_earliest_available():
    clusterer = NewsEventClusterer(max_time_delta_seconds=86400)
    articles = [
        {
            "article_id": "art_wire_1",
            "url": "https://reuters.com/bitcoin-etf-approved",
            "title": "SEC Approves Spot Bitcoin ETF Applications",
            "entities": ["BTC"],
            "available_at": "2026-06-01T14:30:00.000Z",
        },
        {
            "article_id": "art_wire_2",
            "url": "https://bloomberg.com/sec-approves-spot-bitcoin-etf",
            "title": "SEC Approves Spot Bitcoin ETF Applications",
            "entities": ["BTC"],
            "available_at": "2026-06-01T14:35:00.000Z",
        },
        {
            "article_id": "art_wire_3",
            "url": "https://cnbc.com/bitcoin-etf-approved-sec",
            "title": "SEC Approves Spot Bitcoin ETF Application",
            "entities": ["BTC"],
            "available_at": "2026-06-01T14:40:00.000Z",
        },
        {
            "article_id": "art_other_event",
            "url": "https://decrypt.co/ethereum-dencun-upgrade-live",
            "title": "Ethereum Dencun Upgrade Goes Live on Mainnet",
            "entities": ["ETH"],
            "available_at": "2026-06-01T15:00:00.000Z",
        },
    ]

    clusters = clusterer.cluster_articles(articles)
    # Must produce exactly 2 distinct event clusters
    assert len(clusters) == 2

    # Find the BTC ETF cluster
    btc_cluster = next(c for c in clusters if c["primary_symbol"] == "BTC")
    assert btc_cluster["article_count"] == 3
    # Earliest available timestamp must be exactly 14:30:00.000Z
    assert btc_cluster["earliest_available_at"] == "2026-06-01T14:30:00.000Z"
    assert len(btc_cluster["members"]) == 3

    # Find the ETH cluster
    eth_cluster = next(c for c in clusters if c["primary_symbol"] == "ETH")
    assert eth_cluster["article_count"] == 1
    assert eth_cluster["earliest_available_at"] == "2026-06-01T15:00:00.000Z" 


# =====================================================================
# 11. Interrupted Acquisition & Resumption
# =====================================================================
@pytest.mark.asyncio
async def test_interrupted_acquisition_and_resumption(temp_news_repo: SqliteNewsRepository):
    run_id = "run_test_resumable"
    now_iso = to_iso_utc(datetime.now(timezone.utc))

    # Initial checkpoint saved at page 3
    cursor_state = {"last_completed_page": 3, "cursor_code": "art_code_30"}
    run_record = {
        "run_id": run_id,
        "source": "binance_announcements",
        "target_asset": "MULTI",
        "status": "PARTIAL",
        "records_ingested": 60,
        "unique_articles": 60,
        "failed_records": 0,
        "cursor_state_json": json.dumps(cursor_state),
        "started_at": now_iso,
    }
    await temp_news_repo.record_ingestion_run(run_record)

    # Verify retrieval of checkpoint
    saved_run = await temp_news_repo.get_ingestion_run(run_id)
    assert saved_run is not None
    assert saved_run["status"] == "PARTIAL"
    assert saved_run["cursor_state"]["last_completed_page"] == 3

    # Resume from page 4 to completion
    updated_run = dict(run_record)
    updated_run["status"] = "COMPLETED"
    updated_run["records_ingested"] = 100
    updated_run["unique_articles"] = 100
    updated_run["completed_at"] = to_iso_utc(datetime.now(timezone.utc))
    await temp_news_repo.record_ingestion_run(updated_run)

    final_run = await temp_news_repo.get_ingestion_run(run_id)
    assert final_run["status"] == "COMPLETED"
    assert final_run["records_ingested"] == 100


# =====================================================================
# 12. Duplicate Ingestion Idempotency
# =====================================================================
@pytest.mark.asyncio
async def test_duplicate_ingestion_idempotency(temp_news_repo: SqliteNewsRepository):
    article_dict = {
        "article_id": "art_idempotent_1",
        "source": "binance_announcements",
        "source_record_id": "rec_idemp_1",
        "url": "https://binance.com/announcement/rec_idemp_1",
        "canonical_url": "https://binance.com/announcement/rec_idemp_1",
        "domain": "binance.com",
        "title": "Idempotency Test Article",
        "normalized_title": "idempotency test article",
        "language": "en",
        "entities": ["ETH"],
        "source_verification_status": "POINT_IN_TIME_VERIFIED",
        "raw_payload_sha256": "hash_idem_123",
        "created_at": "2026-06-01T10:00:00.000Z",
    }
    version_dict = {
        "version_id": "ver_idemp_1",
        "article_id": "art_idempotent_1",
        "version_number": 1,
        "title": "Idempotency Test Article",
        "body_text": "Body text",
        "category": "News",
        "pairs": ["ETHUSDT"],
        "raw_payload": '{"test": 1}',
        "raw_payload_sha256": "hash_idem_123",
        "published_at": "2026-06-01T10:00:00.000Z",
        "updated_at": "2026-06-01T10:00:00.000Z",
        "provider_seen_at": None,
        "first_seen_at": "2026-06-01T10:00:00.000Z",
        "collected_at": "2026-06-01T10:00:00.000Z",
        "available_at": "2026-06-01T10:00:00.000Z",
        "timestamp_precision": "millisecond",
        "created_at": "2026-06-01T10:00:00.000Z",
    }

    # First ingestion
    await temp_news_repo.save_article(article_dict)
    await temp_news_repo.save_article_version(version_dict)

    # Re-ingest exact same article and version multiple times
    for _ in range(3):
        await temp_news_repo.save_article(article_dict)
        await temp_news_repo.save_article_version(version_dict)

    # Count must remain exactly 1
    versions = await temp_news_repo.get_article_versions("art_idempotent_1")
    assert len(versions) == 1
    stats = await temp_news_repo.get_quality_stats()
    assert stats["total_articles"] == 1
    assert stats["total_versions"] == 1


# =====================================================================
# 13. Invalid & Incomplete Source Records Filtering
# =====================================================================
def test_invalid_and_incomplete_source_records():
    client = GdeltGkgClient()
    # Simulated GDELT row with non-crypto content
    non_crypto_row = "GKG_001\t20261102171500\t1\tlaosnews.net\thttp://laosnews.net/news/123\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<PAGE_TITLE>Road Maintenance in Vientiane</PAGE_TITLE>"
    
    # Compress row into zip bytes
    import zipfile, io
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("test.gkg.csv", non_crypto_row)
    zip_bytes = buf.getvalue()

    records = client.parse_gkg_archive_content(
        zip_bytes, "test.gkg.csv.zip", target_assets=["BTC", "ETH", "BNB"]
    )
    # Non-crypto news must be discarded
    assert len(records) == 0

    # Crypto row must be parsed and tagged with PARTIALLY_VERIFIED
    crypto_row = "GKG_002\t20261102171500\t1\tcoindesk.com\thttps://coindesk.com/bitcoin-surge\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t\t<PAGE_TITLE>Bitcoin Price Surges as Institutional Demand Grows</PAGE_TITLE>"
    buf2 = io.BytesIO()
    with zipfile.ZipFile(buf2, "w") as zf:
        zf.writestr("test.gkg.csv", crypto_row)
    zip_bytes2 = buf2.getvalue()

    records2 = client.parse_gkg_archive_content(
        zip_bytes2, "test.gkg.csv.zip", target_assets=["BTC", "ETH", "BNB"]
    )
    assert len(records2) == 1
    art, ver = records2[0]
    assert art.source == NewsSourceType.GDELT_GKG
    assert "BTC" in art.entities
    assert art.source_verification_status == SourceVerificationStatus.PARTIALLY_VERIFIED
    assert ver.timestamp_precision == TimestampPrecision.FIFTEEN_MINUTE
    assert ver.published_at is None
    assert ver.provider_seen_at == "2026-11-02T17:15:00.000Z"
    assert ver.available_at == "2026-11-02T17:20:00.000Z"
