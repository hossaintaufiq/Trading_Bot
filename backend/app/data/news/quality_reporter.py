"""
NEPTUNE News Data Quality Reporter (`quality_reporter.py`)

Audits stored historical news datasets across empirical dimensions:
1. Total articles, versions, clusters, and macro events
2. Source distribution
3. Event taxonomy category distribution (15 categories)
4. Asset relevance distribution (6 tiers)
5. Monthly asset coverage for BTC, ETH, BNB, EXCHANGE_WIDE, MARKET_WIDE, MACRO
6. Timestamp precision distribution
7. Point-in-time verification status breakdown
8. Deduplication and clustering metrics
Governed by: Rule S-06, Rule S-07, ADR-023, ADR-024.
"""
import json
import sqlite3
from typing import Any, Dict, List, Optional
import pandas as pd


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

            # Macro Event Counts
            total_macro_events = 0
            table_check = cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='news_macro_events'"
            ).fetchone()
            if table_check:
                total_macro_events = cur.execute("SELECT COUNT(*) FROM news_macro_events").fetchone()[0]

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
            category_counts = dict(
                cur.execute(
                    "SELECT COALESCE(event_category, 'UNCLASSIFIED'), COUNT(*) FROM news_articles GROUP BY event_category"
                ).fetchall()
            )
            relevance_counts = dict(
                cur.execute(
                    "SELECT COALESCE(relevance_classification, 'UNCLASSIFIED'), COUNT(*) FROM news_articles GROUP BY relevance_classification"
                ).fetchall()
            )

            # Timestamps Completeness
            missing_published_at = cur.execute(
                "SELECT COUNT(*) FROM news_article_versions WHERE published_at IS NULL"
            ).fetchone()[0]
            missing_available_at = cur.execute(
                "SELECT COUNT(*) FROM news_article_versions WHERE available_at IS NULL"
            ).fetchone()[0]

            # Monthly Asset & Relevance Coverage
            # Join articles with their earliest version to get effective date
            df_dates = pd.read_sql_query(
                """
                SELECT a.article_id, a.event_category, a.relevance_classification, a.affected_assets_json,
                       COALESCE(v.published_at, v.provider_seen_at, v.created_at) as effective_date
                FROM news_articles a
                LEFT JOIN news_article_versions v ON a.article_id = v.article_id AND v.version_number = 1
                """,
                conn,
            )

            monthly_coverage: Dict[str, Dict[str, int]] = {}
            if not df_dates.empty:
                df_dates["month"] = pd.to_datetime(df_dates["effective_date"], errors="coerce", utc=True).dt.strftime("%Y-%m")
                df_dates["month"] = df_dates["month"].fillna("UNKNOWN")

                for _, row in df_dates.iterrows():
                    m = row["month"]
                    if m not in monthly_coverage:
                        monthly_coverage[m] = {
                            "BTC": 0, "ETH": 0, "BNB": 0,
                            "EXCHANGE_WIDE": 0, "MARKET_WIDE": 0, "MACRO": 0, "OTHER": 0, "TOTAL": 0,
                        }
                    monthly_coverage[m]["TOTAL"] += 1
                    rel = row["relevance_classification"]
                    if rel in monthly_coverage[m]:
                        monthly_coverage[m][rel] += 1
                    else:
                        monthly_coverage[m]["OTHER"] += 1

                    try:
                        assets = json.loads(row["affected_assets_json"] or "[]")
                    except Exception:
                        assets = []
                    for ast in ["BTC", "ETH", "BNB"]:
                        if ast in assets:
                            monthly_coverage[m][ast] += 1

            return {
                "total_articles": total_articles,
                "unique_urls": unique_urls,
                "unique_canonical_urls": unique_canonical,
                "total_versions": total_versions,
                "multi_version_articles": multi_version_articles,
                "max_versions_for_article": max_versions_for_article,
                "total_clusters": total_clusters,
                "clustered_articles": clustered_articles,
                "multi_article_clusters": multi_article_clusters,
                "total_macro_events": total_macro_events,
                "total_ingestion_runs": total_runs,
                "failed_records_sum": failed_records_sum,
                "missing_published_at": missing_published_at,
                "missing_available_at": missing_available_at,
                "precision_distribution": precision_counts,
                "verification_distribution": verification_counts,
                "source_distribution": source_counts,
                "category_distribution": category_counts,
                "relevance_distribution": relevance_counts,
                "monthly_coverage": monthly_coverage,
            }
