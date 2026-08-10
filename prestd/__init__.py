"""
prestd - Modern, typed Python client library and microservice toolkit for pREST (prestd) on PostgreSQL.
"""

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
    raise_for_prest_status,
)
from prestd.integrations.fastapi import (
    get_async_prest_client,
    get_prest_client,
    setup_prest_exception_handlers,
)
from prestd.models import (
    ColumnInfo,
    DatabaseInfo,
    HealthResponse,
    PaginatedResponse,
    PrestConfig,
    PrestSettings,
    SchemaInfo,
    TableInfo,
)
from prestd.query import QueryBuilder
from prestd.schema import (
    AsyncDatabaseAccessor,
    AsyncSchemaAccessor,
    DatabaseAccessor,
    SchemaAccessor,
)
from prestd.sql import AsyncSqlQueries, SqlQueries
from prestd.table import AsyncTableAccessor, TableAccessor

__version__ = "0.1.0"

__all__ = [
    "AsyncDatabaseAccessor",
    "AsyncPrestClient",
    "AsyncSchemaAccessor",
    "AsyncSqlQueries",
    "AsyncTableAccessor",
    "ColumnInfo",
    "DatabaseAccessor",
    "DatabaseInfo",
    "HealthResponse",
    "PaginatedResponse",
    "PrestAuthenticationError",
    "PrestClient",
    "PrestConfig",
    "PrestConflictError",
    "PrestConnectionError",
    "PrestError",
    "PrestNotFoundError",
    "PrestServerError",
    "PrestSettings",
    "PrestTimeoutError",
    "PrestValidationError",
    "QueryBuilder",
    "SchemaAccessor",
    "SchemaInfo",
    "SqlQueries",
    "TableAccessor",
    "TableInfo",
    "get_async_prest_client",
    "get_prest_client",
    "raise_for_prest_status",
    "setup_prest_exception_handlers",
]
