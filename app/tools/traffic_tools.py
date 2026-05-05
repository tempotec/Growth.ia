"""Traffic-related tools for Glacier AI V1."""

from __future__ import annotations

from datetime import date

from app.services.analytics_read_service import AnalyticsReadService


def get_users_by_source(
    traffic_source: str,
    start_date: date | None = None,
    end_date: date | None = None,
    repository: AnalyticsReadService | None = None,
) -> dict:
    """Return users acquired from a traffic source in a period."""

    analytics_repository = repository or AnalyticsReadService()
    return analytics_repository.get_users_by_source(
        traffic_source=traffic_source,
        start_date=start_date,
        end_date=end_date,
    )
