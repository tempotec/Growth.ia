"""Unit tests for the local SQLite cache repository."""

from __future__ import annotations

import sqlite3
from datetime import datetime

import pytest

from app.repositories.local_cache_repository import LocalCacheRepository
from app.services.sqlite_service import SQLiteService


@pytest.fixture
def sqlite_service() -> SQLiteService:
    """Return an in-memory SQLite service for deterministic unit tests."""

    connection = sqlite3.connect(":memory:")
    service = SQLiteService(connection=connection)
    yield service
    connection.close()


def test_local_cache_repository_initializes_database_schema(
    sqlite_service: SQLiteService,
) -> None:
    LocalCacheRepository(sqlite_service=sqlite_service)

    tables = sqlite_service.fetch_all(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    )

    assert tables == [
        {"name": "channel_performance_snapshot"},
        {"name": "revenue_by_source_snapshot"},
        {"name": "users_by_source_snapshot"},
    ]


def test_local_cache_repository_reads_latest_snapshot_only(
    sqlite_service: SQLiteService,
) -> None:
    repository = LocalCacheRepository(sqlite_service=sqlite_service)
    older_snapshot_at = datetime(2026, 5, 5, 12, 0, 0)
    latest_snapshot_at = datetime(2026, 5, 5, 12, 10, 0)

    repository.write_channel_performance_snapshot(
        [
            {
                "traffic_source": "Organic",
                "users": 900,
                "orders": 60,
                "revenue": 4000.0,
                "conversion_rate": 0.0667,
            }
        ],
        older_snapshot_at,
    )
    repository.write_channel_performance_snapshot(
        [
            {
                "traffic_source": "Organic",
                "users": 1000,
                "orders": 80,
                "revenue": 5500.0,
                "conversion_rate": 0.08,
            },
            {
                "traffic_source": "Search",
                "users": 700,
                "orders": 42,
                "revenue": 3200.0,
                "conversion_rate": 0.06,
            },
        ],
        latest_snapshot_at,
    )

    latest_rows = repository.get_latest_channel_performance_snapshot()

    assert latest_rows == [
        {
            "snapshot_at": latest_snapshot_at.isoformat(),
            "traffic_source": "Organic",
            "users": 1000,
            "orders": 80,
            "revenue": 5500.0,
            "conversion_rate": 0.08,
        },
        {
            "snapshot_at": latest_snapshot_at.isoformat(),
            "traffic_source": "Search",
            "users": 700,
            "orders": 42,
            "revenue": 3200.0,
            "conversion_rate": 0.06,
        },
    ]


def test_local_cache_repository_writes_and_reads_other_snapshot_views(
    sqlite_service: SQLiteService,
) -> None:
    repository = LocalCacheRepository(sqlite_service=sqlite_service)
    snapshot_at = datetime(2026, 5, 5, 13, 0, 0)

    repository.write_revenue_by_source_snapshot(
        [
            {"traffic_source": "Organic", "revenue": 5500.0},
            {"traffic_source": "Search", "revenue": 3200.0},
        ],
        snapshot_at,
    )
    repository.write_users_by_source_snapshot(
        [
            {"traffic_source": "Organic", "users": 1000},
            {"traffic_source": "Search", "users": 700},
        ],
        snapshot_at,
    )

    assert repository.get_latest_revenue_by_source_snapshot() == [
        {
            "snapshot_at": snapshot_at.isoformat(),
            "traffic_source": "Organic",
            "revenue": 5500.0,
        },
        {
            "snapshot_at": snapshot_at.isoformat(),
            "traffic_source": "Search",
            "revenue": 3200.0,
        },
    ]
    assert repository.get_latest_users_by_source_snapshot() == [
        {
            "snapshot_at": snapshot_at.isoformat(),
            "traffic_source": "Organic",
            "users": 1000,
        },
        {
            "snapshot_at": snapshot_at.isoformat(),
            "traffic_source": "Search",
            "users": 700,
        },
    ]
