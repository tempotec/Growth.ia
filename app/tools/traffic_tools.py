"""Traffic-related tools for Glacier AI V1."""

from __future__ import annotations

from datetime import date

from app.repositories.analytics_repository import AnalyticsRepository


def get_users_by_source(
    traffic_source: str,
    start_date: date | None = None,
    end_date: date | None = None,
    repository: AnalyticsRepository | None = None,
) -> dict:
    """Return users acquired from a traffic source in a period."""

    analytics_repository = repository or AnalyticsRepository()
    return analytics_repository.get_users_by_source(
        traffic_source=traffic_source,
        start_date=start_date,
        end_date=end_date,
    )
