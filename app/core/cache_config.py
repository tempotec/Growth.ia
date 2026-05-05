"""Settings for the local analytics cache."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CacheSettings(BaseSettings):
    """Application settings for the local SQLite cache."""

    local_cache_db_path: str = Field(
        default="data/glacier_cache.db",
        alias="LOCAL_CACHE_DB_PATH",
    )
    cache_refresh_minutes: int = Field(default=10, alias="CACHE_REFRESH_MINUTES")

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
