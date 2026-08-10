"""
Framework integrations for prestd (FastAPI, etc.).
"""

from prestd.integrations.fastapi import (
    get_async_prest_client,
    get_prest_client,
    setup_prest_exception_handlers,
)

__all__ = [
    "get_async_prest_client",
    "get_prest_client",
    "setup_prest_exception_handlers",
]
