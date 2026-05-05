"""Manual validation script for real BigQuery and OpenAI connectivity."""

from __future__ import annotations

import argparse
import json

from app.core.logging import configure_logging
from app.services.bigquery_service import BigQueryService
from app.services.llm_service import LLMService

BIGQUERY_VALIDATION_QUERY = """
SELECT COUNT(*) AS total
FROM `bigquery-public-data.thelook_ecommerce.users`
"""


def validate_bigquery() -> dict[str, object]:
    """Run a simple query against the public dataset."""

    service = BigQueryService()
    rows = service.run_query(BIGQUERY_VALIDATION_QUERY)
    return {
        "service": "bigquery",
        "status": "ok",
        "result": rows[0] if rows else {},
    }


def validate_openai() -> dict[str, object]:
    """Run a cheap connectivity check against OpenAI."""

    service = LLMService()
    result = service.validate_connectivity()
    return {
        "service": "openai",
        "status": "ok",
        "result": {"reply": result},
    }


def main() -> int:
    """Validate selected external services manually."""

    configure_logging()
    parser = argparse.ArgumentParser(description="Validate Glacier AI real services.")
    parser.add_argument(
        "--service",
        choices=["all", "bigquery", "openai"],
        default="all",
        help="Choose which external dependency to validate.",
    )
    args = parser.parse_args()

    validations = []
    try:
        if args.service in {"all", "bigquery"}:
            validations.append(validate_bigquery())
        if args.service in {"all", "openai"}:
            validations.append(validate_openai())
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=True))
        return 1

    print(json.dumps({"status": "ok", "validations": validations}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
