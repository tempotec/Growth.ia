"""Unit tests for the local SQLite cache repository."""

from __future__ import annotations

import sqlite3
from datetime import datetime

import pytest

from app.repositories.local_cache_repository import (
    LocalCacheRepository,
    LocalCacheSnapshotNotFoundError,
)
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
        {"name": "cache_sync_runs"},
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
                "start_date": "2026-04-06",
                "end_date": "2026-05-05",
                "traffic_source": "Organic",
                "users": 900,
                "converted_users": 60,
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
                "start_date": "2026-04-06",
                "end_date": "2026-05-05",
                "traffic_source": "Organic",
                "users": 1000,
                "converted_users": 80,
                "orders": 80,
                "revenue": 5500.0,
                "conversion_rate": 0.08,
            },
            {
                "start_date": "2026-04-06",
                "end_date": "2026-05-05",
                "traffic_source": "Search",
                "users": 700,
                "converted_users": 42,
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
            "start_date": "2026-04-06",
            "end_date": "2026-05-05",
            "traffic_source": "Organic",
            "users": 1000,
            "converted_users": 80,
            "orders": 80,
            "revenue": 5500.0,
            "conversion_rate": 0.08,
        },
        {
            "snapshot_at": latest_snapshot_at.isoformat(),
            "start_date": "2026-04-06",
            "end_date": "2026-05-05",
            "traffic_source": "Search",
            "users": 700,
            "converted_users": 42,
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
            {
                "start_date": "2026-04-06",
                "end_date": "2026-05-05",
                "traffic_source": "Organic",
                "revenue": 5500.0,
            },
            {
                "start_date": "2026-04-06",
                "end_date": "2026-05-05",
                "traffic_source": "Search",
                "revenue": 3200.0,
            },
        ],
        snapshot_at,
    )
    repository.write_users_by_source_snapshot(
        [
            {
                "start_date": "2026-04-06",
                "end_date": "2026-05-05",
                "traffic_source": "Organic",
                "users": 1000,
            },
            {
                "start_date": "2026-04-06",
                "end_date": "2026-05-05",
                "traffic_source": "Search",
                "users": 700,
            },
        ],
        snapshot_at,
    )

    assert repository.get_latest_revenue_by_source_snapshot() == [
        {
            "snapshot_at": snapshot_at.isoformat(),
            "start_date": "2026-04-06",
            "end_date": "2026-05-05",
            "traffic_source": "Organic",
            "revenue": 5500.0,
        },
        {
            "snapshot_at": snapshot_at.isoformat(),
            "start_date": "2026-04-06",
            "end_date": "2026-05-05",
            "traffic_source": "Search",
            "revenue": 3200.0,
        },
    ]
    assert repository.get_latest_users_by_source_snapshot() == [
        {
            "snapshot_at": snapshot_at.isoformat(),
            "start_date": "2026-04-06",
            "end_date": "2026-05-05",
            "traffic_source": "Organic",
            "users": 1000,
        },
        {
            "snapshot_at": snapshot_at.isoformat(),
            "start_date": "2026-04-06",
            "end_date": "2026-05-05",
            "traffic_source": "Search",
            "users": 700,
        },
    ]


def test_local_cache_repository_returns_contract_compatible_payloads(
    sqlite_service: SQLiteService,
) -> None:
    repository = LocalCacheRepository(sqlite_service=sqlite_service)
    snapshot_at = datetime(2026, 5, 5, 13, 0, 0)

    repository.write_channel_performance_snapshot(
        [
            {
                "start_date": "2026-04-06",
                "end_date": "2026-05-05",
                "traffic_source": "Organic",
                "users": 1000,
                "converted_users": 80,
                "orders": 80,
                "revenue": 5500.0,
                "conversion_rate": 0.08,
            }
        ],
        snapshot_at,
    )
    repository.write_revenue_by_source_snapshot(
        [
            {
                "start_date": "2026-04-06",
                "end_date": "2026-05-05",
                "traffic_source": "Organic",
                "revenue": 5500.0,
            }
        ],
        snapshot_at,
    )
    repository.write_users_by_source_snapshot(
        [
            {
                "start_date": "2026-04-06",
                "end_date": "2026-05-05",
                "traffic_source": "Organic",
                "users": 1000,
            }
        ],
        snapshot_at,
    )

    assert repository.get_users_by_source("Organic") == {
        "traffic_source": "Organic",
        "users": 1000,
        "start_date": "2026-04-06",
        "end_date": "2026-05-05",
    }
    assert repository.get_revenue_by_source() == [
        {
            "traffic_source": "Organic",
            "revenue": 5500.0,
            "start_date": "2026-04-06",
            "end_date": "2026-05-05",
        }
    ]
    assert repository.get_channel_performance_summary() == [
        {
            "traffic_source": "Organic",
            "users": 1000,
            "converted_users": 80,
            "orders": 80,
            "revenue": 5500.0,
            "conversion_rate": 0.08,
            "start_date": "2026-04-06",
            "end_date": "2026-05-05",
        }
    ]


