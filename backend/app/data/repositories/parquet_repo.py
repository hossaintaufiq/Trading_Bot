"""
NEPTUNE Data Storage — Parquet Market Data Repository

Implements IMarketDataRepository protocol:
- Stores historical candles in partitioned Apache Parquet archives:
    storage/historical/{symbol}/{timeframe}/{YYYY}/{MM}/{YYYY}-{MM}.parquet
- Cache-first loading: avoids network overhead by querying disk first (ADR-014).
- Safe duplicate deduplication on append (merging on timestamp, keeping latest).
- Fast latest-timestamp query for incremental backfill delta computation.
"""
import os
from datetime import datetime, timezone
from typing import List, Optional

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from app.config.settings import get_settings


class ParquetMarketDataRepository:
    """
    Repository for persisting and loading historical candle time-series using Apache Parquet.
    """

    def __init__(self, base_dir: Optional[str] = None):
        settings = get_settings()
        self.base_dir = base_dir or settings.historical_data_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def _get_timeframe_dir(self, symbol: str, timeframe: str) -> str:
        sym_clean = symbol.upper().replace("/", "")
        path = os.path.join(self.base_dir, sym_clean, timeframe)
        os.makedirs(path, exist_ok=True)
        return path

    def _get_partition_path(self, symbol: str, timeframe: str, year: int, month: int) -> str:
        sym_clean = symbol.upper().replace("/", "")
        month_str = f"{month:02d}"
        dir_path = os.path.join(self.base_dir, sym_clean, timeframe, str(year), month_str)
        os.makedirs(dir_path, exist_ok=True)
        return os.path.join(dir_path, f"{year}-{month_str}.parquet")

    def _find_all_partition_files(self, symbol: str, timeframe: str) -> List[str]:
        tf_dir = self._get_timeframe_dir(symbol, timeframe)
        files = []
        for root, _, filenames in os.walk(tf_dir):
            for fn in filenames:
                if fn.endswith(".parquet"):
                    files.append(os.path.join(root, fn))
        files.sort()
        return files

    async def get_latest_candle_time(
        self, symbol: str, timeframe: str
    ) -> Optional[datetime]:
        """
        Return the timestamp of the most recent stored closed candle.
        Scans partition files in reverse order for sub-millisecond retrieval.
        """
        files = self._find_all_partition_files(symbol, timeframe)
        if not files:
            return None

        # Inspect latest file (last in sorted list)
        latest_file = files[-1]
        try:
            table = pq.read_table(latest_file, columns=["timestamp"])
            if table.num_rows == 0:
                return None
            ts_val = table.column("timestamp")[-1].as_py()
            if isinstance(ts_val, (int, float)):
                sec = ts_val / 1000.0 if ts_val > 1e11 else float(ts_val)
                return datetime.fromtimestamp(sec, tz=timezone.utc)
            elif isinstance(ts_val, str):
                cleaned = ts_val.replace("Z", "+00:00")
                dt = datetime.fromisoformat(cleaned)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            elif isinstance(ts_val, datetime):
                return ts_val if ts_val.tzinfo else ts_val.replace(tzinfo=timezone.utc)
        except Exception:
            return None
        return None

    async def save_candles(
        self, symbol: str, timeframe: str, df: pd.DataFrame
    ) -> int:
        """
        Upsert candles into Parquet storage.
        Deduplicates timestamps and merges with existing monthly partitions.
        """
        if df.empty:
            return 0

        # Ensure required columns
        df = df.copy()
        if "timestamp" not in df.columns:
            raise ValueError("Candle DataFrame must contain 'timestamp' column.")

        # Convert timestamps to UTC datetime for grouping
        if pd.api.types.is_string_dtype(df["timestamp"]):
            dt_series = pd.to_datetime(df["timestamp"], utc=True)
        elif pd.api.types.is_numeric_dtype(df["timestamp"]):
            unit = "ms" if df["timestamp"].iloc[0] > 1e11 else "s"
            dt_series = pd.to_datetime(df["timestamp"], unit=unit, utc=True)
        else:
            dt_series = pd.to_datetime(df["timestamp"], utc=True)

        df["_dt"] = dt_series
        df["_year"] = df["_dt"].dt.year
        df["_month"] = df["_dt"].dt.month

        # Standardize timestamp string column (Rule A-02, ADR-012)
        df["timestamp"] = df["_dt"].dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")

        total_saved = 0

        # Group by year and month
        for (year, month), group in df.groupby(["_year", "_month"]):
            file_path = self._get_partition_path(symbol, timeframe, int(year), int(month))
            clean_cols = [c for c in group.columns if not c.startswith("_")]
            group_clean = group[clean_cols].copy()

            if os.path.exists(file_path):
                try:
                    existing_df = pq.read_table(file_path).to_pandas()
                    combined = pd.concat([existing_df, group_clean], ignore_index=True)
                    # Deduplicate on timestamp, keeping latest
                    combined = combined.drop_duplicates(subset=["timestamp"], keep="last")
                    combined = combined.sort_values(by="timestamp").reset_index(drop=True)
                    table_to_write = pa.Table.from_pandas(combined)
                except Exception:
                    table_to_write = pa.Table.from_pandas(group_clean)
            else:
                group_clean = group_clean.sort_values(by="timestamp").reset_index(drop=True)
                table_to_write = pa.Table.from_pandas(group_clean)

            pq.write_table(table_to_write, file_path, compression="snappy")
            total_saved += len(group_clean)

        return total_saved

    async def load_candles(
        self,
        symbol: str,
        timeframe: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Load historical candles from Parquet storage.
        Returns DataFrame sorted by timestamp ascending.
        """
        files = self._find_all_partition_files(symbol, timeframe)
        if not files:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        tables = []
        for fp in files:
            try:
                t = pq.read_table(fp)
                tables.append(t)
            except Exception:
                continue

        if not tables:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        combined_table = pa.concat_tables(tables)
        df = combined_table.to_pandas()

        if df.empty:
            return df

        # Deduplicate and sort
        df = df.drop_duplicates(subset=["timestamp"]).sort_values(by="timestamp").reset_index(drop=True)

        # Apply start / end filters if provided
        if start or end:
            dt_series = pd.to_datetime(df["timestamp"], utc=True)
            if start:
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                df = df[dt_series >= start]
            if end:
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                df = df[dt_series <= end]

        if limit and limit > 0:
            df = df.iloc[-limit:].reset_index(drop=True)

        return df

