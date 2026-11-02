"""
NEPTUNE Data Storage — SQLite News Repository (`news_repo.py`)

Implements INewsRepository interface:
- Tracks immutable news articles, revision histories, event clusters, and ingestion runs.
- Enforces SQLite single-process WAL integrity (Rule S-08, ADR-001, ADR-023).
- Immutability Invariant: Article revisions are strictly append-only. Historical versions
  are never mutated or deleted.
"""
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

from app.config.settings import get_settings


class SqliteNewsRepository:
    """
    SQLite persistence for news articles, versions, clusters, and ingestion runs.
    """

    def __init__(self, db_path: Optional[str] = None):
        settings = get_settings()
        if db_path:
            self.db_path = db_path
        else:
            raw_url = settings.database_url
            self.db_path = raw_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")

        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA foreign_keys=ON;")
        return conn

    def _init_db(self) -> None:
        # Load and execute 005_news_schema.sql if tables do not exist
        migration_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "database",
            "migrations",
            "005_news_schema.sql",
        )
        if os.path.exists(migration_path):
            with open(migration_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            with self._get_connection() as conn:
                conn.executescript(schema_sql)
                conn.commit()

    async def save_article(self, article: Dict[str, Any]) -> str:
        """
        Upsert article identity record. Article identity is immutable once created.
        """
        article_id = article["article_id"]
        entities_json = article.get("entities_json")
        if not isinstance(entities_json, str):
            entities_json = json.dumps(article.get("entities", []))

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO news_articles (
                    article_id, source, source_record_id, url, canonical_url,
                    domain, title, normalized_title, language, entities_json,
                    source_verification_status, raw_payload_sha256, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(article_id) DO UPDATE SET
                    canonical_url = excluded.canonical_url,
                    domain = excluded.domain,
                    normalized_title = excluded.normalized_title,
                    entities_json = excluded.entities_json,
                    source_verification_status = excluded.source_verification_status;
                """,
                (
                    article_id,
                    article["source"],
                    article.get("source_record_id"),
                    article["url"],
                    article.get("canonical_url", article["url"]),
                    article["domain"],
                    article["title"],
                    article["normalized_title"],
                    article.get("language", "en"),
                    entities_json,
                    article["source_verification_status"],
                    article["raw_payload_sha256"],
                    article["created_at"],
                ),
            )
            conn.commit()
        return article_id

    async def save_article_version(self, version: Dict[str, Any]) -> str:
        """
        Persist an immutable article version record.
        Raises ValueError if an attempt is made to overwrite an existing version with conflicting data.
        """
        version_id = version["version_id"]
        article_id = version["article_id"]
        version_number = int(version["version_number"])

        pairs_json = version.get("pairs_json")
        if not isinstance(pairs_json, str):
            pairs_json = json.dumps(version.get("pairs", []))

        with self._get_connection() as conn:
            # Check if version already exists
            cur = conn.cursor()
            cur.execute(
                "SELECT version_id, raw_payload_sha256 FROM news_article_versions WHERE article_id = ? AND version_number = ?",
                (article_id, version_number),
            )
            existing = cur.fetchone()
            if existing:
                if existing["raw_payload_sha256"] == version["raw_payload_sha256"]:
                    return existing["version_id"]
                else:
                    raise ValueError(
                        f"Immutability violation: Version {version_number} for article {article_id} already exists with different payload hash {existing['raw_payload_sha256']}."
                    )

            conn.execute(
                """
                INSERT INTO news_article_versions (
                    version_id, article_id, version_number, title, body_text,
                    category, pairs_json, raw_payload, raw_payload_sha256,
                    published_at, updated_at, provider_seen_at, first_seen_at,
                    collected_at, available_at, timestamp_precision, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    version_id,
                    article_id,
                    version_number,
                    version["title"],
                    version.get("body_text"),
                    version.get("category"),
                    pairs_json,
                    version["raw_payload"],
                    version["raw_payload_sha256"],
                    version.get("published_at"),
                    version.get("updated_at"),
                    version.get("provider_seen_at"),
                    version["first_seen_at"],
                    version["collected_at"],
                    version.get("available_at"),
                    version["timestamp_precision"],
                    version["created_at"],
                ),
            )
            conn.commit()
        return version_id

    async def get_article(self, article_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM news_articles WHERE article_id = ?", (article_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["entities"] = json.loads(res.get("entities_json", "[]"))
            return res

    async def get_article_versions(self, article_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM news_article_versions WHERE article_id = ? ORDER BY version_number ASC",
                (article_id,),
            )
            rows = cur.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["pairs"] = json.loads(d.get("pairs_json", "[]"))
                results.append(d)
            return results

    async def get_latest_article_version(self, article_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM news_article_versions WHERE article_id = ? ORDER BY version_number DESC LIMIT 1",
                (article_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            d = dict(row)
            d["pairs"] = json.loads(d.get("pairs_json", "[]"))
            return d

    async def find_article_by_source_record(
        self, source: str, source_record_id: str
    ) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM news_articles WHERE source = ? AND source_record_id = ?",
                (source, source_record_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["entities"] = json.loads(res.get("entities_json", "[]"))
            return res

    async def find_article_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM news_articles WHERE url = ?", (url,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["entities"] = json.loads(res.get("entities_json", "[]"))
            return res

    async def find_article_by_canonical_url(self, canonical_url: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM news_articles WHERE canonical_url = ?", (canonical_url,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["entities"] = json.loads(res.get("entities_json", "[]"))
            return res

    async def find_articles_by_normalized_title(
        self, normalized_title: str
    ) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT * FROM news_articles WHERE normalized_title = ?", (normalized_title,)
            )
            rows = cur.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["entities"] = json.loads(d.get("entities_json", "[]"))
                results.append(d)
            return results

    async def save_event_cluster(
        self, cluster: Dict[str, Any], member_article_ids: List[Tuple[str, int]]
    ) -> str:
        """
        Persist event cluster and its member article associations.
        member_article_ids is a list of tuples: (article_id, simhash_distance).
        """
        cluster_id = cluster["cluster_id"]
        evidence_json = cluster.get("matching_evidence_json")
        if not isinstance(evidence_json, str):
            evidence_json = json.dumps(cluster.get("matching_evidence", {}))

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO news_event_clusters (
                    cluster_id, cluster_title, primary_symbol, earliest_available_at,
                    article_count, clustering_algorithm, confidence_score,
                    matching_evidence_json, review_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    cluster_id,
                    cluster["cluster_title"],
                    cluster.get("primary_symbol"),
                    cluster["earliest_available_at"],
                    len(member_article_ids) or cluster.get("article_count", 1),
                    cluster["clustering_algorithm"],
                    float(cluster["confidence_score"]),
                    evidence_json,
                    cluster.get("review_status", "UNREVIEWED"),
                    cluster["created_at"],
                ),
            )

            for art_id, dist in member_article_ids:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO news_cluster_members (
                        cluster_id, article_id, simhash_distance, added_at
                    ) VALUES (?, ?, ?, ?);
                    """,
                    (cluster_id, art_id, int(dist), cluster["created_at"]),
                )
            conn.commit()
        return cluster_id

    async def get_event_cluster(self, cluster_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM news_event_clusters WHERE cluster_id = ?", (cluster_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            res["matching_evidence"] = json.loads(res.get("matching_evidence_json", "{}"))
            return res

    async def get_cluster_members(self, cluster_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT m.cluster_id, m.article_id, m.simhash_distance, m.added_at,
                       a.title, a.url, a.domain, a.source, a.source_verification_status
                FROM news_cluster_members m
                JOIN news_articles a ON m.article_id = a.article_id
                WHERE m.cluster_id = ?
                ORDER BY m.added_at ASC;
                """,
                (cluster_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    async def list_clusters(
        self, primary_symbol: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            if primary_symbol:
                cur.execute(
                    "SELECT * FROM news_event_clusters WHERE primary_symbol = ? ORDER BY earliest_available_at DESC LIMIT ?",
                    (primary_symbol, limit),
                )
            else:
                cur.execute(
                    "SELECT * FROM news_event_clusters ORDER BY earliest_available_at DESC LIMIT ?",
                    (limit,),
                )
            rows = cur.fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["matching_evidence"] = json.loads(d.get("matching_evidence_json", "{}"))
                results.append(d)
            return results

    async def record_ingestion_run(self, run_data: Dict[str, Any]) -> str:
        run_id = run_data["run_id"]
        cursor_state = run_data.get("cursor_state_json")
        if cursor_state is not None and not isinstance(cursor_state, str):
            cursor_state = json.dumps(cursor_state)

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO news_ingestion_runs (
                    run_id, source, target_asset, start_date, end_date,
                    status, records_ingested, unique_articles, failed_records,
                    cursor_state_json, started_at, completed_at, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    status = excluded.status,
                    records_ingested = excluded.records_ingested,
                    unique_articles = excluded.unique_articles,
                    failed_records = excluded.failed_records,
                    cursor_state_json = excluded.cursor_state_json,
                    completed_at = excluded.completed_at,
                    error_message = excluded.error_message;
                """,
                (
                    run_id,
                    run_data["source"],
                    run_data.get("target_asset"),
                    run_data.get("start_date"),
                    run_data.get("end_date"),
                    run_data["status"],
                    run_data.get("records_ingested", 0),
                    run_data.get("unique_articles", 0),
                    run_data.get("failed_records", 0),
                    cursor_state,
                    run_data["started_at"],
                    run_data.get("completed_at"),
                    run_data.get("error_message"),
                ),
            )
            conn.commit()
        return run_id

    async def get_ingestion_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM news_ingestion_runs WHERE run_id = ?", (run_id,))
            row = cur.fetchone()
            if not row:
                return None
            res = dict(row)
            if res.get("cursor_state_json"):
                try:
                    res["cursor_state"] = json.loads(res["cursor_state_json"])
                except Exception:
                    res["cursor_state"] = res["cursor_state_json"]
            return res

    async def get_quality_stats(self) -> Dict[str, Any]:
        """Aggregate statistical metrics for data quality auditing."""
        with self._get_connection() as conn:
            cur = conn.cursor()
            total_articles = cur.execute("SELECT COUNT(*) FROM news_articles").fetchone()[0]
            unique_urls = cur.execute("SELECT COUNT(DISTINCT url) FROM news_articles").fetchone()[0]
            unique_canonical = cur.execute(
                "SELECT COUNT(DISTINCT canonical_url) FROM news_articles"
            ).fetchone()[0]
            total_versions = cur.execute("SELECT COUNT(*) FROM news_article_versions").fetchone()[0]
            total_clusters = cur.execute("SELECT COUNT(*) FROM news_event_clusters").fetchone()[0]

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
            missing_pub = cur.execute(
                "SELECT COUNT(*) FROM news_article_versions WHERE published_at IS NULL"
            ).fetchone()[0]

            multi_version_articles = cur.execute(
                "SELECT COUNT(*) FROM (SELECT article_id FROM news_article_versions GROUP BY article_id HAVING COUNT(*) > 1)"
            ).fetchone()[0]

            return {
                "total_articles": total_articles,
                "unique_urls": unique_urls,
                "unique_canonical_urls": unique_canonical,
                "total_versions": total_versions,
                "total_clusters": total_clusters,
                "multi_version_articles": multi_version_articles,
                "missing_published_at": missing_pub,
                "precision_distribution": precision_counts,
                "verification_distribution": verification_counts,
                "source_distribution": source_counts,
            }
