"""
NEPTUNE Data Storage — SQLite Historical Dataset Repository

Implements IHistoricalDatasetRepository interface:
- Tracks dataset versions, provenance, start/end timestamps, candle counts.
- Stores SHA256 cryptographic fingerprints for bit-for-bit reproducibility.
- Enforces SQLite single-process WAL integrity (Rule S-08, ADR-001).
"""
import os
import sqlite3
from typing import Any, Dict, List, Optional

from app.config.settings import get_settings


class SqliteHistoricalDatasetRepository:
    """
    SQLite persistence for historical dataset manifests and version tracking.
    """

    def __init__(self, db_path: Optional[str] = None):
        settings = get_settings()
        if db_path:
            self.db_path = db_path
        else:
            raw_url = settings.database_url
            # Clean 'sqlite+aiosqlite:///' or 'sqlite:///'
            self.db_path = raw_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")

        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS historical_datasets (
                    dataset_id TEXT PRIMARY KEY,
                    dataset_version TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    start_timestamp TEXT NOT NULL,
                    end_timestamp TEXT NOT NULL,
                    candle_count INTEGER NOT NULL,
                    missing_intervals_count INTEGER NOT NULL,
                    duplicate_count INTEGER NOT NULL,
                    invalid_candle_count INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    schema_version TEXT NOT NULL,
                    validation_status TEXT NOT NULL,
                    sha256_fingerprint TEXT NOT NULL,
                    retrieval_timestamp TEXT NOT NULL,
                    storage_path TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_historical_datasets_sym_tf
                ON historical_datasets (symbol, timeframe, dataset_version);
            """)
            conn.commit()

    async def save_dataset_meta(self, record: Dict[str, Any]) -> str:
        dataset_id = record["dataset_id"]
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO historical_datasets (
                    dataset_id, dataset_version, symbol, timeframe,
                    start_timestamp, end_timestamp, candle_count,
                    missing_intervals_count, duplicate_count, invalid_candle_count,
                    source, schema_version, validation_status,
                    sha256_fingerprint, retrieval_timestamp, storage_path
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                );
            """, (
                record["dataset_id"],
                record["dataset_version"],
                record["symbol"],
                record["timeframe"],
                record["start_timestamp"],
                record["end_timestamp"],
                record["candle_count"],
                record["missing_intervals_count"],
                record["duplicate_count"],
                record["invalid_candle_count"],
                record["source"],
                record["schema_version"],
                record["validation_status"],
                record["sha256_fingerprint"],
                record["retrieval_timestamp"],
                record["storage_path"],
            ))
            conn.commit()
        return dataset_id

    async def get_dataset_meta(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM historical_datasets WHERE dataset_id = ?",
                (dataset_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    async def list_datasets(
        self, dataset_version: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            if dataset_version:
                cursor = conn.execute(
                    "SELECT * FROM historical_datasets WHERE dataset_version = ? ORDER BY symbol, timeframe",
                    (dataset_version,)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM historical_datasets ORDER BY dataset_version, symbol, timeframe"
                )
            return [dict(r) for r in cursor.fetchall()]

