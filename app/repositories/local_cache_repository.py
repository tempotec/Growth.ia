"""Repository for local SQLite-backed analytics snapshots."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.services.sqlite_service import SQLiteService


class LocalCacheRepository:
    """Persist and read local analytics snapshots."""

    def __init__(self, sqlite_service: SQLiteService | None = None) -> None:
        self._sqlite_service = sqlite_service or SQLiteService()
        self._sqlite_service.initialize_schema()

    def write_channel_performance_snapshot(
        self,
        rows: list[dict[str, Any]],
        snapshot_at: datetime,
    ) -> None:
        """Persist a channel performance snapshot."""

        self._sqlite_service.execute_many(
            """
            INSERT INTO channel_performance_snapshot (
                snapshot_at,
                traffic_source,
                users,
                orders,
                revenue,
                conversion_rate
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    snapshot_at.isoformat(),
                    row["traffic_source"],
                    int(row["users"]),
                    int(row["orders"]),
                    float(row["revenue"]),
                    float(row["conversion_rate"]),
                )
                for row in rows
            ],
        )

    def write_revenue_by_source_snapshot(
        self,
        rows: list[dict[str, Any]],
        snapshot_at: datetime,
    ) -> None:
        """Persist a revenue by source snapshot."""

        self._sqlite_service.execute_many(
            """
            INSERT INTO revenue_by_source_snapshot (
                snapshot_at,
                traffic_source,
                revenue
            ) VALUES (?, ?, ?)
            """,
            [
                (
                    snapshot_at.isoformat(),
                    row["traffic_source"],
                    float(row["revenue"]),
                )
                for row in rows
            ],
        )

    def write_users_by_source_snapshot(
        self,
        rows: list[dict[str, Any]],
        snapshot_at: datetime,
    ) -> None:
        """Persist a users by source snapshot."""

        self._sqlite_service.execute_many(
            """
            INSERT INTO users_by_source_snapshot (
                snapshot_at,
                traffic_source,
                users
            ) VALUES (?, ?, ?)
            """,
            [
                (
                    snapshot_at.isoformat(),
                    row["traffic_source"],
                    int(row["users"]),
                )
                for row in rows
            ],
        )

    def get_latest_channel_performance_snapshot(self) -> list[dict[str, Any]]:
        """Return the most recent channel performance snapshot."""

        return self._sqlite_service.fetch_all(
            """
            SELECT
                snapshot_at,
                traffic_source,
                users,
                orders,
                revenue,
                conversion_rate
            FROM channel_performance_snapshot
            WHERE snapshot_at = (
                SELECT MAX(snapshot_at)
                FROM channel_performance_snapshot
            )
            ORDER BY conversion_rate DESC, revenue DESC, traffic_source ASC
            """
        )

    def get_latest_revenue_by_source_snapshot(self) -> list[dict[str, Any]]:
        """Return the most recent revenue by source snapshot."""

        return self._sqlite_service.fetch_all(
            """
            SELECT
                snapshot_at,
                traffic_source,
                revenue
            FROM revenue_by_source_snapshot
            WHERE snapshot_at = (
                SELECT MAX(snapshot_at)
                FROM revenue_by_source_snapshot
            )
            ORDER BY revenue DESC, traffic_source ASC
            """
        )

    def get_latest_users_by_source_snapshot(self) -> list[dict[str, Any]]:
        """Return the most recent users by source snapshot."""

        return self._sqlite_service.fetch_all(
            """
            SELECT
                snapshot_at,
                traffic_source,
                users
            FROM users_by_source_snapshot
            WHERE snapshot_at = (
                SELECT MAX(snapshot_at)
                FROM users_by_source_snapshot
            )
            ORDER BY users DESC, traffic_source ASC
            """
        )
