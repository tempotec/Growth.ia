"""Application entrypoint for Glacier AI V1."""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import os
from time import perf_counter
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.logging import (
    clear_request_id,
    configure_logging,
    elapsed_ms,
    generate_request_id,
    get_logger,
    log_event,
    set_request_id,
)
from app.services.cache_scheduler_service import CacheSchedulerService


DEFAULT_CORS_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


def _get_cors_origins() -> list[str]:
    """Return normalized CORS origins from a comma-separated env var."""

    configured_origins = os.getenv("BACKEND_CORS_ORIGINS", DEFAULT_CORS_ORIGINS)
    return [origin.strip() for origin in configured_origins.split(",") if origin.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start and stop background services for the API lifecycle."""

    cache_scheduler = CacheSchedulerService()
    app.state.cache_scheduler = cache_scheduler
    await cache_scheduler.start()
    try:
        yield
    finally:
        await cache_scheduler.stop()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    configure_logging()
    app = FastAPI(title="Glacier AI Backend", version="0.1.0", lifespan=lifespan)
    logger = get_logger(__name__)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_get_cors_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or generate_request_id()
        request.state.request_id = request_id
        set_request_id(request_id)
        request_start = perf_counter()
        log_event(
            logger,
            logging.INFO,
            "http_request_started",
            method=request.method,
            path=request.url.path,
        )
        try:
            response = await call_next(request)
        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "http_request_failed",
                method=request.method,
                path=request.url.path,
                duration_ms=elapsed_ms(request_start),
                error_type=type(exc).__name__,
            )
            clear_request_id()
            raise

        response.headers["X-Request-ID"] = request_id
        log_event(
            logger,
            logging.INFO,
            "http_request_completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=elapsed_ms(request_start),
        )
        clear_request_id()
        return response

    app.include_router(router)

    @app.exception_handler(FastAPIHTTPException)
    async def http_exception_handler(request, exc: FastAPIHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"error": exc.detail}
        return JSONResponse(status_code=exc.status_code, content=detail)

    return app


app = create_app()
