"""Manual sync entrypoint for the local analytics cache."""

from __future__ import annotations

import json

from app.core.logging import configure_logging
from app.services.cache_sync_service import CacheSyncService


def main() -> int:
    """Sync BigQuery-backed analytics snapshots into SQLite."""

    configure_logging()
    service = CacheSyncService()

    try:
        result = service.sync_all()
    except Exception as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, ensure_ascii=True))
        return 1

    print(json.dumps({"status": "ok", "result": result}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
