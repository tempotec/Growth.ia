"""LLM service wrapper for Glacier AI V1."""

from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from app.agent.prompts import (
    ANSWER_SYSTEM_PROMPT,
    PARSE_SYSTEM_PROMPT,
    build_answer_user_prompt,
    build_parse_user_prompt,
)
from app.core.config import get_settings
from app.core.logging import elapsed_ms, get_logger, log_event, short_text, start_timer
from app.schemas.analytics import ParsedQuestion


class LLMServiceError(Exception):
    """Raised when an LLM interaction fails or returns invalid output."""


class LLMService:
    """Thin wrapper around OpenAI chat completions."""

    def __init__(self, client: OpenAI | None = None, model: str | None = None) -> None:
        settings = None
        if client is None or model is None:
            settings = get_settings()
        self._model = model or settings.openai_model
        self._client = client or OpenAI(api_key=settings.openai_api_key)
        self._logger = get_logger(__name__)

    def parse_question(self, question: str) -> ParsedQuestion:
        """Parse a natural-language question into a structured intent payload."""

        request_start = start_timer()
        log_event(
            self._logger,
            logging.INFO,
            "llm_parse_started",
            model=self._model,
            question_preview=short_text(question),
        )
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": PARSE_SYSTEM_PROMPT},
                    {"role": "user", "content": build_parse_user_prompt(question)},
                ],
            )
            content = self._extract_content(response)
            payload = json.loads(content)
            parsed_question = ParsedQuestion.model_validate(payload)
            log_event(
                self._logger,
                logging.INFO,
                "llm_parse_completed",
                model=self._model,
                duration_ms=elapsed_ms(request_start),
                intent=parsed_question.intent,
            )
            return parsed_question
        except Exception as exc:
            log_event(
                self._logger,
                logging.ERROR,
                "llm_parse_failed",
                model=self._model,
                duration_ms=elapsed_ms(request_start),
                error_type=type(exc).__name__,
            )
            raise LLMServiceError("Failed to parse question with the configured LLM.") from exc

    def generate_answer(
        self,
        *,
        question: str,
        intent: str | None,
        tool_result: Any = None,
        out_of_scope_reason: str | None = None,
    ) -> str:
        """Generate a final business-friendly answer."""

        request_start = start_timer()
        log_event(
            self._logger,
            logging.INFO,
            "llm_answer_started",
            model=self._model,
            intent=intent,
            question_preview=short_text(question),
        )
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                messages=[
                    {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": build_answer_user_prompt(
                            question=question,
                            intent=intent,
                            tool_result=tool_result,
                            out_of_scope_reason=out_of_scope_reason,
                        ),
                    },
                ],
            )
            answer = self._extract_content(response).strip()
            log_event(
                self._logger,
                logging.INFO,
                "llm_answer_completed",
                model=self._model,
                duration_ms=elapsed_ms(request_start),
                intent=intent,
            )
            return answer
        except Exception as exc:
            log_event(
                self._logger,
                logging.ERROR,
                "llm_answer_failed",
                model=self._model,
                duration_ms=elapsed_ms(request_start),
                error_type=type(exc).__name__,
                intent=intent,
            )
            raise LLMServiceError("Failed to generate final answer with the configured LLM.") from exc

    def validate_connectivity(self) -> str:
        """Run a cheap connectivity check against the configured model."""

        request_start = start_timer()
        log_event(
            self._logger,
            logging.INFO,
            "llm_connectivity_check_started",
            model=self._model,
        )
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                max_tokens=10,
                messages=[
                    {
                        "role": "user",
                        "content": "Reply with exactly OK if you can read this message.",
                    }
                ],
            )
            result = self._extract_content(response).strip()
            log_event(
                self._logger,
                logging.INFO,
                "llm_connectivity_check_completed",
                model=self._model,
                duration_ms=elapsed_ms(request_start),
            )
            return result
        except Exception as exc:
            log_event(
                self._logger,
                logging.ERROR,
                "llm_connectivity_check_failed",
                model=self._model,
                duration_ms=elapsed_ms(request_start),
                error_type=type(exc).__name__,
            )
            raise LLMServiceError("Failed to validate OpenAI connectivity.") from exc

    @staticmethod
    def _extract_content(response: Any) -> str:
        """Extract the first assistant message content from a completion response."""

        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM response did not include content.")
        return content
