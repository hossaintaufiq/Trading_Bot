"""
NEPTUNE News Data Quality Reporter (`quality_reporter.py`)

Audits stored historical news datasets across 13 empirical dimensions:
1. Total records
2. Unique articles
3. Unique URLs
4. Unique canonical URLs
5. Unique event clusters
6. Duplicate rates
7. Missing timestamps
8. Timestamp precision distribution
9. Revision frequency
10. Asset relevance coverage
11. Source distribution
12. Failed downloads
13. Verification status breakdown
Governed by: Rule S-06, Rule S-07, ADR-023.
"""
import json
import sqlite3
from typing import Any, Dict, List, Optional


class NewsQualityReporter:
    """Produces objective, empirical data quality reports for historical news."""

    def __init__(self, db_path: str):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def generate_report(self) -> Dict[str, Any]:
        """Generate comprehensive data quality report."""
        with self._get_connection() as conn:
            cur = conn.cursor()

            # Article & URL Counts
            total_articles = cur.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0]
            unique_urls = cur.execute("SELECT COUNT(DISTINCT url) FROM news_articles").fetchone()[0]
            unique_canonical = cur.execute(
                "SELECT COUNT(DISTINCT canonical_url) FROM news_articles"
            ).fetchone()[0]

            # Version Counts
            total_versions = cur.execute("SELECT COUNT(*) FROM news_article_versions").fetchone()[0]
            multi_version_articles = cur.execute(
                "SELECT COUNT(*) FROM (SELECT article_id FROM news_article_versions GROUP BY article_id HAVING COUNT(*) > 1)"
            ).fetchone()[0]
            max_versions_for_article = cur.execute(
                "SELECT COALESCE(MAX(version_count), 0) FROM (SELECT COUNT(*) as version_count FROM news_article_versions GROUP BY article_id)"
            ).fetchone()[0]

            # Cluster Counts
            total_clusters = cur.execute("SELECT COUNT(*) FROM news_event_clusters").fetchone()[0]
            clustered_articles = cur.execute(
                "SELECT COUNT(DISTINCT article_id) FROM news_cluster_members"
            ).fetchone()[0]
            multi_article_clusters = cur.execute(
                "SELECT COUNT(*) FROM news_event_clusters WHERE article_count > 1"
            ).fetchone()[0]

            # Ingestion Runs
            total_runs = cur.execute("SELECT COUNT(*) FROM news_ingestion_runs").fetchone()[0]
            failed_records_sum = cur.execute(
                "SELECT COALESCE(SUM(failed_records), 0) FROM news_ingestion_runs"
            ).fetchone()[0]

            # Distributions
            precision_counts = dict(
                cur.execute(
                    "SELECT timestamp_precision, COUNT(*) FROM news_article_versions GROUP BY timestamp_precision"
                ).fetchall()
            )
            verification_counts = dict(
                cur.execute(
                    "SELECT source_verification_status, COUNT(*) FROM news_articles GROUP BY source_verification_status"
                ).fetchall()
            )
            source_counts = dict(
                cur.execute(
                    "SELECT source, COUNT(*) FROM news_articles GROUP BY source"
                ).fetchall()
            )

            # Timestamps Completeness
            missing_published_at = cur.execute(
                "SELECT COUNT(*) FROM news_article_versions WHERE published_at IS NULL"
            ).fetchone()[0]
            missing_available_at = cur.execute(
                "SELECT COUNT(*) FROM news_article_versions WHERE available_at IS NULL"
            ).fetchone()[0]

            # Asset Relevance Breakdown
            raw_entities = cur.execute("SELECT entities_json FROM news_articles").fetchall()
            asset_coverage = {"BTC": 0, "ETH": 0, "BNB": 0, "OTHER": 0}
            for row in raw_entities:
                try:
                    ents = json.loads(row[0])
                    for sym in ["BTC", "ETH", "BNB"]:
                        if sym in ents:
                            asset_coverage[sym] += 1
                    if not any(s in ents for s in ["BTC", "ETH", "BNB"]):
                        asset_coverage["OTHER"] += 1
                except Exception:
                    pass

            # Duplicate Rate
            duplicate_rate_pct = 0.0
            if total_articles > 0:
                duplicate_rate_pct = round(
                    ((total_articles - total_clusters) / total_articles) * 100.0, 2
                )

            return {
                "total_articles": total_articles,
                "total_versions": total_versions,
                "unique_raw_urls": unique_urls,
                "unique_canonical_urls": unique_canonical,
                "total_event_clusters": total_clusters,
                "clustered_articles": clustered_articles,
                "multi_article_clusters": multi_article_clusters,
                "multi_version_articles": multi_version_articles,
                "max_versions_observed": max_versions_for_article,
                "duplicate_rate_percent": duplicate_rate_pct,
                "missing_published_at_count": missing_published_at,
                "missing_available_at_count": missing_available_at,
                "precision_distribution": precision_counts,
                "verification_distribution": verification_counts,
                "source_distribution": source_counts,
                "asset_coverage": asset_coverage,
                "total_ingestion_runs": total_runs,
                "failed_records_count": failed_records_sum,
            }
