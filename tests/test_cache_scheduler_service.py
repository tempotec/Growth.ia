"""Unit tests for automatic cache synchronization scheduling."""

from __future__ import annotations

import asyncio
import logging

from app.services.cache_scheduler_service import CacheSchedulerService


class StubCacheSettings:
    """Minimal settings object for scheduler tests."""

    def __init__(
        self,
        *,
        auto_sync_cache_on_startup: bool,
        auto_sync_cache_interval: bool,
        cache_refresh_minutes: int = 60,
    ) -> None:
        self.auto_sync_cache_on_startup = auto_sync_cache_on_startup
        self.auto_sync_cache_interval = auto_sync_cache_interval
        self.cache_refresh_minutes = cache_refresh_minutes


class StubSyncService:
    """Synchronous cache sync stub."""

    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.call_count = 0

    def sync_all(self) -> dict[str, object]:
        self.call_count += 1
        if self.should_fail:
            raise RuntimeError("boom")
        return {"status": "ok"}


def test_scheduler_runs_startup_sync_when_enabled() -> None:
    sync_service = StubSyncService()
    scheduler = CacheSchedulerService(
        cache_sync_service=sync_service,
        cache_settings=StubCacheSettings(
            auto_sync_cache_on_startup=True,
            auto_sync_cache_interval=False,
        ),
    )

    asyncio.run(scheduler.start())

    assert sync_service.call_count == 1
    assert scheduler.is_interval_running is False


def test_scheduler_does_not_raise_when_startup_sync_fails(caplog) -> None:
    sync_service = StubSyncService(should_fail=True)
    scheduler = CacheSchedulerService(
        cache_sync_service=sync_service,
        cache_settings=StubCacheSettings(
            auto_sync_cache_on_startup=True,
            auto_sync_cache_interval=False,
        ),
    )

    with caplog.at_level(logging.WARNING):
        asyncio.run(scheduler.start())

    assert sync_service.call_count == 1
    assert "event=cache_auto_sync_failed" in " ".join(caplog.messages)


def test_scheduler_does_not_start_interval_when_disabled() -> None:
    sync_service = StubSyncService()
    scheduler = CacheSchedulerService(
        cache_sync_service=sync_service,
        cache_settings=StubCacheSettings(
            auto_sync_cache_on_startup=False,
            auto_sync_cache_interval=False,
        ),
    )

    asyncio.run(scheduler.start())

    assert sync_service.call_count == 0
    assert scheduler.is_interval_running is False
