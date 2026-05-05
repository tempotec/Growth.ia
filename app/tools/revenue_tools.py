"""Revenue-related tools for Glacier AI V1."""

from __future__ import annotations

from datetime import date

from app.services.analytics_read_service import AnalyticsReadService


def get_revenue_by_source(
    start_date: date | None = None,
    end_date: date | None = None,
    repository: AnalyticsReadService | None = None,
) -> list[dict]:
    """Return revenue aggregated by traffic source."""

    analytics_repository = repository or AnalyticsReadService()
    return analytics_repository.get_revenue_by_source(
        start_date=start_date,
        end_date=end_date,
    )
