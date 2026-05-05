"""Application entrypoint for Glacier AI V1."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException as FastAPIHTTPException

from app.api.routes import router


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(title="Glacier AI Backend", version="0.1.0")
    app.include_router(router)

    @app.exception_handler(FastAPIHTTPException)
    async def http_exception_handler(request, exc: FastAPIHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, dict) else {"error": exc.detail}
        return JSONResponse(status_code=exc.status_code, content=detail)

    return app


app = create_app()
