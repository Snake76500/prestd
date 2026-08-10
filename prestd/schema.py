"""
Database and Schema hierarchy accessors for pREST.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from prestd.models import SchemaInfo, TableInfo
from prestd.table import AsyncTableAccessor, TableAccessor

if TYPE_CHECKING:
    from prestd.client import AsyncPrestClient, PrestClient


class SchemaAccessor:
    """Synchronous accessor for a specific PostgreSQL schema."""

    def __init__(self, client: PrestClient, database: str, schema: str) -> None:
        self._client = client
        self.database = database
        self.schema = schema

    def table(self, table_name: str) -> TableAccessor:
        """Access a specific table in this schema."""
        return TableAccessor(
            client=self._client,
            database=self.database,
            schema=self.schema,
            table=table_name,
        )

    def tables(self) -> list[TableInfo]:
        """List all tables available in this schema."""
        resp = self._client._request("GET", "/tables")
        data = resp.json()
        if isinstance(data, list):
            return [
                TableInfo.model_validate(item)
                for item in data
                if isinstance(item, dict) and item.get("table_schema") == self.schema
            ]
        return []


class DatabaseAccessor:
    """Synchronous accessor for a specific PostgreSQL database."""

    def __init__(self, client: PrestClient, database: str) -> None:
        self._client = client
        self.database = database

    def schema(self, schema_name: str = "public") -> SchemaAccessor:
        """Access a specific schema within this database."""
        return SchemaAccessor(client=self._client, database=self.database, schema=schema_name)

    def table(self, table_name: str, schema_name: str = "public") -> TableAccessor:
        """Shortcut to access a table directly with default or specified schema."""
        return self.schema(schema_name).table(table_name)

    def schemas(self) -> list[SchemaInfo]:
        """List all schemas in this database."""
        resp = self._client._request("GET", "/schemas")
        data = resp.json()
        if isinstance(data, list):
            return [SchemaInfo.model_validate(item) for item in data if isinstance(item, dict)]
        return []


class AsyncSchemaAccessor:
    """Asynchronous accessor for a specific PostgreSQL schema."""

    def __init__(self, client: AsyncPrestClient, database: str, schema: str) -> None:
        self._client = client
        self.database = database
        self.schema = schema

    def table(self, table_name: str) -> AsyncTableAccessor:
        """Access a specific table in this schema asynchronously."""
        return AsyncTableAccessor(
            client=self._client,
            database=self.database,
            schema=self.schema,
            table=table_name,
        )

    async def tables(self) -> list[TableInfo]:
        """List all tables available in this schema asynchronously."""
        resp = await self._client._request("GET", "/tables")
        data = resp.json()
        if isinstance(data, list):
            return [
                TableInfo.model_validate(item)
                for item in data
                if isinstance(item, dict) and item.get("table_schema") == self.schema
            ]
        return []


class AsyncDatabaseAccessor:
    """Asynchronous accessor for a specific PostgreSQL database."""

    def __init__(self, client: AsyncPrestClient, database: str) -> None:
        self._client = client
        self.database = database

    def schema(self, schema_name: str = "public") -> AsyncSchemaAccessor:
        """Access a specific schema within this database asynchronously."""
        return AsyncSchemaAccessor(client=self._client, database=self.database, schema=schema_name)

    def table(self, table_name: str, schema_name: str = "public") -> AsyncTableAccessor:
        """Shortcut to access a table directly asynchronously."""
        return self.schema(schema_name).table(table_name)

    async def schemas(self) -> list[SchemaInfo]:
        """List all schemas in this database asynchronously."""
        resp = await self._client._request("GET", "/schemas")
        data = resp.json()
        if isinstance(data, list):
            return [SchemaInfo.model_validate(item) for item in data if isinstance(item, dict)]
        return []
