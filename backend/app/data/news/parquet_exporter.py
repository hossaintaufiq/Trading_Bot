"""
NEPTUNE News Parquet Exporter (`parquet_exporter.py`)

Exports SQLite news articles, immutable revision versions, event clusters,
and macro event calendar records to standardized Parquet files partitioned by source and year.
Governed by: Rule S-08, ADR-001, ADR-023, ADR-024.
"""
import hashlib
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional
import pandas as pd


class NewsParquetExporter:
    """Exports relational SQLite news data into partitioned Parquet storage."""

    def __init__(self, db_path: str, storage_root: str = "storage/news"):
        self.db_path = db_path
        self.storage_root = storage_root

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def _compute_sha256(file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def export_all(self) -> Dict[str, Any]:
        """
        Export all news tables to Parquet partitions:
        storage/news/{source}/{YYYY}/articles.parquet
        storage/news/{source}/{YYYY}/versions.parquet
        storage/news/clusters/event_clusters.parquet
        storage/news/macro_calendar/macro_events.parquet
        """
        os.makedirs(self.storage_root, exist_ok=True)
        stats: Dict[str, Any] = {
            "articles_exported": 0,
            "versions_exported": 0,
            "clusters_exported": 0,
            "macro_events_exported": 0,
            "partitions": [],
            "file_hashes": {},
        }

        with self._get_connection() as conn:
            # 1. Export Articles
            df_articles = pd.read_sql_query("SELECT * FROM news_articles", conn)
            df_versions = pd.read_sql_query("SELECT * FROM news_article_versions", conn)

            if not df_articles.empty:
                # Determine event year from versions published_at or created_at
                ver_dates = df_versions[["article_id", "published_at", "provider_seen_at"]].drop_duplicates()
                df_art_dates = df_articles.merge(ver_dates, on="article_id", how="left")
                
                # Preferred date is published_at -> provider_seen_at -> created_at
                date_col = df_art_dates["published_at"].fillna(df_art_dates["provider_seen_at"]).fillna(df_art_dates["created_at"])
                df_articles["year"] = pd.to_datetime(date_col, errors="coerce").dt.year.fillna(2024).astype(int)

                for (source, year), group in df_articles.groupby(["source", "year"]):
                    out_dir = os.path.join(self.storage_root, str(source), str(year))
                    os.makedirs(out_dir, exist_ok=True)
                    out_path = os.path.join(out_dir, "articles.parquet")
                    group.drop(columns=["year"]).to_parquet(out_path, index=False)
                    stats["articles_exported"] += len(group)
                    stats["partitions"].append(out_path)
                    stats["file_hashes"][out_path] = self._compute_sha256(out_path)

            # 2. Export Versions
            if not df_versions.empty:
                df_art_source = df_articles[["article_id", "source"]].drop_duplicates()
                df_ver_merged = df_versions.merge(df_art_source, on="article_id", how="left")
                date_col = df_ver_merged["published_at"].fillna(df_ver_merged["provider_seen_at"]).fillna(df_ver_merged["created_at"])
                df_ver_merged["year"] = pd.to_datetime(date_col, errors="coerce").dt.year.fillna(2024).astype(int)

                for (source, year), group in df_ver_merged.groupby(["source", "year"]):
                    out_dir = os.path.join(self.storage_root, str(source), str(year))
                    os.makedirs(out_dir, exist_ok=True)
                    out_path = os.path.join(out_dir, "versions.parquet")
                    group.drop(columns=["source", "year"]).to_parquet(out_path, index=False)
                    stats["versions_exported"] += len(group)
                    if out_path not in stats["partitions"]:
                        stats["partitions"].append(out_path)
                    stats["file_hashes"][out_path] = self._compute_sha256(out_path)

            # 3. Export Clusters
            df_clusters = pd.read_sql_query("SELECT * FROM news_event_clusters", conn)
            if not df_clusters.empty:
                cluster_dir = os.path.join(self.storage_root, "clusters")
                os.makedirs(cluster_dir, exist_ok=True)
                cluster_path = os.path.join(cluster_dir, "event_clusters.parquet")
                df_clusters.to_parquet(cluster_path, index=False)
                stats["clusters_exported"] = len(df_clusters)
                stats["partitions"].append(cluster_path)
                stats["file_hashes"][cluster_path] = self._compute_sha256(cluster_path)

            # 4. Export Macro Events (Source C)
            cursor = conn.cursor()
            table_check = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='news_macro_events'").fetchone()
            if table_check:
                df_macro = pd.read_sql_query("SELECT * FROM news_macro_events", conn)
                if not df_macro.empty:
                    macro_dir = os.path.join(self.storage_root, "macro_calendar")
                    os.makedirs(macro_dir, exist_ok=True)
                    macro_path = os.path.join(macro_dir, "macro_events.parquet")
                    df_macro.to_parquet(macro_path, index=False)
                    stats["macro_events_exported"] = len(df_macro)
                    stats["partitions"].append(macro_path)
                    stats["file_hashes"][macro_path] = self._compute_sha256(macro_path)

        return stats
