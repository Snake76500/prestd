"""
Support for executing pREST custom SQL scripts (/_QUERIES/{folder}/{script}).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, overload

from pydantic import BaseModel

if TYPE_CHECKING:
    from prestd.client import AsyncPrestClient, PrestClient

ModelT = TypeVar("ModelT", bound=BaseModel)


def _prepare_payload(data: dict[str, Any] | BaseModel | list[dict[str, Any] | BaseModel] | None) -> Any:
    """Normalize data for JSON request body."""
    if data is None:
        return None
    if isinstance(data, BaseModel):
        return data.model_dump(exclude_unset=True, mode="json")
    if isinstance(data, list):
        return [
            item.model_dump(exclude_unset=True, mode="json") if isinstance(item, BaseModel) else item
            for item in data
        ]
    return data


def _parse_sql_result(data: Any, model: type[ModelT] | None) -> Any:
    """Parse custom SQL query result into Pydantic model if specified."""
    if model is None or data is None:
        return data
    if isinstance(data, list):
        return [model.model_validate(item) for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        return model.model_validate(data)
    return data


class SqlQueries:
    """Synchronous executor for pREST predefined SQL scripts."""

    def __init__(self, client: PrestClient) -> None:
        self._client = client

    @overload
    def get(
        self,
        folder: str,
        script: str,
        params: dict[str, Any] | None = ...,
        *,
        model: type[ModelT],
    ) -> list[ModelT]: ...

    @overload
    def get(
        self,
        folder: str,
        script: str,
        params: dict[str, Any] | None = ...,
        *,
        model: None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]: ...

    def get(
        self,
        folder: str,
        script: str,
        params: dict[str, Any] | None = None,
        *,
        model: type[ModelT] | None = None,
    ) -> Any:
        """
        Execute a custom SQL script via HTTP GET.
        
        Path: /_QUERIES/{folder}/{script}
        """
        path = f"/_QUERIES/{folder}/{script}"
        resp = self._client._request("GET", path, params=params)
        return _parse_sql_result(resp.json(), model)

    @overload
    def post(
        self,
        folder: str,
        script: str,
        data: dict[str, Any] | BaseModel | list[dict[str, Any] | BaseModel] | None = ...,
        params: dict[str, Any] | None = ...,
        *,
        model: type[ModelT],
    ) -> list[ModelT] | ModelT: ...

    @overload
    def post(
        self,
        folder: str,
        script: str,
        data: dict[str, Any] | BaseModel | list[dict[str, Any] | BaseModel] | None = ...,
        params: dict[str, Any] | None = ...,
        *,
        model: None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]: ...

    def post(
        self,
        folder: str,
        script: str,
        data: dict[str, Any] | BaseModel | list[dict[str, Any] | BaseModel] | None = None,
        params: dict[str, Any] | None = None,
        *,
        model: type[ModelT] | None = None,
    ) -> Any:
        """
        Execute a custom SQL script via HTTP POST.
        
        Path: /_QUERIES/{folder}/{script}
        """
        path = f"/_QUERIES/{folder}/{script}"
        payload = _prepare_payload(data)
        resp = self._client._request("POST", path, json_data=payload, params=params)
        return _parse_sql_result(resp.json(), model)

    def put(
        self,
        folder: str,
        script: str,
        data: dict[str, Any] | BaseModel | None = None,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Execute a custom SQL script via HTTP PUT."""
        path = f"/_QUERIES/{folder}/{script}"
        payload = _prepare_payload(data)
        resp = self._client._request("PUT", path, json_data=payload, params=params)
        return resp.json()

    def delete(
        self,
        folder: str,
        script: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Execute a custom SQL script via HTTP DELETE."""
        path = f"/_QUERIES/{folder}/{script}"
        resp = self._client._request("DELETE", path, params=params)
        return resp.json()


class AsyncSqlQueries:
    """Asynchronous executor for pREST predefined SQL scripts."""

    def __init__(self, client: AsyncPrestClient) -> None:
        self._client = client

    @overload
    async def get(
        self,
        folder: str,
        script: str,
        params: dict[str, Any] | None = ...,
        *,
        model: type[ModelT],
    ) -> list[ModelT]: ...

    @overload
    async def get(
        self,
        folder: str,
        script: str,
        params: dict[str, Any] | None = ...,
        *,
        model: None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]: ...

    async def get(
        self,
        folder: str,
        script: str,
        params: dict[str, Any] | None = None,
        *,
        model: type[ModelT] | None = None,
    ) -> Any:
        """Execute a custom SQL script via HTTP GET asynchronously."""
        path = f"/_QUERIES/{folder}/{script}"
        resp = await self._client._request("GET", path, params=params)
        return _parse_sql_result(resp.json(), model)

    @overload
    async def post(
        self,
        folder: str,
        script: str,
        data: dict[str, Any] | BaseModel | list[dict[str, Any] | BaseModel] | None = ...,
        params: dict[str, Any] | None = ...,
        *,
        model: type[ModelT],
    ) -> list[ModelT] | ModelT: ...

    @overload
    async def post(
        self,
        folder: str,
        script: str,
        data: dict[str, Any] | BaseModel | list[dict[str, Any] | BaseModel] | None = ...,
        params: dict[str, Any] | None = ...,
        *,
        model: None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]: ...

    async def post(
        self,
        folder: str,
        script: str,
        data: dict[str, Any] | BaseModel | list[dict[str, Any] | BaseModel] | None = None,
        params: dict[str, Any] | None = None,
        *,
        model: type[ModelT] | None = None,
    ) -> Any:
        """Execute a custom SQL script via HTTP POST asynchronously."""
        path = f"/_QUERIES/{folder}/{script}"
        payload = _prepare_payload(data)
        resp = await self._client._request("POST", path, json_data=payload, params=params)
        return _parse_sql_result(resp.json(), model)

    async def put(
        self,
        folder: str,
        script: str,
        data: dict[str, Any] | BaseModel | None = None,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Execute a custom SQL script via HTTP PUT asynchronously."""
        path = f"/_QUERIES/{folder}/{script}"
        payload = _prepare_payload(data)
        resp = await self._client._request("PUT", path, json_data=payload, params=params)
        return resp.json()

    async def delete(
        self,
        folder: str,
        script: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """Execute a custom SQL script via HTTP DELETE asynchronously."""
        path = f"/_QUERIES/{folder}/{script}"
        resp = await self._client._request("DELETE", path, params=params)
        return resp.json()
