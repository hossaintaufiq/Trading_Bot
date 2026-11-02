"""
NEPTUNE News Parquet Exporter (`parquet_exporter.py`)

Exports SQLite news articles, immutable revision versions, and event clusters
to standardized Parquet files partitioned by source and year.
Governed by: Rule S-08, ADR-001, ADR-023.
"""
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

    def export_all(self) -> Dict[str, Any]:
        """
        Export all news tables to Parquet partitions:
        storage/news/{source}/{YYYY}/articles.parquet
        storage/news/{source}/{YYYY}/versions.parquet
        storage/news/clusters/clusters.parquet
        """
        os.makedirs(self.storage_root, exist_ok=True)
        stats = {
            "articles_exported": 0,
            "versions_exported": 0,
            "clusters_exported": 0,
            "partitions": [],
        }

        with self._get_connection() as conn:
            # 1. Export Articles
            df_articles = pd.read_sql_query("SELECT * FROM news_articles", conn)
            if not df_articles.empty:
                # Group by source and year of created_at
                df_articles["year"] = pd.to_datetime(
                    df_articles["created_at"], errors="coerce"
                ).dt.year.fillna(2026).astype(int)

                for (source, year), group in df_articles.groupby(["source", "year"]):
                    out_dir = os.path.join(self.storage_root, str(source), str(year))
                    os.makedirs(out_dir, exist_ok=True)
                    out_path = os.path.join(out_dir, "articles.parquet")
                    group.drop(columns=["year"]).to_parquet(out_path, index=False)
                    stats["articles_exported"] += len(group)
                    stats["partitions"].append(out_path)

            # 2. Export Versions
            df_versions = pd.read_sql_query("SELECT * FROM news_article_versions", conn)
            if not df_versions.empty:
                # Merge with articles to get source
                df_art_source = df_articles[["article_id", "source"]].drop_duplicates()
                df_ver_merged = df_versions.merge(df_art_source, on="article_id", how="left")
                df_ver_merged["year"] = pd.to_datetime(
                    df_ver_merged["created_at"], errors="coerce"
                ).dt.year.fillna(2026).astype(int)

                for (source, year), group in df_ver_merged.groupby(["source", "year"]):
                    out_dir = os.path.join(self.storage_root, str(source), str(year))
                    os.makedirs(out_dir, exist_ok=True)
                    out_path = os.path.join(out_dir, "versions.parquet")
                    group.drop(columns=["source", "year"]).to_parquet(out_path, index=False)
                    stats["versions_exported"] += len(group)
                    if out_path not in stats["partitions"]:
                        stats["partitions"].append(out_path)

            # 3. Export Clusters
            df_clusters = pd.read_sql_query("SELECT * FROM news_event_clusters", conn)
            if not df_clusters.empty:
                cluster_dir = os.path.join(self.storage_root, "clusters")
                os.makedirs(cluster_dir, exist_ok=True)
                cluster_path = os.path.join(cluster_dir, "event_clusters.parquet")
                df_clusters.to_parquet(cluster_path, index=False)
                stats["clusters_exported"] = len(df_clusters)
                stats["partitions"].append(cluster_path)

        return stats