def test_local_cache_revenue_by_source_uses_channel_performance_snapshot(
    sqlite_service: SQLiteService,
) -> None:
    repository = LocalCacheRepository(sqlite_service=sqlite_service)
    snapshot_at = datetime(2026, 5, 5, 13, 0, 0)

    repository.write_channel_performance_snapshot(
        [
            {
                "start_date": "2026-04-06",
                "end_date": "2026-05-05",
                "traffic_source": "Search",
                "users": 1000,
                "converted_users": 80,
                "orders": 90,
                "revenue": 5500.0,
                "conversion_rate": 0.08,
            }
        ],
        snapshot_at,
    )
    repository.write_revenue_by_source_snapshot(
        [
            {
                "start_date": "2026-04-06",
                "end_date": "2026-05-05",
                "traffic_source": "Search",
                "revenue": 9999.0,
            }
        ],
        snapshot_at,
    )

    assert repository.get_revenue_by_source() == [
        {
            "traffic_source": "Search",
            "revenue": 5500.0,
            "start_date": "2026-04-06",
            "end_date": "2026-05-05",
        }
    ]


def test_local_cache_repository_raises_when_snapshot_is_missing(
    sqlite_service: SQLiteService,
) -> None:
    repository = LocalCacheRepository(sqlite_service=sqlite_service)

    with pytest.raises(LocalCacheSnapshotNotFoundError) as exc_info:
        repository.get_channel_performance_summary()

    assert "Run the cache sync first" in str(exc_info.value)


def test_local_cache_repository_raises_for_missing_requested_date_range(
    sqlite_service: SQLiteService,
) -> None:
    repository = LocalCacheRepository(sqlite_service=sqlite_service)
    snapshot_at = datetime(2026, 5, 5, 13, 0, 0)
    repository.write_channel_performance_snapshot(
        [
            {
                "start_date": "2026-04-06",
                "end_date": "2026-05-05",
                "traffic_source": "Organic",
                "users": 1000,
                "converted_users": 80,
                "orders": 90,
                "revenue": 5500.0,
                "conversion_rate": 0.08,
            }
        ],
        snapshot_at,
    )

    with pytest.raises(LocalCacheSnapshotNotFoundError) as exc_info:
        repository.get_revenue_by_source(
            start_date=datetime(2026, 4, 1).date(),
            end_date=datetime(2026, 4, 30).date(),
        )

    assert "requested date range" in str(exc_info.value)


def test_local_cache_repository_records_latest_sync_status(
    sqlite_service: SQLiteService,
) -> None:
    repository = LocalCacheRepository(sqlite_service=sqlite_service)
    started_at = datetime(2026, 5, 5, 14, 0, 0)
    completed_at = datetime(2026, 5, 5, 14, 0, 30)
    snapshot_at = datetime(2026, 5, 5, 14, 0, 10)

    repository.record_sync_run(
        started_at=started_at,
        completed_at=completed_at,
        snapshot_at=snapshot_at,
        status="success",
        channel_performance_rows=7,
        revenue_by_source_rows=5,
        users_by_source_rows=7,
    )

    assert repository.get_latest_sync_status() == {
        "started_at": started_at.isoformat(),
        "completed_at": completed_at.isoformat(),
        "snapshot_at": snapshot_at.isoformat(),
        "status": "success",
        "channel_performance_rows": 7,
        "revenue_by_source_rows": 5,
        "users_by_source_rows": 7,
        "error_message": None,
    }
