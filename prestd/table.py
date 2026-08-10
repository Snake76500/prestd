"""
Table-level accessors for CRUD operations on pREST PostgreSQL tables.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, overload

from pydantic import BaseModel

from prestd.models import PaginatedResponse, TableInfo
from prestd.query import QueryBuilder

if TYPE_CHECKING:
    from prestd.client import AsyncPrestClient, PrestClient

ModelT = TypeVar("ModelT", bound=BaseModel)


def _prepare_payload(data: dict[str, Any] | BaseModel | list[dict[str, Any] | BaseModel]) -> Any:
    """Normalize Pydantic models or dicts to JSON-compatible data."""
    if isinstance(data, BaseModel):
        return data.model_dump(exclude_unset=True, mode="json")
    if isinstance(data, list):
        return [
            item.model_dump(exclude_unset=True, mode="json") if isinstance(item, BaseModel) else item
            for item in data
        ]
    return data


def _extract_params(query: QueryBuilder | dict[str, Any] | None) -> dict[str, Any]:
    """Extract params dict from a QueryBuilder or raw dict."""
    if query is None:
        return {}
    if isinstance(query, QueryBuilder):
        return query.to_params()
    return query


def _parse_items(items: list[dict[str, Any]], model: type[ModelT] | None) -> list[Any]:
    """Parse list of dicts to list of Pydantic models if a model type is specified."""
    if model is None:
        return items
    return [model.model_validate(item) for item in items]


def _parse_item(item: dict[str, Any] | None, model: type[ModelT] | None) -> Any:
    """Parse single dict to Pydantic model if specified."""
    if item is None:
        return None
    if model is None:
        return item
    return model.model_validate(item)


class TableAccessor:
    """
    Synchronous CRUD and query interface for a specific PostgreSQL table via pREST.
    
    Examples:
        >>> users = client.table("users")
        >>> all_users = users.find()
        >>> active_users = users.find(users.query().filter_eq("status", "active"), model=UserModel)
        >>> user = users.get(1, model=UserModel)
    """

    def __init__(
        self,
        client: PrestClient,
        database: str,
        schema: str,
        table: str,
    ) -> None:
        self._client = client
        self.database = database
        self.schema = schema
        self.table = table
        self.endpoint_path = f"/{database}/{schema}/{table}"

    def query(self) -> QueryBuilder:
        """Create a new QueryBuilder instance for this table."""
        return QueryBuilder()

    @overload
    def find(
        self,
        query: QueryBuilder | dict[str, Any] | None = ...,
        *,
        model: type[ModelT],
    ) -> list[ModelT]: ...

    @overload
    def find(
        self,
        query: QueryBuilder | dict[str, Any] | None = ...,
        *,
        model: None = None,
    ) -> list[dict[str, Any]]: ...

    def find(
        self,
        query: QueryBuilder | dict[str, Any] | None = None,
        *,
        model: type[ModelT] | None = None,
    ) -> list[Any]:
        """
        Fetch records matching query conditions.
        
        GET /{database}/{schema}/{table}
        """
        params = _extract_params(query)
        resp = self._client._request("GET", self.endpoint_path, params=params)
        data = resp.json()
        raw_items: list[dict[str, Any]] = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
        return _parse_items(raw_items, model)

    @overload
    def find_one(
        self,
        query: QueryBuilder | dict[str, Any] | None = ...,
        *,
        model: type[ModelT],
    ) -> ModelT | None: ...

    @overload
    def find_one(
        self,
        query: QueryBuilder | dict[str, Any] | None = ...,
        *,
        model: None = None,
    ) -> dict[str, Any] | None: ...

    def find_one(
        self,
        query: QueryBuilder | dict[str, Any] | None = None,
        *,
        model: type[ModelT] | None = None,
    ) -> Any | None:
        """Fetch the first record matching query conditions."""
        if isinstance(query, QueryBuilder):
            q = query.paginate(page=1, page_size=1)
        elif query is None:
            q = QueryBuilder().paginate(page=1, page_size=1)
        else:
            q = QueryBuilder()
            for k, v in query.items():
                q = q.filter(k, value=v)
            q = q.paginate(page=1, page_size=1)

        results = self.find(q, model=model)
        return results[0] if results else None

    @overload
    def get(
        self,
        pk_value: Any,
        pk_field: str = "id",
        *,
        model: type[ModelT],
    ) -> ModelT | None: ...

    @overload
    def get(
        self,
        pk_value: Any,
        pk_field: str = "id",
        *,
        model: None = None,
    ) -> dict[str, Any] | None: ...

    def get(
        self,
        pk_value: Any,
        pk_field: str = "id",
        *,
        model: type[ModelT] | None = None,
    ) -> Any | None:
        """Get a single record by its primary key."""
        q = QueryBuilder().filter_eq(pk_field, pk_value).paginate(page=1, page_size=1)
        return self.find_one(q, model=model)

    @overload
    def insert(
        self,
        data: dict[str, Any] | BaseModel,
        *,
        model: type[ModelT],
    ) -> ModelT: ...

    @overload
    def insert(
        self,
        data: dict[str, Any] | BaseModel,
        *,
        model: None = None,
    ) -> dict[str, Any]: ...

    def insert(
        self,
        data: dict[str, Any] | BaseModel,
        *,
        model: type[ModelT] | None = None,
    ) -> Any:
        """
        Insert a new record into the table.
        
        POST /{database}/{schema}/{table}
        """
        payload = _prepare_payload(data)
        resp = self._client._request("POST", self.endpoint_path, json_data=payload)
        res_data = resp.json()
        return _parse_item(res_data, model)

    @overload
    def insert_many(
        self,
        items: list[dict[str, Any] | BaseModel],
        *,
        model: type[ModelT],
    ) -> list[ModelT]: ...

    @overload
    def insert_many(
        self,
        items: list[dict[str, Any] | BaseModel],
        *,
        model: None = None,
    ) -> list[dict[str, Any]]: ...

    def insert_many(
        self,
        items: list[dict[str, Any] | BaseModel],
        *,
        model: type[ModelT] | None = None,
    ) -> list[Any]:
        """
        Batch insert records into the table.
        
        POST /{database}/{schema}/{table}/batch
        """
        payload = _prepare_payload(items)
        resp = self._client._request("POST", f"{self.endpoint_path}/batch", json_data=payload)
        res_data = resp.json()
        raw_items: list[dict[str, Any]] = res_data if isinstance(res_data, list) else ([res_data] if isinstance(res_data, dict) else [])
        return _parse_items(raw_items, model)

    def update(
        self,
        data: dict[str, Any] | BaseModel,
        query: QueryBuilder | dict[str, Any] | None = None,
        method: str = "PATCH",
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Update records matching filter criteria.
        
        PATCH or PUT /{database}/{schema}/{table}?filter...
        """
        params = _extract_params(query)
        payload = _prepare_payload(data)
        resp = self._client._request(method.upper(), self.endpoint_path, params=params, json_data=payload)
        return resp.json()

    def update_by_id(
        self,
        pk_value: Any,
        data: dict[str, Any] | BaseModel,
        pk_field: str = "id",
        method: str = "PATCH",
    ) -> dict[str, Any]:
        """Update a single record by primary key."""
        q = QueryBuilder().filter_eq(pk_field, pk_value)
        res = self.update(data=data, query=q, method=method)
        return res[0] if isinstance(res, list) and res else res  # type: ignore

    def delete(
        self,
        query: QueryBuilder | dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Delete records matching filter criteria.
        
        DELETE /{database}/{schema}/{table}?filter...
        """
        params = _extract_params(query)
        resp = self._client._request("DELETE", self.endpoint_path, params=params)
        return resp.json()

    def delete_by_id(self, pk_value: Any, pk_field: str = "id") -> dict[str, Any]:
        """Delete a single record by primary key."""
        q = QueryBuilder().filter_eq(pk_field, pk_value)
        res = self.delete(query=q)
        return res[0] if isinstance(res, list) and res else res  # type: ignore

    def count(self, query: QueryBuilder | dict[str, Any] | None = None) -> int:
        """Count records matching filter criteria."""
        if isinstance(query, QueryBuilder):
            q = query.count("*")
        elif query is None:
            q = QueryBuilder().count("*")
        else:
            q = QueryBuilder()
            for k, v in query.items():
                q = q.filter(k, value=v)
            q = q.count("*")

        res = self.find(q)
        if res and isinstance(res[0], dict) and "count" in res[0]:
            return int(res[0]["count"])
        return len(res)

    def paginate(
        self,
        query: QueryBuilder | dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 10,
        *,
        model: type[ModelT] | None = None,
    ) -> PaginatedResponse[Any]:
        """Fetch a paginated slice with total count metadata."""
        if isinstance(query, QueryBuilder):
            base_q = query._clone()
        elif query is None:
            base_q = QueryBuilder()
        else:
            base_q = QueryBuilder()
            for k, v in query.items():
                base_q = base_q.filter(k, value=v)

        total_count = self.count(base_q)
        paged_q = base_q.paginate(page=page, page_size=page_size)
        items = self.find(paged_q, model=model)
        return PaginatedResponse.create(items=items, page=page, page_size=page_size, total_count=total_count)

    def show(self) -> TableInfo:
        """
        Inspect table schema and column structure.
        
        GET /show/{database}/{schema}/{table}
        """
        path = f"/show/{self.database}/{self.schema}/{self.table}"
        resp = self._client._request("GET", path)
        data = resp.json()
        if isinstance(data, list):
            return TableInfo(table_name=self.table, table_schema=self.schema, columns=data)
        elif isinstance(data, dict):
            return TableInfo.model_validate(data)
        return TableInfo(table_name=self.table, table_schema=self.schema)


class AsyncTableAccessor:
    """
    Asynchronous CRUD and query interface for a specific PostgreSQL table via pREST.
    
    Examples:
        >>> users = client.table("users")
        >>> all_users = await users.find()
        >>> active_users = await users.find(users.query().filter_eq("status", "active"), model=UserModel)
        >>> user = await users.get(1, model=UserModel)
    """

    def __init__(
        self,
        client: AsyncPrestClient,
        database: str,
        schema: str,
        table: str,
    ) -> None:
        self._client = client
        self.database = database
        self.schema = schema
        self.table = table
        self.endpoint_path = f"/{database}/{schema}/{table}"

    def query(self) -> QueryBuilder:
        """Create a new QueryBuilder instance for this table."""
        return QueryBuilder()

    @overload
    async def find(
        self,
        query: QueryBuilder | dict[str, Any] | None = ...,
        *,
        model: type[ModelT],
    ) -> list[ModelT]: ...

    @overload
    async def find(
        self,
        query: QueryBuilder | dict[str, Any] | None = ...,
        *,
        model: None = None,
    ) -> list[dict[str, Any]]: ...

    async def find(
        self,
        query: QueryBuilder | dict[str, Any] | None = None,
        *,
        model: type[ModelT] | None = None,
    ) -> list[Any]:
        """Fetch records matching query conditions asynchronously."""
        params = _extract_params(query)
        resp = await self._client._request("GET", self.endpoint_path, params=params)
        data = resp.json()
        raw_items: list[dict[str, Any]] = data if isinstance(data, list) else ([data] if isinstance(data, dict) else [])
        return _parse_items(raw_items, model)

    @overload
    async def find_one(
        self,
        query: QueryBuilder | dict[str, Any] | None = ...,
        *,
        model: type[ModelT],
    ) -> ModelT | None: ...

    @overload
    async def find_one(
        self,
        query: QueryBuilder | dict[str, Any] | None = ...,
        *,
        model: None = None,
    ) -> dict[str, Any] | None: ...

    async def find_one(
        self,
        query: QueryBuilder | dict[str, Any] | None = None,
        *,
        model: type[ModelT] | None = None,
    ) -> Any | None:
        """Fetch the first record matching query conditions asynchronously."""
        if isinstance(query, QueryBuilder):
            q = query.paginate(page=1, page_size=1)
        elif query is None:
            q = QueryBuilder().paginate(page=1, page_size=1)
        else:
            q = QueryBuilder()
            for k, v in query.items():
                q = q.filter(k, value=v)
            q = q.paginate(page=1, page_size=1)

        results = await self.find(q, model=model)
        return results[0] if results else None

    @overload
    async def get(
        self,
        pk_value: Any,
        pk_field: str = "id",
        *,
        model: type[ModelT],
    ) -> ModelT | None: ...

    @overload
    async def get(
        self,
        pk_value: Any,
        pk_field: str = "id",
        *,
        model: None = None,
    ) -> dict[str, Any] | None: ...

    async def get(
        self,
        pk_value: Any,
        pk_field: str = "id",
        *,
        model: type[ModelT] | None = None,
    ) -> Any | None:
        """Get a single record by primary key asynchronously."""
        q = QueryBuilder().filter_eq(pk_field, pk_value).paginate(page=1, page_size=1)
        return await self.find_one(q, model=model)

    @overload
    async def insert(
        self,
        data: dict[str, Any] | BaseModel,
        *,
        model: type[ModelT],
    ) -> ModelT: ...

    @overload
    async def insert(
        self,
        data: dict[str, Any] | BaseModel,
        *,
        model: None = None,
    ) -> dict[str, Any]: ...

    async def insert(
        self,
        data: dict[str, Any] | BaseModel,
        *,
        model: type[ModelT] | None = None,
    ) -> Any:
        """Insert a new record into the table asynchronously."""
        payload = _prepare_payload(data)
        resp = await self._client._request("POST", self.endpoint_path, json_data=payload)
        res_data = resp.json()
        return _parse_item(res_data, model)

    @overload
    async def insert_many(
        self,
        items: list[dict[str, Any] | BaseModel],
        *,
        model: type[ModelT],
    ) -> list[ModelT]: ...

    @overload
    async def insert_many(
        self,
        items: list[dict[str, Any] | BaseModel],
        *,
        model: None = None,
    ) -> list[dict[str, Any]]: ...

    async def insert_many(
        self,
        items: list[dict[str, Any] | BaseModel],
        *,
        model: type[ModelT] | None = None,
    ) -> list[Any]:
        """Batch insert records into the table asynchronously."""
        payload = _prepare_payload(items)
        resp = await self._client._request("POST", f"{self.endpoint_path}/batch", json_data=payload)
        res_data = resp.json()
        raw_items: list[dict[str, Any]] = res_data if isinstance(res_data, list) else ([res_data] if isinstance(res_data, dict) else [])
        return _parse_items(raw_items, model)

    async def update(
        self,
        data: dict[str, Any] | BaseModel,
        query: QueryBuilder | dict[str, Any] | None = None,
        method: str = "PATCH",
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Update records matching filter criteria asynchronously."""
        params = _extract_params(query)
        payload = _prepare_payload(data)
        resp = await self._client._request(method.upper(), self.endpoint_path, params=params, json_data=payload)
        return resp.json()

    async def update_by_id(
        self,
        pk_value: Any,
        data: dict[str, Any] | BaseModel,
        pk_field: str = "id",
        method: str = "PATCH",
    ) -> dict[str, Any]:
        """Update a single record by primary key asynchronously."""
        q = QueryBuilder().filter_eq(pk_field, pk_value)
        res = await self.update(data=data, query=q, method=method)
        return res[0] if isinstance(res, list) and res else res  # type: ignore

    async def delete(
        self,
        query: QueryBuilder | dict[str, Any] | None = None,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Delete records matching filter criteria asynchronously."""
        params = _extract_params(query)
        resp = await self._client._request("DELETE", self.endpoint_path, params=params)
        return resp.json()

    async def delete_by_id(self, pk_value: Any, pk_field: str = "id") -> dict[str, Any]:
        """Delete a single record by primary key asynchronously."""
        q = QueryBuilder().filter_eq(pk_field, pk_value)
        res = await self.delete(query=q)
        return res[0] if isinstance(res, list) and res else res  # type: ignore

    async def count(self, query: QueryBuilder | dict[str, Any] | None = None) -> int:
        """Count records matching filter criteria asynchronously."""
        if isinstance(query, QueryBuilder):
            q = query.count("*")
        elif query is None:
            q = QueryBuilder().count("*")
        else:
            q = QueryBuilder()
            for k, v in query.items():
                q = q.filter(k, value=v)
            q = q.count("*")

        res = await self.find(q)
        if res and isinstance(res[0], dict) and "count" in res[0]:
            return int(res[0]["count"])
        return len(res)

    async def paginate(
        self,
        query: QueryBuilder | dict[str, Any] | None = None,
        page: int = 1,
        page_size: int = 10,
        *,
        model: type[ModelT] | None = None,
    ) -> PaginatedResponse[Any]:
        """Fetch a paginated slice with total count metadata asynchronously."""
        if isinstance(query, QueryBuilder):
            base_q = query._clone()
        elif query is None:
            base_q = QueryBuilder()
        else:
            base_q = QueryBuilder()
            for k, v in query.items():
                base_q = base_q.filter(k, value=v)

        total_count = await self.count(base_q)
        paged_q = base_q.paginate(page=page, page_size=page_size)
        items = await self.find(paged_q, model=model)
        return PaginatedResponse.create(items=items, page=page, page_size=page_size, total_count=total_count)

    async def show(self) -> TableInfo:
        """Inspect table schema and structure asynchronously."""
        path = f"/show/{self.database}/{self.schema}/{self.table}"
        resp = await self._client._request("GET", path)
        data = resp.json()
        if isinstance(data, list):
            return TableInfo(table_name=self.table, table_schema=self.schema, columns=data)
        elif isinstance(data, dict):
            return TableInfo.model_validate(data)
        return TableInfo(table_name=self.table, table_schema=self.schema)
