"""
Synchronous and Asynchronous HTTP client implementations for pREST (prestd).
"""

from __future__ import annotations

from typing import Any

import httpx

from prestd.exceptions import (
    PrestConnectionError,
    PrestError,
    PrestTimeoutError,
    PrestValidationError,
    raise_for_prest_status,
)
from prestd.models import (
    DatabaseInfo,
    HealthResponse,
    PrestConfig,
    PrestSettings,
    SchemaInfo,
    TableInfo,
)
from prestd.schema import (
    AsyncDatabaseAccessor,
    AsyncSchemaAccessor,
    DatabaseAccessor,
    SchemaAccessor,
)
from prestd.sql import AsyncSqlQueries, SqlQueries
from prestd.table import AsyncTableAccessor, TableAccessor


def _build_headers(config: PrestConfig) -> dict[str, str]:
    """Construct HTTP headers including authentication and user-defined headers."""
    headers: dict[str, str] = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    headers.update(config.headers)

    if config.api_key:
        prefix = config.token_prefix
        val = f"{prefix}{config.api_key}" if prefix and not config.api_key.startswith(prefix) else config.api_key
        headers[config.token_header] = val

    return headers


class PrestClient:
    """
    Synchronous client for communicating with a pREST (prestd) PostgreSQL REST server.

    Examples:
        >>> client = PrestClient(base_url="http://localhost:3000", default_database="mydb")
        >>> users_table = client.table("users")
        >>> active_users = users_table.find(users_table.query().filter_eq("status", "active"))
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        default_database: str | None = None,
        default_schema: str = "public",
        api_key: str | None = None,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        config: PrestConfig | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if config:
            self.config = config
        else:
            self.config = PrestConfig(
                base_url=base_url.rstrip("/"),
                default_database=default_database,
                default_schema=default_schema,
                api_key=api_key,
                timeout=timeout,
                headers=headers or {},
            )

        self._own_client = http_client is None
        self._client = http_client or httpx.Client(
            base_url=self.config.base_url.rstrip("/"),
            headers=_build_headers(self.config),
            timeout=self.config.timeout,
        )

        self.sql = SqlQueries(self)

    @classmethod
    def from_env(cls, **overrides: Any) -> PrestClient:
        """Create a PrestClient using environment variables (PREST_* prefix)."""
        settings = PrestSettings()
        cfg = settings.to_config()
        for k, v in overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cls(config=cfg)

    @classmethod
    def from_settings(cls, settings: PrestSettings, **overrides: Any) -> PrestClient:
        """Create a PrestClient from a PrestSettings instance."""
        cfg = settings.to_config()
        for k, v in overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cls(config=cfg)

    def __enter__(self) -> PrestClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close the underlying HTTP client session if owned."""
        if self._own_client:
            self._client.close()

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request with error handling and status code verification."""
        clean_path = f"/{path.lstrip('/')}"
        try:
            resp = self._client.request(
                method=method,
                url=clean_path,
                params=params,
                json=json_data,
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise PrestTimeoutError(f"Request to pREST timed out: {exc}") from exc
        except httpx.NetworkError as exc:
            raise PrestConnectionError(f"Failed to connect to pREST server at {self.config.base_url}: {exc}") from exc
        except httpx.HTTPError as exc:
            raise PrestError(f"HTTP transport error during pREST request: {exc}") from exc

        if not resp.is_success:
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            raise_for_prest_status(resp.status_code, response_body=body)

        return resp

    def health(self) -> HealthResponse:
        """
        Check pREST liveness status.
        
        GET /_health
        """
        resp = self._request("GET", "/_health")
        try:
            data = resp.json()
            if isinstance(data, dict):
                return HealthResponse(
                    status=data.get("status", "UP"),
                    database_connected=True,
                    details=data,
                )
        except Exception:
            pass
        return HealthResponse(status="UP", database_connected=True)

    def ready(self) -> HealthResponse:
        """
        Check pREST readiness status.
        
        GET /_ready
        """
        resp = self._request("GET", "/_ready")
        try:
            data = resp.json()
            if isinstance(data, dict):
                return HealthResponse(
                    status=data.get("status", "UP"),
                    database_connected=True,
                    details=data,
                )
        except Exception:
            pass
        return HealthResponse(status="UP", database_connected=True)

    def databases(self) -> list[DatabaseInfo]:
        """
        List all available databases.
        
        GET /databases
        """
        resp = self._request("GET", "/databases")
        data = resp.json()
        if isinstance(data, list):
            return [DatabaseInfo.model_validate(item) for item in data if isinstance(item, dict)]
        return []

    def schemas(self) -> list[SchemaInfo]:
        """
        List all available schemas.
        
        GET /schemas
        """
        resp = self._request("GET", "/schemas")
        data = resp.json()
        if isinstance(data, list):
            return [SchemaInfo.model_validate(item) for item in data if isinstance(item, dict)]
        return []

    def tables(self) -> list[TableInfo]:
        """
        List all available tables.
        
        GET /tables
        """
        resp = self._request("GET", "/tables")
        data = resp.json()
        if isinstance(data, list):
            return [TableInfo.model_validate(item) for item in data if isinstance(item, dict)]
        return []

    def database(self, database_name: str) -> DatabaseAccessor:
        """Access a specific database."""
        return DatabaseAccessor(client=self, database=database_name)

    def schema(self, schema_name: str = "public", database: str | None = None) -> SchemaAccessor:
        """Access a specific schema within default or given database."""
        db = database or self.config.default_database
        if not db:
            raise PrestValidationError("Database name must be specified or set as default_database in client config")
        return SchemaAccessor(client=self, database=db, schema=schema_name)

    def table(
        self,
        table_name: str,
        database: str | None = None,
        schema: str | None = None,
    ) -> TableAccessor:
        """Access a specific table using default database and schema if not specified."""
        db = database or self.config.default_database
        if not db:
            raise PrestValidationError("Database name must be specified or set as default_database in client config")
        sch = schema or self.config.default_schema
        return TableAccessor(client=self, database=db, schema=sch, table=table_name)


class AsyncPrestClient:
    """
    Asynchronous client for communicating with a pREST (prestd) PostgreSQL REST server.

    Examples:
        >>> async with AsyncPrestClient(base_url="http://localhost:3000", default_database="mydb") as client:
        ...     users = client.table("users")
        ...     result = await users.find()
    """

    def __init__(
        self,
        base_url: str = "http://localhost:3000",
        default_database: str | None = None,
        default_schema: str = "public",
        api_key: str | None = None,
        timeout: float = 30.0,
        headers: dict[str, str] | None = None,
        config: PrestConfig | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if config:
            self.config = config
        else:
            self.config = PrestConfig(
                base_url=base_url.rstrip("/"),
                default_database=default_database,
                default_schema=default_schema,
                api_key=api_key,
                timeout=timeout,
                headers=headers or {},
            )

        self._own_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=self.config.base_url.rstrip("/"),
            headers=_build_headers(self.config),
            timeout=self.config.timeout,
        )

        self.sql = AsyncSqlQueries(self)

    @classmethod
    def from_env(cls, **overrides: Any) -> AsyncPrestClient:
        """Create an AsyncPrestClient using environment variables (PREST_* prefix)."""
        settings = PrestSettings()
        cfg = settings.to_config()
        for k, v in overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cls(config=cfg)

    @classmethod
    def from_settings(cls, settings: PrestSettings, **overrides: Any) -> AsyncPrestClient:
        """Create an AsyncPrestClient from a PrestSettings instance."""
        cfg = settings.to_config()
        for k, v in overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)
        return cls(config=cfg)

    async def __aenter__(self) -> AsyncPrestClient:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the underlying asynchronous HTTP client session if owned."""
        if self._own_client:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_data: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> httpx.Response:
        """Execute an asynchronous HTTP request with error handling."""
        clean_path = f"/{path.lstrip('/')}"
        try:
            resp = await self._client.request(
                method=method,
                url=clean_path,
                params=params,
                json=json_data,
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise PrestTimeoutError(f"Request to pREST timed out: {exc}") from exc
        except httpx.NetworkError as exc:
            raise PrestConnectionError(f"Failed to connect to pREST server at {self.config.base_url}: {exc}") from exc
        except httpx.HTTPError as exc:
            raise PrestError(f"HTTP transport error during pREST request: {exc}") from exc

        if not resp.is_success:
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            raise_for_prest_status(resp.status_code, response_body=body)

        return resp

    async def health(self) -> HealthResponse:
        """Check pREST liveness status asynchronously."""
        resp = await self._request("GET", "/_health")
        try:
            data = resp.json()
            if isinstance(data, dict):
                return HealthResponse(
                    status=data.get("status", "UP"),
                    database_connected=True,
                    details=data,
                )
        except Exception:
            pass
        return HealthResponse(status="UP", database_connected=True)

    async def ready(self) -> HealthResponse:
        """Check pREST readiness probe asynchronously."""
        resp = await self._request("GET", "/_ready")
        try:
            data = resp.json()
            if isinstance(data, dict):
                return HealthResponse(
                    status=data.get("status", "UP"),
                    database_connected=True,
                    details=data,
                )
        except Exception:
            pass
        return HealthResponse(status="UP", database_connected=True)

    async def databases(self) -> list[DatabaseInfo]:
        """List all available databases asynchronously."""
        resp = await self._request("GET", "/databases")
        data = resp.json()
        if isinstance(data, list):
            return [DatabaseInfo.model_validate(item) for item in data if isinstance(item, dict)]
        return []

    async def schemas(self) -> list[SchemaInfo]:
        """List all available schemas asynchronously."""
        resp = await self._request("GET", "/schemas")
        data = resp.json()
        if isinstance(data, list):
            return [SchemaInfo.model_validate(item) for item in data if isinstance(item, dict)]
        return []

    async def tables(self) -> list[TableInfo]:
        """List all available tables asynchronously."""
        resp = await self._request("GET", "/tables")
        data = resp.json()
        if isinstance(data, list):
            return [TableInfo.model_validate(item) for item in data if isinstance(item, dict)]
        return []

    def database(self, database_name: str) -> AsyncDatabaseAccessor:
        """Access a specific database asynchronously."""
        return AsyncDatabaseAccessor(client=self, database=database_name)

    def schema(self, schema_name: str = "public", database: str | None = None) -> AsyncSchemaAccessor:
        """Access a specific schema asynchronously within default or given database."""
        db = database or self.config.default_database
        if not db:
            raise PrestValidationError("Database name must be specified or set as default_database in client config")
        return AsyncSchemaAccessor(client=self, database=db, schema=schema_name)

    def table(
        self,
        table_name: str,
        database: str | None = None,
        schema: str | None = None,
    ) -> AsyncTableAccessor:
        """Access a specific table asynchronously using default database and schema."""
        db = database or self.config.default_database
        if not db:
            raise PrestValidationError("Database name must be specified or set as default_database in client config")
        sch = schema or self.config.default_schema
        return AsyncTableAccessor(client=self, database=db, schema=sch, table=table_name)
