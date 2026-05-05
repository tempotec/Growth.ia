"""Shared fixtures for the Glacier AI test suite."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def isolate_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate settings resolution between tests."""

    get_settings.cache_clear()
    runtime_dir = Path.cwd() / ".test_runtime"
    runtime_dir.mkdir(exist_ok=True)
    monkeypatch.chdir(runtime_dir)
    for env_var in (
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "GOOGLE_APPLICATION_CREDENTIALS",
    ):
        monkeypatch.delenv(env_var, raising=False)

    yield

    get_settings.cache_clear()


@pytest.fixture
def valid_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Provide a complete set of valid environment variables."""

    env = {
        "OPENAI_API_KEY": "test-openai-key",
        "OPENAI_MODEL": "gpt-4.1-mini",
        "GOOGLE_APPLICATION_CREDENTIALS": "/tmp/fake-service-account.json",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return env


@pytest.fixture
def valid_ask_request_payload() -> dict[str, str]:
    """Return a valid /ask request payload."""

    return {"question": "Qual canal teve melhor performance?"}


@pytest.fixture
def valid_ask_response_payload() -> dict:
    """Return a valid /ask response payload."""

    return {
        "answer": "Organic teve a melhor performance nos ultimos 30 dias.",
        "used_tool": "get_channel_performance_summary",
        "data": {"channels": []},
        "error": None,
    }


@pytest.fixture
def valid_date_range_payload() -> dict[str, str]:
    """Return a valid date range payload."""

    return {"start_date": "2026-04-01", "end_date": "2026-04-30"}


@pytest.fixture
def valid_parsed_question_payload(valid_date_range_payload: dict[str, str]) -> dict:
    """Return a valid parsed question payload."""

    return {
        "intent": "traffic_volume_by_source",
        "traffic_source": "Search",
        "date_range": valid_date_range_payload,
        "needs_data": True,
        "out_of_scope_reason": None,
    }


@pytest.fixture
def valid_channel_performance_payload() -> dict:
    """Return a valid channel performance payload."""

    return {
        "traffic_source": "Organic",
        "users": 1000,
        "orders": 80,
        "revenue": 5500.0,
        "conversion_rate": 0.08,
    }
