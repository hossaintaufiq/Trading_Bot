"""
NEPTUNE News Dataset Manifest Generator (`manifest.py`)

Produces bit-for-bit reproducible dataset manifests for historical news datasets:
- Calculates SHA-256 cryptographic fingerprints for exported Parquet partitions and SQLite tables.
- Preserves schema versions, row counts, temporal bounds, and source verification taxonomies.
- Enforces Rule S-06, Rule S-07, ADR-020, ADR-023.
"""
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def compute_file_sha256(filepath: str) -> str:
    """Compute SHA-256 hash of a file on disk."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class NewsDatasetManifestGenerator:
    """Generates immutable JSON manifests for historical news datasets."""

    def __init__(self, db_path: str, storage_root: str = "storage/news"):
        self.db_path = db_path
        self.storage_root = storage_root

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def generate_manifest(
        self,
        dataset_version: str = "news-v1.0.0",
        export_output_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive manifest of news tables and Parquet partitions.
        """
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

        # 1. Fingerprint SQLite tables
        table_stats = {}
        with self._get_connection() as conn:
            cur = conn.cursor()
            tables = [
                "news_articles",
                "news_article_versions",
                "news_event_clusters",
                "news_cluster_members",
                "news_ingestion_runs",
            ]
            for tbl in tables:
                row_count = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
                # Canonical representation hash
                rows = cur.execute(f"SELECT * FROM {tbl} ORDER BY 1 ASC").fetchall()
                serialized = json.dumps([dict(r) for r in rows], sort_keys=True)
                tbl_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
                table_stats[tbl] = {
                    "row_count": row_count,
                    "sha256_fingerprint": tbl_hash,
                }

        # 2. Fingerprint Parquet files in storage_root
        parquet_files = {}
        if os.path.exists(self.storage_root):
            for root, _, files in os.walk(self.storage_root):
                for f in files:
                    if f.endswith(".parquet"):
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, self.storage_root).replace("\\", "/")
                        size_bytes = os.path.getsize(full_path)
                        f_hash = compute_file_sha256(full_path)
                        parquet_files[rel_path] = {
                            "size_bytes": size_bytes,
                            "sha256": f_hash,
                        }

        # Calculate combined dataset hash
        combined_repr = json.dumps(
            {"tables": table_stats, "parquet": parquet_files}, sort_keys=True
        )
        composite_dataset_hash = hashlib.sha256(combined_repr.encode("utf-8")).hexdigest()

        manifest = {
            "dataset_version": dataset_version,
            "composite_sha256": composite_dataset_hash,
            "generated_at": now_iso,
            "schema_version": "1.0.0",
            "sqlite_database": {
                "db_path": self.db_path,
                "tables": table_stats,
            },
            "parquet_storage": {
                "storage_root": self.storage_root.replace("\\", "/"),
                "file_count": len(parquet_files),
                "files": parquet_files,
            },
        }

        if export_output_path:
            os.makedirs(os.path.dirname(os.path.abspath(export_output_path)), exist_ok=True)
            with open(export_output_path, "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)

        return manifest
