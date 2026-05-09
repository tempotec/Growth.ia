"""Performance-related tools for Glacier AI V1."""

from __future__ import annotations

from datetime import date

from app.services.analytics_read_service import AnalyticsReadService


def get_channel_performance_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    repository: AnalyticsReadService | None = None,
) -> list[dict]:
    """Return channel performance metrics for the requested period."""

    analytics_repository = repository or AnalyticsReadService()
    return analytics_repository.get_channel_performance_summary(
        start_date=start_date,
        end_date=end_date,
    )


def get_channel_performance_by_source(
    traffic_source: str,
    start_date: date | None = None,
    end_date: date | None = None,
    repository: AnalyticsReadService | None = None,
) -> dict:
    """Return complete performance metrics for one traffic source."""

    analytics_repository = repository or AnalyticsReadService()
    return analytics_repository.get_channel_performance_by_source(
        traffic_source=traffic_source,
        start_date=start_date,
        end_date=end_date,
    )
