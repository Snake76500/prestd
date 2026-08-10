"""
FastAPI dependency injection and error handling helpers for pREST.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator, Generator
from typing import Any

from prestd.client import AsyncPrestClient, PrestClient
from prestd.exceptions import (
    PrestAuthenticationError,
    PrestConflictError,
    PrestConnectionError,
    PrestError,
    PrestNotFoundError,
    PrestServerError,
    PrestTimeoutError,
    PrestValidationError,
)
from prestd.models import PrestSettings

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    FastAPI = Any  # type: ignore[misc,assignment]


_default_settings: PrestSettings | None = None


def get_prest_settings() -> PrestSettings:
    """Singleton getter for PrestSettings loaded from environment variables."""
    global _default_settings
    if _default_settings is None:
        _default_settings = PrestSettings()
    return _default_settings


def set_prest_settings(settings: PrestSettings) -> None:
    """Set custom PrestSettings."""
    global _default_settings
    _default_settings = settings


def get_prest_client() -> Generator[PrestClient, None, None]:
    """
    FastAPI dependency yielding a synchronous PrestClient instance.
    
    Usage:
        @app.get("/users")
        def list_users(client: PrestClient = Depends(get_prest_client)):
            return client.table("users").find()
    """
    settings = get_prest_settings()
    client = PrestClient.from_settings(settings)
    try:
        yield client
    finally:
        client.close()


async def get_async_prest_client() -> AsyncGenerator[AsyncPrestClient, None]:
    """
    FastAPI dependency yielding an asynchronous AsyncPrestClient instance.
    
    Usage:
        @app.get("/users")
        async def list_users(client: AsyncPrestClient = Depends(get_async_prest_client)):
            return await client.table("users").find()
    """
    settings = get_prest_settings()
    client = AsyncPrestClient.from_settings(settings)
    try:
        yield client
    finally:
        await client.aclose()


def setup_prest_exception_handlers(app: FastAPI) -> None:
    """
    Register exception handlers on a FastAPI application to translate PrestErrors into appropriate HTTP responses.
    """
    if not FASTAPI_AVAILABLE:
        raise ImportError("FastAPI is not installed. Install with `pip install prestd[fastapi]`")

    @app.exception_handler(PrestNotFoundError)
    async def not_found_handler(request: Request, exc: PrestNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={"detail": exc.message, "type": "PrestNotFoundError"},
        )

    @app.exception_handler(PrestAuthenticationError)
    async def auth_handler(request: Request, exc: PrestAuthenticationError) -> JSONResponse:
        status = exc.status_code or 401
        return JSONResponse(
            status_code=status,
            content={"detail": exc.message, "type": "PrestAuthenticationError"},
        )

    @app.exception_handler(PrestValidationError)
    async def validation_handler(request: Request, exc: PrestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": exc.message, "type": "PrestValidationError"},
        )

    @app.exception_handler(PrestConflictError)
    async def conflict_handler(request: Request, exc: PrestConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=409,
            content={"detail": exc.message, "type": "PrestConflictError"},
        )

    @app.exception_handler(PrestTimeoutError)
    async def timeout_handler(request: Request, exc: PrestTimeoutError) -> JSONResponse:
        return JSONResponse(
            status_code=504,
            content={"detail": exc.message, "type": "PrestTimeoutError"},
        )

    @app.exception_handler(PrestConnectionError)
    async def connection_handler(request: Request, exc: PrestConnectionError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": exc.message, "type": "PrestConnectionError"},
        )

    @app.exception_handler(PrestServerError)
    async def server_error_handler(request: Request, exc: PrestServerError) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": exc.message, "type": "PrestServerError"},
        )

    @app.exception_handler(PrestError)
    async def base_prest_error_handler(request: Request, exc: PrestError) -> JSONResponse:
        status = exc.status_code if exc.status_code and exc.status_code >= 400 else 500
        return JSONResponse(
            status_code=status,
            content={"detail": exc.message, "type": "PrestError"},
        )
