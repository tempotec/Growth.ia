"""Unit tests for the cache sync service."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock

from app.repositories.analytics_repository import ALLOWED_TRAFFIC_SOURCES
from app.services.cache_sync_service import CacheSyncService


def test_cache_sync_service_materializes_all_supported_views() -> None:
    analytics_repository = Mock()
    analytics_repository.get_channel_performance_summary.return_value = [
        {
            "traffic_source": "Organic",
            "users": 1000,
            "orders": 80,
            "revenue": 5500.0,
            "conversion_rate": 0.08,
            "start_date": "2026-04-06",
            "end_date": "2026-05-05",
        }
    ]
    analytics_repository.get_revenue_by_source.return_value = [
        {
            "traffic_source": "Organic",
            "revenue": 5500.0,
            "start_date": "2026-04-06",
            "end_date": "2026-05-05",
        }
    ]
    analytics_repository.get_users_by_source.side_effect = [
        {
            "traffic_source": traffic_source,
            "users": index * 10,
            "start_date": "2026-04-06",
            "end_date": "2026-05-05",
        }
        for index, traffic_source in enumerate(ALLOWED_TRAFFIC_SOURCES, start=1)
    ]
    local_cache_repository = Mock()
    snapshot_at = datetime(2026, 5, 5, 15, 0, 0)

    service = CacheSyncService(
        analytics_repository=analytics_repository,
        local_cache_repository=local_cache_repository,
    )

    result = service.sync_all(snapshot_at=snapshot_at)

    analytics_repository.get_channel_performance_summary.assert_called_once_with()
    analytics_repository.get_revenue_by_source.assert_called_once_with()
    assert analytics_repository.get_users_by_source.call_count == len(
        ALLOWED_TRAFFIC_SOURCES
    )
    local_cache_repository.write_channel_performance_snapshot.assert_called_once()
    local_cache_repository.write_revenue_by_source_snapshot.assert_called_once()
    local_cache_repository.write_users_by_source_snapshot.assert_called_once()
    local_cache_repository.record_sync_run.assert_called_once()
    assert result == {
        "snapshot_at": snapshot_at.isoformat(),
        "channel_performance_rows": 1,
        "revenue_by_source_rows": 1,
        "users_by_source_rows": len(ALLOWED_TRAFFIC_SOURCES),
    }


def test_cache_sync_service_queries_users_snapshot_for_every_allowed_source() -> None:
    analytics_repository = Mock()
    analytics_repository.get_channel_performance_summary.return_value = []
    analytics_repository.get_revenue_by_source.return_value = []
    analytics_repository.get_users_by_source.side_effect = [
        {
            "traffic_source": traffic_source,
            "users": 0,
            "start_date": "2026-04-06",
            "end_date": "2026-05-05",
        }
        for traffic_source in ALLOWED_TRAFFIC_SOURCES
    ]
    local_cache_repository = Mock()

    service = CacheSyncService(
        analytics_repository=analytics_repository,
        local_cache_repository=local_cache_repository,
    )

    service.sync_all(snapshot_at=datetime(2026, 5, 5, 15, 5, 0))

    queried_sources = [
        call.args[0] for call in analytics_repository.get_users_by_source.call_args_list
    ]
    assert queried_sources == list(ALLOWED_TRAFFIC_SOURCES)


def test_cache_sync_service_records_failed_sync_runs() -> None:
    analytics_repository = Mock()
    analytics_repository.get_channel_performance_summary.side_effect = RuntimeError("boom")
    local_cache_repository = Mock()
    snapshot_at = datetime(2026, 5, 5, 15, 10, 0)

    service = CacheSyncService(
        analytics_repository=analytics_repository,
        local_cache_repository=local_cache_repository,
    )

    try:
        service.sync_all(snapshot_at=snapshot_at)
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("Expected RuntimeError to be re-raised")

    local_cache_repository.record_sync_run.assert_called_once()
    assert local_cache_repository.record_sync_run.call_args.kwargs["status"] == "failed"
    assert local_cache_repository.record_sync_run.call_args.kwargs["error_message"] == "boom"
