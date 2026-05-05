"""Unit tests for application settings."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import get_settings


def test_get_settings_loads_required_environment_variables(
    valid_env: dict[str, str],
) -> None:
    settings = get_settings()

    assert settings.openai_api_key == valid_env["OPENAI_API_KEY"]
    assert (
        settings.google_application_credentials
        == valid_env["GOOGLE_APPLICATION_CREDENTIALS"]
    )
    assert settings.openai_model == valid_env["OPENAI_MODEL"]


def test_get_settings_uses_default_openai_model_when_env_is_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv(
        "GOOGLE_APPLICATION_CREDENTIALS", "/tmp/fake-service-account.json"
    )

    settings = get_settings()

    assert settings.openai_model == "gpt-4.1-mini"


def test_get_settings_fails_when_openai_api_key_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "GOOGLE_APPLICATION_CREDENTIALS", "/tmp/fake-service-account.json"
    )

    with pytest.raises(ValidationError) as exc_info:
        get_settings()

    assert "OPENAI_API_KEY" in str(exc_info.value)


def test_get_settings_fails_when_google_credentials_are_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")

    with pytest.raises(ValidationError) as exc_info:
        get_settings()

    assert "GOOGLE_APPLICATION_CREDENTIALS" in str(exc_info.value)
