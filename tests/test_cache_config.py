"""Unit tests for local cache settings."""

from __future__ import annotations

from app.core.cache_config import get_cache_settings


def test_get_cache_settings_uses_defaults_when_env_is_absent() -> None:
    settings = get_cache_settings()

    assert settings.local_cache_db_path == "data/glacier_cache.db"
    assert settings.cache_refresh_minutes == 10
    assert settings.data_source_mode == "bigquery_direct"


def test_get_cache_settings_reads_data_source_mode_from_env(
    monkeypatch,
) -> None:
    monkeypatch.setenv("DATA_SOURCE_MODE", "local_cache")

    settings = get_cache_settings()

    assert settings.data_source_mode == "local_cache"
