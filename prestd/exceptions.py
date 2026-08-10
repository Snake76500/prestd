"""
Exception hierarchy for the prestd Python library.
"""

from __future__ import annotations

from typing import Any


class PrestError(Exception):
    """Base exception for all prestd client and service errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body

    def __str__(self) -> str:
        if self.status_code:
            return f"[{self.status_code}] {self.message}"
        return self.message


class PrestConnectionError(PrestError):
    """Raised when communication with the pREST server fails (network / transport error)."""


class PrestTimeoutError(PrestError):
    """Raised when a request to the pREST server times out."""


class PrestAuthenticationError(PrestError):
    """Raised when authentication or authorization fails (HTTP 401 Unauthorized or 403 Forbidden)."""


class PrestNotFoundError(PrestError):
    """Raised when a database, schema, table, record, or query is not found (HTTP 404 Not Found)."""


class PrestValidationError(PrestError):
    """Raised when query parameters, payload, or syntax validation fails (HTTP 400 / 422)."""


class PrestConflictError(PrestError):
    """Raised when a unique constraint is violated or a conflict occurs (HTTP 409 Conflict)."""


class PrestServerError(PrestError):
    """Raised when pREST or PostgreSQL encounters an internal server error (HTTP 500+)."""


def raise_for_prest_status(
    status_code: int,
    response_body: Any = None,
    message: str | None = None,
) -> None:
    """
    Evaluate HTTP status code and raise the appropriate PrestError subclass if not successful.
    
    Args:
        status_code: HTTP response status code.
        response_body: Raw or parsed response body from pREST.
        message: Optional custom error message.
    """
    if 200 <= status_code < 300:
        return

    default_msg = f"pREST request failed with HTTP status {status_code}"
    detail: str | None = None
    if isinstance(response_body, dict):
        detail = response_body.get("error") or response_body.get("message") or response_body.get("detail")
    elif isinstance(response_body, str) and response_body.strip():
        detail = response_body.strip()

    msg = f"{message or default_msg}: {detail}" if detail else (message or default_msg)

    if status_code in (401, 403):
        raise PrestAuthenticationError(msg, status_code=status_code, response_body=response_body)
    elif status_code == 404:
        raise PrestNotFoundError(msg, status_code=status_code, response_body=response_body)
    elif status_code in (400, 422):
        raise PrestValidationError(msg, status_code=status_code, response_body=response_body)
    elif status_code == 409:
        raise PrestConflictError(msg, status_code=status_code, response_body=response_body)
    elif status_code >= 500:
        raise PrestServerError(msg, status_code=status_code, response_body=response_body)
    else:
        raise PrestError(msg, status_code=status_code, response_body=response_body)
