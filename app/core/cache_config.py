"""Settings for the local analytics cache."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DataSourceMode = Literal["bigquery_direct", "local_cache"]


class CacheSettings(BaseSettings):
    """Application settings for the local SQLite cache."""

    local_cache_db_path: str = Field(
        default="data/glacier_cache.db",
        alias="LOCAL_CACHE_DB_PATH",
    )
    cache_refresh_minutes: int = Field(default=60, alias="CACHE_REFRESH_MINUTES")
    data_source_mode: DataSourceMode = Field(
        default="bigquery_direct",
        alias="DATA_SOURCE_MODE",
    )
    auto_sync_cache_on_startup: bool = Field(
        default=False,
        alias="AUTO_SYNC_CACHE_ON_STARTUP",
    )
    auto_sync_cache_interval: bool = Field(
        default=False,
        alias="AUTO_SYNC_CACHE_INTERVAL",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def resolved_local_cache_db_path(self) -> Path:
        """Return the resolved cache database path."""

        return Path(self.local_cache_db_path).expanduser().resolve()


@lru_cache
def get_cache_settings() -> CacheSettings:
    """Return cached local cache settings."""

    return CacheSettings()
