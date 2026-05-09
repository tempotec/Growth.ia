"""Unit tests for the analytics repository."""

from __future__ import annotations

from datetime import date
from unittest.mock import Mock, patch

import pytest

from app.core.bigquery_tables import ORDER_ITEMS_TABLE, ORDERS_TABLE, USERS_TABLE
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
        {
            "traffic_source": "Organic",
            "users": 1000,
            "converted_users": 80,
            "orders": 90,
            "revenue": 12345.67,
            "conversion_rate": 0.08,
        },
        {
            "traffic_source": "Search",
            "users": 900,
            "converted_users": 70,
            "orders": 80,
            "revenue": 9876.54,
            "conversion_rate": 0.0778,
        },
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


def test_get_revenue_by_source_derives_from_channel_performance_summary(
    analytics_repository: AnalyticsRepository,
    mock_bigquery_service: Mock,
) -> None:
    summary_rows = [
        {
            "traffic_source": "Search",
            "users": 900,
            "converted_users": 70,
            "orders": 80,
            "revenue": 9876.54,
            "conversion_rate": 0.0778,
            "start_date": "2026-04-01",
            "end_date": "2026-04-30",
        }
    ]

    with patch.object(
        analytics_repository,
        "get_channel_performance_summary",
        return_value=summary_rows,
    ) as get_channel_performance_summary:
        result = analytics_repository.get_revenue_by_source(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
        )

    assert result == [
        {
            "traffic_source": "Search",
            "revenue": 9876.54,
            "start_date": "2026-04-01",
            "end_date": "2026-04-30",
        }
    ]
    get_channel_performance_summary.assert_called_once_with(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    )
    mock_bigquery_service.run_query.assert_not_called()


def test_revenue_by_source_matches_channel_performance_revenue(
    analytics_repository: AnalyticsRepository,
    mock_bigquery_service: Mock,
) -> None:
    performance_rows = [
        {
            "traffic_source": "Search",
            "users": 900,
            "converted_users": 70,
            "orders": 80,
            "revenue": 9876.54,
            "conversion_rate": 0.0778,
        },
        {
            "traffic_source": "Organic",
            "users": 1000,
            "converted_users": 80,
            "orders": 90,
            "revenue": 12345.67,
            "conversion_rate": 0.08,
        },
    ]
    mock_bigquery_service.run_query.side_effect = [performance_rows, performance_rows]

    channel_performance = analytics_repository.get_channel_performance_summary(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    )
    revenue_by_source = analytics_repository.get_revenue_by_source(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    )

    performance_revenue = {
        row["traffic_source"]: row["revenue"] for row in channel_performance
    }
    revenue_revenue = {row["traffic_source"]: row["revenue"] for row in revenue_by_source}
    assert performance_revenue["Search"] == revenue_revenue["Search"]
    assert performance_revenue == revenue_revenue


def test_get_channel_performance_summary_returns_structured_rows(
    analytics_repository: AnalyticsRepository,
    mock_bigquery_service: Mock,
) -> None:
    mock_bigquery_service.run_query.return_value = [
        {
            "traffic_source": "Organic",
            "users": 1000,
            "converted_users": 80,
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
            "converted_users": 80,
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

    assert f"FROM `{USERS_TABLE}`" in query
    assert f"INNER JOIN `{ORDERS_TABLE}` AS o" in query
    assert f"FROM `{ORDER_ITEMS_TABLE}`" in query
    assert "users_base AS" in query
    assert "users_agg AS" in query
    assert "converted_users_agg AS" in query
    assert "orders_base AS" in query
    assert "order_agg AS" in query
    assert "converted_users" in query
    assert "COUNT(DISTINCT ob.order_id) AS orders" in query
    assert "WITH source_dim AS" in query
    assert "order_revenue AS" in query
    assert "SAFE_DIVIDE" in query
    assert "AND DATE(o.created_at) BETWEEN @start_date AND @end_date" in query
    assert parameters[0].values == list(ALLOWED_TRAFFIC_SOURCES)


def test_get_channel_performance_summary_rejects_invalid_conversion_rate(
    analytics_repository: AnalyticsRepository,
    mock_bigquery_service: Mock,
) -> None:
    mock_bigquery_service.run_query.return_value = [
        {
            "traffic_source": "Organic",
            "users": 1000,
            "converted_users": 80,
            "orders": 3200,
            "revenue": 5500.0,
            "conversion_rate": 3.2,
        }
    ]

    with pytest.raises(AnalyticsRepositoryError) as exc_info:
        analytics_repository.get_channel_performance_summary(
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 30),
        )

    assert "conversion_rate invalid" in str(exc_info.value)


def test_repository_rejects_inverted_date_range(
    analytics_repository: AnalyticsRepository,
) -> None:
    with pytest.raises(AnalyticsRepositoryError) as exc_info:
        analytics_repository.get_revenue_by_source(
            start_date=date(2026, 5, 1),
            end_date=date(2026, 4, 30),
        )

    assert "start_date must be less than or equal to end_date" in str(exc_info.value)


def test_get_daily_users_by_source_returns_flat_daily_rows(
    analytics_repository: AnalyticsRepository,
    mock_bigquery_service: Mock,
) -> None:
    mock_bigquery_service.run_query.return_value = [
        {"metric_date": date(2026, 4, 1), "traffic_source": "Organic", "visits": 842},
        {"metric_date": date(2026, 4, 1), "traffic_source": "Direct", "visits": 420},
    ]

    result = analytics_repository.get_daily_users_by_source(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    )

    assert result == [
        {"date": "2026-04-01", "channel": "Organic", "visits": 842},
        {"date": "2026-04-01", "channel": "Direct", "visits": 420},
    ]


def test_get_daily_users_by_source_query_groups_by_day_and_source(
    analytics_repository: AnalyticsRepository,
    mock_bigquery_service: Mock,
) -> None:
    mock_bigquery_service.run_query.return_value = []

    analytics_repository.get_daily_users_by_source(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
    )

    query, parameters = mock_bigquery_service.run_query.call_args.args

    assert "DATE(created_at) AS metric_date" in query
    assert "GROUP BY metric_date, traffic_source" in query
    assert "ORDER BY metric_date ASC, traffic_source ASC" in query
    assert parameters[0].values == list(ALLOWED_TRAFFIC_SOURCES)
