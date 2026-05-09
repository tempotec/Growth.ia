"""Unit tests for local cache settings."""

from __future__ import annotations

from app.core.cache_config import get_cache_settings


def test_get_cache_settings_uses_defaults_when_env_is_absent() -> None:
    settings = get_cache_settings()

    assert settings.local_cache_db_path == "data/glacier_cache.db"
    assert settings.cache_refresh_minutes == 60
    assert settings.data_source_mode == "bigquery_direct"
    assert settings.auto_sync_cache_on_startup is False
    assert settings.auto_sync_cache_interval is False


def test_get_cache_settings_reads_data_source_mode_from_env(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DATA_SOURCE_MODE", "local_cache")

    settings = get_cache_settings()

    assert settings.data_source_mode == "local_cache"


def test_get_cache_settings_reads_auto_sync_flags_from_env(
    monkeypatch,
) -> None:
    monkeypatch.setenv("AUTO_SYNC_CACHE_ON_STARTUP", "true")
    monkeypatch.setenv("AUTO_SYNC_CACHE_INTERVAL", "true")
    monkeypatch.setenv("CACHE_REFRESH_MINUTES", "15")

    settings = get_cache_settings()

    assert settings.auto_sync_cache_on_startup is True
    assert settings.auto_sync_cache_interval is True
    assert settings.cache_refresh_minutes == 15
