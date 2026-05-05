"""LLM service wrapper for Glacier AI V1."""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.agent.prompts import (
    ANSWER_SYSTEM_PROMPT,
    PARSE_SYSTEM_PROMPT,
    build_answer_user_prompt,
    build_parse_user_prompt,
)
from app.core.config import get_settings
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

    def parse_question(self, question: str) -> ParsedQuestion:
        """Parse a natural-language question into a structured intent payload."""

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
            return ParsedQuestion.model_validate(payload)
        except Exception as exc:
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
            return self._extract_content(response).strip()
        except Exception as exc:
            raise LLMServiceError("Failed to generate final answer with the configured LLM.") from exc

    @staticmethod
    def _extract_content(response: Any) -> str:
        """Extract the first assistant message content from a completion response."""

        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM response did not include content.")
        return content
