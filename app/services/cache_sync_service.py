"""Sync BigQuery analytics snapshots into the local SQLite cache."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.core.analytics_metrics import derive_revenue_by_source
from app.core.logging import get_logger, log_event
from app.repositories.analytics_repository import (
    ALLOWED_TRAFFIC_SOURCES,
    AnalyticsRepository,
)
from app.repositories.local_cache_repository import LocalCacheRepository


class CacheSyncService:
    """Materialize BigQuery-backed analytics views into SQLite snapshots."""

    def __init__(
        self,
        analytics_repository: AnalyticsRepository | None = None,
        local_cache_repository: LocalCacheRepository | None = None,
    ) -> None:
        self._analytics_repository = analytics_repository or AnalyticsRepository()
        self._local_cache_repository = local_cache_repository or LocalCacheRepository()
        self._logger = get_logger(__name__)

    def sync_all(self, snapshot_at: datetime | None = None) -> dict[str, object]:
        """Sync all supported analytical views into the local cache."""

        sync_started_at = datetime.now(UTC)
        effective_snapshot_at = snapshot_at or sync_started_at
        log_event(
            self._logger,
            logging.INFO,
            "cache_sync_started",
            snapshot_at=effective_snapshot_at.isoformat(),
        )

        try:
            channel_performance = self._analytics_repository.get_channel_performance_summary()
            revenue_by_source = derive_revenue_by_source(channel_performance)
            users_by_source = [
                self._analytics_repository.get_users_by_source(traffic_source)
                for traffic_source in ALLOWED_TRAFFIC_SOURCES
            ]

            self._local_cache_repository.write_channel_performance_snapshot(
                channel_performance,
                effective_snapshot_at,
            )
            self._local_cache_repository.write_revenue_by_source_snapshot(
                revenue_by_source,
                effective_snapshot_at,
            )
            self._local_cache_repository.write_users_by_source_snapshot(
                users_by_source,
                effective_snapshot_at,
            )

            result = {
                "snapshot_at": effective_snapshot_at.isoformat(),
                "channel_performance_rows": len(channel_performance),
                "revenue_by_source_rows": len(revenue_by_source),
                "users_by_source_rows": len(users_by_source),
            }
            self._local_cache_repository.record_sync_run(
                started_at=sync_started_at,
                completed_at=datetime.now(UTC),
                snapshot_at=effective_snapshot_at,
                status="success",
                channel_performance_rows=result["channel_performance_rows"],
                revenue_by_source_rows=result["revenue_by_source_rows"],
                users_by_source_rows=result["users_by_source_rows"],
            )
            log_event(
                self._logger,
                logging.INFO,
                "cache_sync_completed",
                **result,
            )
            return result
        except Exception as exc:
            self._local_cache_repository.record_sync_run(
                started_at=sync_started_at,
                completed_at=datetime.now(UTC),
                snapshot_at=effective_snapshot_at,
                status="failed",
                error_message=str(exc),
            )
            log_event(
                self._logger,
                logging.ERROR,
                "cache_sync_failed",
                snapshot_at=effective_snapshot_at.isoformat(),
                error_type=type(exc).__name__,
            )
            raise
