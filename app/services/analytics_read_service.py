"""Facade that selects the configured analytics read source."""

from __future__ import annotations

from datetime import date

from app.core.cache_config import DataSourceMode, get_cache_settings
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.local_cache_repository import LocalCacheRepository


class AnalyticsReadService:
    """Read analytics from either BigQuery or the local cache."""

    def __init__(
        self,
        *,
        bigquery_repository: AnalyticsRepository | None = None,
        local_cache_repository: LocalCacheRepository | None = None,
        data_source_mode: DataSourceMode | None = None,
    ) -> None:
        settings = get_cache_settings()
        self._data_source_mode = data_source_mode or settings.data_source_mode
        self._bigquery_repository = bigquery_repository
        self._local_cache_repository = local_cache_repository

    def get_users_by_source(
        self,
        traffic_source: str,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        """Return users acquired from a traffic source in a period."""

        repository = self._get_active_repository()
        return repository.get_users_by_source(
            traffic_source=traffic_source,
            start_date=start_date,
            end_date=end_date,
        )

    def get_revenue_by_source(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        """Return revenue aggregated by traffic source for a period."""

        repository = self._get_active_repository()
        return repository.get_revenue_by_source(
            start_date=start_date,
            end_date=end_date,
        )

    def get_channel_performance_summary(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict]:
        """Return users, orders, revenue, and conversion rate by traffic source."""

        repository = self._get_active_repository()
        return repository.get_channel_performance_summary(
            start_date=start_date,
            end_date=end_date,
        )

    def _get_active_repository(self):
        """Return the configured analytics read source."""

        if self._data_source_mode == "local_cache":
            if self._local_cache_repository is None:
                self._local_cache_repository = LocalCacheRepository()
            return self._local_cache_repository
        if self._bigquery_repository is None:
            self._bigquery_repository = AnalyticsRepository()
        return self._bigquery_repository
