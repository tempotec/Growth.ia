"""API request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Input payload for the /ask endpoint."""

    question: str = Field(..., min_length=1, description="User natural language query.")


class AskResponse(BaseModel):
    """Output payload for the /ask endpoint."""

    answer: str
    used_tool: str | None = None
    data: dict | list[dict] | None = None
    error: str | None = None


class CacheStatusResponse(BaseModel):
    """Operational status payload for the local cache layer."""

    status: str
    data_source_mode: str
    last_sync_status: str | None = None
    last_snapshot_at: datetime | None = None
    cache_age_minutes: int | None = None
    last_sync_started_at: datetime | None = None
    last_sync_completed_at: datetime | None = None
    last_sync_error_message: str | None = None
