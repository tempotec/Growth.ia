"""Small SQLite access layer for local analytics snapshots."""

from __future__ import annotations

import sqlite3
from contextlib import nullcontext
from pathlib import Path
from typing import Any

from app.core.cache_config import get_cache_settings

SCHEMA_STATEMENTS = """
CREATE TABLE IF NOT EXISTS channel_performance_snapshot (
    snapshot_at TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    traffic_source TEXT NOT NULL,
    users INTEGER NOT NULL,
    orders INTEGER NOT NULL,
    revenue REAL NOT NULL,
    conversion_rate REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS revenue_by_source_snapshot (
    snapshot_at TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    traffic_source TEXT NOT NULL,
    revenue REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS users_by_source_snapshot (
    snapshot_at TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    traffic_source TEXT NOT NULL,
    users INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_channel_performance_snapshot_at
ON channel_performance_snapshot (snapshot_at);

CREATE INDEX IF NOT EXISTS idx_revenue_by_source_snapshot_at
ON revenue_by_source_snapshot (snapshot_at);

CREATE INDEX IF NOT EXISTS idx_users_by_source_snapshot_at
ON users_by_source_snapshot (snapshot_at);
"""

REQUIRED_TEXT_COLUMNS = {
    "channel_performance_snapshot": ("start_date", "end_date"),
    "revenue_by_source_snapshot": ("start_date", "end_date"),
    "users_by_source_snapshot": ("start_date", "end_date"),
}


class SQLiteService:
    """Thin wrapper around sqlite3 for snapshot persistence."""

    def __init__(
        self,
        database_path: Path | str | None = None,
        connection: sqlite3.Connection | None = None,
    ) -> None:
        settings = get_cache_settings()
        self._database_path = database_path or settings.resolved_local_cache_db_path
        self._connection = connection
        if self._connection is not None:
            self._connection.row_factory = sqlite3.Row

    @property
    def database_path(self) -> Path | str:
        """Return the SQLite database path."""

        return self._database_path

    def initialize_schema(self) -> None:
        """Create the local cache database and required tables."""

        if self._connection is None and isinstance(self._database_path, Path):
            self._database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection_context() as connection:
            connection.executescript(SCHEMA_STATEMENTS)
            self._ensure_required_columns(connection)
            connection.commit()

    def execute_many(self, statement: str, rows: list[tuple[Any, ...]]) -> None:
        """Execute a parameterized statement against many rows."""

        with self._connection_context() as connection:
            connection.executemany(statement, rows)
            connection.commit()

    def fetch_all(
        self,
        statement: str,
        parameters: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:
        """Return all rows from a query as dictionaries."""

        with self._connection_context() as connection:
            cursor = connection.execute(statement, parameters)
            return [dict(row) for row in cursor.fetchall()]

    def _connection_context(self):
        """Return a managed connection context."""

        if self._connection is not None:
            return nullcontext(self._connection)
        return self._connect()

    def _connect(self) -> sqlite3.Connection:
        """Open a SQLite connection configured for dictionary-like rows."""

        connection = sqlite3.connect(self._database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_required_columns(self, connection: sqlite3.Connection) -> None:
        """Add newer required columns when opening an older cache database."""

        for table_name, column_names in REQUIRED_TEXT_COLUMNS.items():
            existing_columns = {
                row["name"]
                for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
            }
            for column_name in column_names:
                if column_name not in existing_columns:
                    connection.execute(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} TEXT"
                    )
