"""API request and response schemas."""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    """Input payload for the /ask endpoint."""

    question: str = Field(..., min_length=1, description="User natural language query.")


class AskResponse(BaseModel):
    """Output payload for the /ask endpoint."""

    answer: str
    used_tool: str | None = None
    data: dict | None = None
    error: str | None = None
