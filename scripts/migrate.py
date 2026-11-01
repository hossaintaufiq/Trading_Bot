#!/usr/bin/env python3
"""
NEPTUNE — SQLite Migration Runner

Usage:
  python scripts/migrate.py               # run all pending migrations
  python scripts/migrate.py --status      # show migration status
"""
import argparse
import os
import sqlite3
from datetime import datetime, timezone

MIGRATIONS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "backend", "app", "database", "migrations"
)
DB_PATH = os.path.join(
    os.path.dirname(__file__), "..", "storage", "db", "neptune.db"
)


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def ensure_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
    """)
    conn.commit()


def get_applied_versions(conn: sqlite3.Connection) -> set:
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {row[0] for row in rows}


def run_migrations(status_only: bool = False) -> None:
    if not os.path.isdir(MIGRATIONS_DIR):
        print(f"No migrations directory found at: {MIGRATIONS_DIR}")
        return

    conn = get_connection()
    ensure_migrations_table(conn)
    applied = get_applied_versions(conn)

    migration_files = sorted(
        f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")
    )

    if not migration_files:
        print("No migration files found.")
        return

    for filename in migration_files:
        version = int(filename.split("_")[0])
        if status_only:
            status = "[APPLIED]" if version in applied else "[PENDING]"
            print(f"  {status}  {filename}")
            continue

        if version in applied:
            print(f"  [SKIP]  {filename}")
            continue

        sql_path = os.path.join(MIGRATIONS_DIR, filename)
        with open(sql_path, "r") as f:
            sql = f.read()

        try:
            conn.executescript(sql)
            conn.execute(
                "INSERT INTO schema_migrations (version, filename, applied_at) VALUES (?, ?, ?)",
                (version, filename, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
            print(f"  [OK] applied  {filename}")
        except Exception as exc:
            conn.rollback()
            print(f"  [FAIL]   {filename}: {exc}")
            raise

    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    run_migrations(status_only=args.status)

