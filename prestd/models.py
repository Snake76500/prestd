"""
Data models, response schemas, and configuration models for pREST.
"""

from __future__ import annotations

import math
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

T = TypeVar("T")


class PrestConfig(BaseModel):
    """Configuration settings for connecting to a pREST instance."""

    base_url: str = Field(default="http://localhost:3000", description="Base URL of the pREST server")
    default_database: str | None = Field(default=None, description="Default PostgreSQL database name")
    default_schema: str = Field(default="public", description="Default PostgreSQL schema name")
    api_key: str | None = Field(default=None, description="API Key or Bearer JWT Token for authentication")
    token_header: str = Field(default="Authorization", description="Header name for token (e.g., Authorization or Prest-Token)")
    token_prefix: str = Field(default="Bearer ", description="Prefix for the token header")
    timeout: float = Field(default=30.0, description="HTTP request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of connection retries")
    headers: dict[str, str] = Field(default_factory=dict, description="Additional default HTTP headers")

    model_config = ConfigDict(extra="ignore")


class PrestSettings(BaseSettings):
    """
    12-Factor environment-based settings for microservices using pREST.
    
    Reads from environment variables with prefix `PREST_` (e.g., `PREST_BASE_URL`, `PREST_DEFAULT_DATABASE`).
    """

    prest_base_url: str = Field(default="http://localhost:3000", description="Base URL of the pREST server")
    prest_default_database: str | None = Field(default=None, description="Default PostgreSQL database name")
    prest_default_schema: str = Field(default="public", description="Default PostgreSQL schema name")
    prest_api_key: str | None = Field(default=None, description="API Key or Bearer JWT Token")
    prest_token_header: str = Field(default="Authorization", description="Token header name")
    prest_token_prefix: str = Field(default="Bearer ", description="Token prefix")
    prest_timeout: float = Field(default=30.0, description="HTTP request timeout in seconds")
    prest_max_retries: int = Field(default=3, description="Maximum connection retries")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    def to_config(self) -> PrestConfig:
        """Convert environment settings into a PrestConfig instance."""
        return PrestConfig(
            base_url=self.prest_base_url,
            default_database=self.prest_default_database,
            default_schema=self.prest_default_schema,
            api_key=self.prest_api_key,
            token_header=self.prest_token_header,
            token_prefix=self.prest_token_prefix,
            timeout=self.prest_timeout,
            max_retries=self.prest_max_retries,
        )


class ColumnInfo(BaseModel):
    """Information regarding a PostgreSQL column exposed by pREST."""

    column_name: str
    data_type: str
    is_nullable: str | None = None
    column_default: str | None = None
    character_maximum_length: int | None = None

    model_config = ConfigDict(extra="allow")


class TableInfo(BaseModel):
    """Information regarding a PostgreSQL table in pREST."""

    table_name: str
    table_schema: str | None = "public"
    table_type: str | None = "BASE TABLE"
    columns: list[ColumnInfo] | None = None

    model_config = ConfigDict(extra="allow")


class SchemaInfo(BaseModel):
    """Information regarding a PostgreSQL schema."""

    schema_name: str

    model_config = ConfigDict(extra="allow")


class DatabaseInfo(BaseModel):
    """Information regarding an available PostgreSQL database."""

    datname: str

    model_config = ConfigDict(extra="allow")


class HealthResponse(BaseModel):
    """Health check response status from pREST /_health and /_ready."""

    status: str = "UP"
    database_connected: bool = True
    details: dict[str, Any] | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic wrapper for paginated result sets with pagination metadata."""

    items: list[T]
    page: int
    page_size: int
    total_count: int | None = None
    has_next: bool = False
    total_pages: int | None = None

    @classmethod
    def create(
        cls,
        items: list[T],
        page: int,
        page_size: int,
        total_count: int | None = None,
    ) -> PaginatedResponse[T]:
        """Factory method computing total_pages and has_next."""
        total_pages = math.ceil(total_count / page_size) if total_count is not None and page_size > 0 else None
        has_next = (page < total_pages) if total_pages is not None else (len(items) == page_size)
        return cls(
            items=items,
            page=page,
            page_size=page_size,
            total_count=total_count,
            total_pages=total_pages,
            has_next=has_next,
        )
