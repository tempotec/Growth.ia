"""Resilient automatic cache synchronization scheduler."""

from __future__ import annotations

import asyncio
import logging
from contextlib import suppress
from typing import Protocol

from app.core.cache_config import CacheSettings, get_cache_settings
from app.core.logging import get_logger, log_event
from app.services.cache_sync_service import CacheSyncService


class CacheSyncServiceProtocol(Protocol):
    """Minimal sync service contract used by the scheduler."""

    def sync_all(self) -> dict[str, object]:
        """Synchronize all cache snapshots."""


class CacheSchedulerService:
    """Run cache sync at startup and optionally on a fixed interval."""

    def __init__(
        self,
        cache_sync_service: CacheSyncServiceProtocol | None = None,
        cache_settings: CacheSettings | None = None,
    ) -> None:
        self._cache_sync_service = cache_sync_service
        self._cache_settings = cache_settings or get_cache_settings()
        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None
        self._logger = get_logger(__name__)

    @property
    def is_interval_running(self) -> bool:
        """Return whether the interval task is currently active."""

        return self._task is not None and not self._task.done()

    async def sync_once_safe(self, reason: str) -> None:
        """Run one sync and never let failures escape to FastAPI startup."""

        log_event(
            self._logger,
            logging.INFO,
            "cache_auto_sync_started",
            reason=reason,
        )
        try:
            result = await asyncio.to_thread(self._get_sync_service().sync_all)
        except Exception as exc:
            log_event(
                self._logger,
                logging.WARNING,
                "cache_auto_sync_failed",
                reason=reason,
                error_type=type(exc).__name__,
            )
            return

        log_event(
            self._logger,
            logging.INFO,
            "cache_auto_sync_completed",
            reason=reason,
            result=result,
        )

    async def start(self) -> None:
        """Start configured startup and interval synchronization."""

        self._ensure_stop_event()
        if self._cache_settings.auto_sync_cache_on_startup:
            await self.sync_once_safe(reason="startup")

        if not self._cache_settings.auto_sync_cache_interval:
            return

        if self.is_interval_running:
            return

        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stop the interval task if one is running."""

        if self._stop_event is not None:
            self._stop_event.set()

        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task
            self._task = None

    async def _run_loop(self) -> None:
        """Run sync repeatedly until the scheduler is stopped."""

        stop_event = self._ensure_stop_event()
        refresh_seconds = max(self._cache_settings.cache_refresh_minutes, 1) * 60

        while not stop_event.is_set():
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=refresh_seconds)
            except asyncio.TimeoutError:
                await self.sync_once_safe(reason="interval")

    def _ensure_stop_event(self) -> asyncio.Event:
        """Create the stop event inside the active event loop."""

        if self._stop_event is None:
            self._stop_event = asyncio.Event()
        return self._stop_event

    def _get_sync_service(self) -> CacheSyncServiceProtocol:
        """Create the BigQuery-backed sync service only when sync is enabled."""

        if self._cache_sync_service is None:
            self._cache_sync_service = CacheSyncService()
        return self._cache_sync_service
