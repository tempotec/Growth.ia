"""Unit tests for the analytics read source selector."""

from __future__ import annotations

from datetime import date
from unittest.mock import Mock

import pytest

from app.repositories.local_cache_repository import LocalCacheSnapshotNotFoundError
from app.services.analytics_read_service import AnalyticsReadService


def test_analytics_read_service_uses_bigquery_direct_mode() -> None:
    bigquery_repository = Mock()
    bigquery_repository.get_channel_performance_summary.return_value = [
        {
            "traffic_source": "Organic",
            "users": 1000,
            "converted_users": 80,
            "orders": 90,
            "revenue": 5500.0,
            "conversion_rate": 0.08,
            "start_date": "2026-04-06",
            "end_date": "2026-05-05",
        }
    ]
    local_cache_repository = Mock()

    service = AnalyticsReadService(
        bigquery_repository=bigquery_repository,
        local_cache_repository=local_cache_repository,
        data_source_mode="bigquery_direct",
    )

    result = service.get_revenue_by_source(
        start_date=date(2026, 4, 6),
        end_date=date(2026, 5, 5),
    )

    assert result[0]["traffic_source"] == "Organic"
    bigquery_repository.get_channel_performance_summary.assert_called_once_with(
        start_date=date(2026, 4, 6),
        end_date=date(2026, 5, 5),
    )
    bigquery_repository.get_revenue_by_source.assert_not_called()
    local_cache_repository.get_revenue_by_source.assert_not_called()


def test_analytics_read_service_uses_local_cache_mode() -> None:
    bigquery_repository = Mock()
    local_cache_repository = Mock()
    local_cache_repository.get_channel_performance_summary.return_value = [
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

    service = AnalyticsReadService(
        bigquery_repository=bigquery_repository,
        local_cache_repository=local_cache_repository,
        data_source_mode="local_cache",
    )

    result = service.get_channel_performance_summary()

    assert result[0]["conversion_rate"] == 0.08
    local_cache_repository.get_channel_performance_summary.assert_called_once_with(
        start_date=None,
        end_date=None,
    )
    bigquery_repository.get_channel_performance_summary.assert_not_called()


def test_analytics_read_service_filters_channel_performance_by_source() -> None:
    bigquery_repository = Mock()
    bigquery_repository.get_channel_performance_summary.return_value = [
        {
            "traffic_source": "Email",
            "users": 168,
            "converted_users": 5,
            "orders": 513,
            "revenue": 44577.74,
            "conversion_rate": 0.03,
            "start_date": "2026-04-08",
            "end_date": "2026-05-07",
        },
        {
            "traffic_source": "Facebook",
            "users": 204,
            "converted_users": 6,
            "orders": 612,
            "revenue": 52615.84,
            "conversion_rate": 0.0294,
            "start_date": "2026-04-08",
            "end_date": "2026-05-07",
        },
    ]

    service = AnalyticsReadService(
        bigquery_repository=bigquery_repository,
        data_source_mode="bigquery_direct",
    )

    result = service.get_channel_performance_by_source("facebook")

    assert result["traffic_source"] == "Facebook"
    assert result["revenue"] == 52615.84


def test_analytics_read_service_surfaces_missing_local_snapshot_error() -> None:
    bigquery_repository = Mock()
    local_cache_repository = Mock()
    local_cache_repository.get_users_by_source.side_effect = (
        LocalCacheSnapshotNotFoundError("No local cache snapshot is available yet.")
    )

    service = AnalyticsReadService(
        bigquery_repository=bigquery_repository,
        local_cache_repository=local_cache_repository,
        data_source_mode="local_cache",
    )

    with pytest.raises(LocalCacheSnapshotNotFoundError) as exc_info:
        service.get_users_by_source("Search")

    assert "No local cache snapshot" in str(exc_info.value)
