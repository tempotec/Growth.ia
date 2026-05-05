"""Tests for local observability helpers and middleware behavior."""

from __future__ import annotations

import logging

from fastapi.testclient import TestClient

from app.core.logging import (
    build_log_message,
    clear_request_id,
    generate_request_id,
    set_request_id,
)
from app.main import create_app


def test_generate_request_id_returns_short_value() -> None:
    request_id = generate_request_id()

    assert isinstance(request_id, str)
    assert len(request_id) == 12


def test_build_log_message_includes_request_id_when_available() -> None:
    set_request_id("abc123request")

    message = build_log_message("event_name", tool_name="get_users_by_source")

    clear_request_id()
    assert "event=event_name" in message
    assert "request_id=abc123request" in message
    assert "tool_name=get_users_by_source" in message


def test_http_middleware_sets_request_id_header() -> None:
    app = create_app()
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_http_middleware_logs_request_lifecycle(caplog) -> None:
    app = create_app()
    client = TestClient(app)

    with caplog.at_level(logging.INFO):
        response = client.get("/health")

    assert response.status_code == 200
    log_text = " ".join(caplog.messages)
    assert "event=http_request_started" in log_text
    assert "event=http_request_completed" in log_text
