"""Repository for local SQLite-backed analytics snapshots."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from typing import Any, get_args

from app.core.analytics_metrics import derive_revenue_by_source
from app.schemas.analytics import AllowedTrafficSource
from app.services.sqlite_service import SQLiteService

ALLOWED_TRAFFIC_SOURCES = tuple(get_args(AllowedTrafficSource))
TRAFFIC_SOURCE_MAP = {source.lower(): source for source in ALLOWED_TRAFFIC_SOURCES}


class LocalCacheRepositoryError(Exception):
    """Base exception for local cache reads and writes."""


class LocalCacheSnapshotNotFoundError(LocalCacheRepositoryError):
    """Raised when the local cache does not contain a usable snapshot."""


class InvalidTrafficSourceError(LocalCacheRepositoryError):
    """Raised when a traffic source is not supported in the V1 scope."""


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
                start_date,
                end_date,
                traffic_source,
                users,
                converted_users,
                orders,
                revenue,
                conversion_rate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    snapshot_at.isoformat(),
                    row["start_date"],
                    row["end_date"],
                    row["traffic_source"],
                    int(row["users"]),
                    int(row["converted_users"]),
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
                start_date,
                end_date,
                traffic_source,
                revenue
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    snapshot_at.isoformat(),
                    row["start_date"],
                    row["end_date"],
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
                start_date,
                end_date,
                traffic_source,
                users
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    snapshot_at.isoformat(),
                    row["start_date"],
                    row["end_date"],
                    row["traffic_source"],
                    int(row["users"]),
                )
                for row in rows
            ],
        )

    def record_sync_run(
        self,
        *,
        started_at: datetime,
        completed_at: datetime,
        status: str,
        snapshot_at: datetime | None = None,
        channel_performance_rows: int = 0,
        revenue_by_source_rows: int = 0,
        users_by_source_rows: int = 0,
        error_message: str | None = None,
    ) -> None:
        """Persist one sync execution record."""

        self._sqlite_service.execute_many(
            """
            INSERT INTO cache_sync_runs (
                started_at,
                completed_at,
                snapshot_at,
                status,
                channel_performance_rows,
                revenue_by_source_rows,
                users_by_source_rows,
                error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    started_at.isoformat(),
                    completed_at.isoformat(),
                    snapshot_at.isoformat() if snapshot_at is not None else None,
                    status,
                    channel_performance_rows,
                    revenue_by_source_rows,
                    users_by_source_rows,
                    error_message,
                )
            ],
        )

    def get_latest_sync_status(self) -> dict[str, Any]:
        """Return the most recent sync execution record."""

        rows = self._fetch_all_or_raise_snapshot_not_found(
            """
            SELECT
                started_at,
                completed_at,
                snapshot_at,
                status,
                channel_performance_rows,
                revenue_by_source_rows,
                users_by_source_rows,
                error_message
            FROM cache_sync_runs
            ORDER BY started_at DESC
            LIMIT 1
            """
        )
        if not rows:
            raise LocalCacheSnapshotNotFoundError(
                "No cache sync has been recorded yet. Run the cache sync first."
            )
        row = rows[0]
        return {
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
            "snapshot_at": row["snapshot_at"],
            "status": row["status"],
            "channel_performance_rows": int(row["channel_performance_rows"]),
            "revenue_by_source_rows": int(row["revenue_by_source_rows"]),
            "users_by_source_rows": int(row["users_by_source_rows"]),
            "error_message": row["error_message"],
        }

    def get_channel_performance_summary(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Return the most recent cached channel performance snapshot."""

        rows = self._fetch_latest_rows(
            """
            SELECT
                snapshot_at,
                start_date,
                end_date,
                traffic_source,
                users,
                converted_users,
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
        self._ensure_matching_date_range(rows, start_date, end_date)
        return [
            {
                "traffic_source": row["traffic_source"],
                "users": int(row["users"]),
                "converted_users": _read_converted_users(row),
                "orders": int(row["orders"]),
                "revenue": float(row["revenue"]),
                "conversion_rate": _validate_conversion_rate(row["conversion_rate"]),
                "start_date": row["start_date"],
                "end_date": row["end_date"],
            }
            for row in rows
        ]

    def get_revenue_by_source(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        """Return cached revenue projected from channel performance."""

        return derive_revenue_by_source(
            self.get_channel_performance_summary(
                start_date=start_date,
                end_date=end_date,
            )
        )

    def get_users_by_source(
        self,
        traffic_source: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Return the most recent cached users by source snapshot."""

        normalized_source = self._normalize_traffic_source(traffic_source)
        rows = self._fetch_latest_rows(
            """
            SELECT
                snapshot_at,
                start_date,
                end_date,
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
        self._ensure_matching_date_range(rows, start_date, end_date)
        for row in rows:
            if row["traffic_source"] == normalized_source:
                return {
                    "traffic_source": normalized_source,
                    "users": int(row["users"]),
                    "start_date": row["start_date"],
                    "end_date": row["end_date"],
                }

        return {
            "traffic_source": normalized_source,
            "users": 0,
            "start_date": rows[0]["start_date"],
            "end_date": rows[0]["end_date"],
        }

    def get_latest_channel_performance_snapshot(self) -> list[dict[str, Any]]:
        """Return raw rows from the most recent channel performance snapshot."""

        return self._fetch_latest_rows(
            """
            SELECT
                snapshot_at,
                start_date,
                end_date,
                traffic_source,
                users,
                converted_users,
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
        """Return raw rows from the most recent revenue by source snapshot."""

        return self._fetch_latest_rows(
            """
            SELECT
                snapshot_at,
                start_date,
                end_date,
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
        """Return raw rows from the most recent users by source snapshot."""

        return self._fetch_latest_rows(
            """
            SELECT
                snapshot_at,
                start_date,
                end_date,
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

    def _fetch_latest_rows(self, statement: str) -> list[dict[str, Any]]:
        """Read the most recent snapshot rows for a materialized view."""

        rows = self._fetch_all_or_raise_snapshot_not_found(statement)
        if not rows:
            raise LocalCacheSnapshotNotFoundError(
                "No local cache snapshot is available yet. Run the cache sync first."
            )
        return rows

    def _fetch_all_or_raise_snapshot_not_found(
        self,
        statement: str,
        parameters: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:
        """Treat missing cache tables as an empty local-cache state."""

        try:
            return self._sqlite_service.fetch_all(statement, parameters)
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc).lower():
                raise
            raise LocalCacheSnapshotNotFoundError(
                "The local cache schema is not initialized yet."
            ) from exc

    def _ensure_matching_date_range(
        self,
        rows: list[dict[str, Any]],
        start_date: date | None,
        end_date: date | None,
    ) -> None:
        """Ensure the cached snapshot matches the requested date range."""

        if start_date is None and end_date is None:
            return

        snapshot_start_date = rows[0]["start_date"]
        snapshot_end_date = rows[0]["end_date"]
        requested_start_date = start_date.isoformat() if start_date is not None else None
        requested_end_date = end_date.isoformat() if end_date is not None else None

        if (
            requested_start_date is not None
            and requested_start_date != snapshot_start_date
        ) or (
            requested_end_date is not None and requested_end_date != snapshot_end_date
        ):
            raise LocalCacheSnapshotNotFoundError(
                "No local cache snapshot is available for the requested date range."
            )

    def _normalize_traffic_source(self, traffic_source: str) -> str:
        """Normalize and validate supported traffic source values."""

        normalized = TRAFFIC_SOURCE_MAP.get(traffic_source.strip().lower())
        if normalized is None:
            allowed_values = ", ".join(ALLOWED_TRAFFIC_SOURCES)
            raise InvalidTrafficSourceError(
                f"Unsupported traffic_source. Allowed values: {allowed_values}."
            )
        return normalized


def _read_converted_users(row: dict[str, Any]) -> int:
    """Read converted users, forcing stale cache snapshots to be refreshed."""

    converted_users = row.get("converted_users")
    if converted_users is None:
        raise LocalCacheSnapshotNotFoundError(
            "No local cache snapshot with converted_users is available. "
            "Run the cache sync first."
        )
    return int(converted_users)


def _validate_conversion_rate(value: object) -> float:
    """Return a decimal conversion rate, rejecting order/user ratios."""

    conversion_rate = float(value or 0)
    if conversion_rate < 0 or conversion_rate > 1:
        raise LocalCacheSnapshotNotFoundError(
            "The latest local cache snapshot contains an invalid conversion_rate. "
            "Run the cache sync first."
        )
    return conversion_rate
