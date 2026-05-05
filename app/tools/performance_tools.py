"""Performance-related tools for Glacier AI V1."""

from __future__ import annotations

from datetime import date

from app.repositories.analytics_repository import AnalyticsRepository


def get_channel_performance_summary(
    start_date: date | None = None,
    end_date: date | None = None,
    repository: AnalyticsRepository | None = None,
) -> list[dict]:
    """Return channel performance metrics for the requested period."""

    analytics_repository = repository or AnalyticsRepository()
    return analytics_repository.get_channel_performance_summary(
        start_date=start_date,
        end_date=end_date,
    )
