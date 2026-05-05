"""Unit tests for Glacier AI tools."""

from __future__ import annotations

from datetime import date
from unittest.mock import Mock, patch

from app.tools.performance_tools import get_channel_performance_summary
from app.tools.revenue_tools import get_revenue_by_source
from app.tools.traffic_tools import get_users_by_source


def test_get_users_by_source_tool_uses_repository() -> None:
    repository = Mock()
    repository.get_users_by_source.return_value = {"traffic_source": "Search", "users": 10}

    result = get_users_by_source(
        traffic_source="Search",
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
        repository=repository,
    )

    assert result["users"] == 10
    repository.get_users_by_source.assert_called_once()


def test_get_revenue_by_source_tool_uses_repository() -> None:
    repository = Mock()
    repository.get_revenue_by_source.return_value = [{"traffic_source": "Organic", "revenue": 50.0}]

    result = get_revenue_by_source(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
        repository=repository,
    )

    assert result[0]["traffic_source"] == "Organic"
    repository.get_revenue_by_source.assert_called_once()


def test_get_channel_performance_summary_tool_uses_repository() -> None:
    repository = Mock()
    repository.get_channel_performance_summary.return_value = [
        {"traffic_source": "Organic", "conversion_rate": 0.08}
    ]

    result = get_channel_performance_summary(
        start_date=date(2026, 4, 1),
        end_date=date(2026, 4, 30),
        repository=repository,
    )

    assert result[0]["conversion_rate"] == 0.08
    repository.get_channel_performance_summary.assert_called_once()


def test_tools_default_to_analytics_read_service_without_changing_contract() -> None:
    service = Mock()
    service.get_users_by_source.return_value = {"traffic_source": "Search", "users": 10}

    with patch("app.tools.traffic_tools.AnalyticsReadService", return_value=service):
        result = get_users_by_source("Search")

    assert result["users"] == 10
    service.get_users_by_source.assert_called_once_with(
        traffic_source="Search",
        start_date=None,
        end_date=None,
    )
