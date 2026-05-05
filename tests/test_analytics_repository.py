"""Unit tests for the analytics repository."""

from __future__ import annotations

from datetime import date
from unittest.mock import Mock, patch

import pytest

from app.repositories.analytics_repository import (
    ALLOWED_TRAFFIC_SOURCES,
    AnalyticsRepository,
    AnalyticsRepositoryError,
    InvalidTrafficSourceError,
)


@pytest.fixture
def mock_bigquery_service() -> Mock:
    """Provide a mock BigQuery service for repository tests."""

    return Mock()


@pytest.fixture
def analytics_repository(mock_bigquery_service: Mock) -> AnalyticsRepository:
    """Provide a repository wired to the mock BigQuery service."""

    return AnalyticsRepository(bigquery_service=mock_bigquery_service)


def test_get_users_by_source_normalizes_traffic_source_and_returns_payload(
    analytics_repository: AnalyticsRepository,
    mock_bigquery_service: Mock,
) -> None:
    mock_bigquery_service.run_query.return_value = [{"users": 1234}]

    result = analytics_repository.get_users_by_source(
        traffic_source="search",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    )

    assert result == {
        "traffic_source": "Search",
        "users": 1234,
        "start_date": "2026-04-01",
        "end_date": "2026-04-30",
    }


def test_get_users_by_source_returns_zero_when_query_has_no_rows(
    analytics_repository: AnalyticsRepository,
    mock_bigquery_service: Mock,
) -> None:
    mock_bigquery_service.run_query.return_value = []

    result = analytics_repository.get_users_by_source(
        traffic_source="Organic",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    )

    assert result["users"] == 0


def test_get_users_by_source_rejects_invalid_traffic_source(
    analytics_repository: AnalyticsRepository,
) -> None:
    with pytest.raises(InvalidTrafficSourceError) as exc_info:
        analytics_repository.get_users_by_source("TikTok")

    assert "Allowed values" in str(exc_info.value)


def test_get_users_by_source_uses_default_30_day_window(
    analytics_repository: AnalyticsRepository,
    mock_bigquery_service: Mock,
) -> None:
    mock_bigquery_service.run_query.return_value = [{"users": 50}]
    with patch("app.repositories.analytics_repository.date") as mock_date:
        mock_date.today.return_value = date(2026, 5, 5)
        result = analytics_repository.get_users_by_source("Email")

    assert result["start_date"] == "2026-04-06"
    assert result["end_date"] == "2026-05-05"


def test_get_revenue_by_source_returns_aggregated_payloads(
    analytics_repository: AnalyticsRepository,
    mock_bigquery_service: Mock,
) -> None:
    mock_bigquery_service.run_query.return_value = [
        {"traffic_source": "Organic", "revenue": 12345.67},
        {"traffic_source": "Search", "revenue": 9876.54},
    ]

    result = analytics_repository.get_revenue_by_source(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    )

    assert result == [
        {
            "traffic_source": "Organic",
            "revenue": 12345.67,
            "start_date": "2026-04-01",
            "end_date": "2026-04-30",
        },
        {
            "traffic_source": "Search",
            "revenue": 9876.54,
            "start_date": "2026-04-01",
            "end_date": "2026-04-30",
        },
    ]


def test_get_revenue_by_source_passes_allowed_traffic_sources_to_query(
    analytics_repository: AnalyticsRepository,
    mock_bigquery_service: Mock,
) -> None:
    mock_bigquery_service.run_query.return_value = []

    analytics_repository.get_revenue_by_source(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    )

    query, parameters = mock_bigquery_service.run_query.call_args.args

    assert "order_revenue AS" in query
    assert "ORDER BY revenue DESC" in query
    assert parameters[0].name == "traffic_sources"
    assert parameters[0].values == list(ALLOWED_TRAFFIC_SOURCES)


def test_get_channel_performance_summary_returns_structured_rows(
    analytics_repository: AnalyticsRepository,
    mock_bigquery_service: Mock,
) -> None:
    mock_bigquery_service.run_query.return_value = [
        {
            "traffic_source": "Organic",
            "users": 1000,
            "orders": 80,
            "revenue": 5500.0,
            "conversion_rate": 0.08,
        }
    ]

    result = analytics_repository.get_channel_performance_summary(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    )

    assert result == [
        {
            "traffic_source": "Organic",
            "users": 1000,
            "orders": 80,
            "revenue": 5500.0,
            "conversion_rate": 0.08,
            "start_date": "2026-04-01",
            "end_date": "2026-04-30",
        }
    ]


def test_get_channel_performance_summary_query_uses_safe_aggregations(
    analytics_repository: AnalyticsRepository,
    mock_bigquery_service: Mock,
) -> None:
    mock_bigquery_service.run_query.return_value = []

    analytics_repository.get_channel_performance_summary(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    )

    query, parameters = mock_bigquery_service.run_query.call_args.args

    assert "COUNT(DISTINCT o.order_id) AS orders" in query
    assert "WITH source_dim AS" in query
    assert "order_revenue AS" in query
    assert "SAFE_DIVIDE" in query
    assert parameters[0].values == list(ALLOWED_TRAFFIC_SOURCES)


def test_repository_rejects_inverted_date_range(
    analytics_repository: AnalyticsRepository,
) -> None:
    with pytest.raises(AnalyticsRepositoryError) as exc_info:
        analytics_repository.get_revenue_by_source(
            start_date=date(2026, 5, 1),
            end_date=date(2026, 4, 30),
        )

    assert "start_date must be less than or equal to end_date" in str(exc_info.value)
