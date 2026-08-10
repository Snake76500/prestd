"""
Tests for generic Pydantic model serialization and deserialization.
"""

import json

import httpx
import pytest
from pydantic import BaseModel

from prestd.client import AsyncPrestClient, PrestClient
from prestd.models import PrestConfig


class UserModel(BaseModel):
    id: int
    name: str
    email: str
    is_active: bool = True


class ReportMetric(BaseModel):
    label: str
    value: float


def test_sync_pydantic_mapping(mock_prest_config: PrestConfig):
    def handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if url_path == "/testdb/public/users":
            if method == "GET":
                if request.url.params.get("_count"):
                    return httpx.Response(200, json=[{"count": 1}])
                return httpx.Response(200, json=[{"id": 1, "name": "Alice", "email": "alice@example.com", "is_active": True}])
            elif method == "POST":
                payload = json.loads(request.content)
                return httpx.Response(201, json={**payload, "id": 2})
        elif url_path == "/_QUERIES/analytics/kpi":
            return httpx.Response(200, json=[{"label": "MRR", "value": 15000.0}])

        return httpx.Response(404, json={"error": "Not found"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url=mock_prest_config.base_url)

    with PrestClient(config=mock_prest_config, http_client=http_client) as client:
        table = client.table("users")

        # find with model
        users = table.find(model=UserModel)
        assert len(users) == 1
        assert isinstance(users[0], UserModel)
        assert users[0].name == "Alice"

        # find_one with model
        user = table.find_one(model=UserModel)
        assert user is not None
        assert isinstance(user, UserModel)
        assert user.id == 1

        # get with model
        user_by_id = table.get(1, model=UserModel)
        assert user_by_id is not None
        assert isinstance(user_by_id, UserModel)

        # insert with model instance
        new_user = UserModel(id=0, name="Bob", email="bob@test.com", is_active=True)
        created = table.insert(new_user, model=UserModel)
        assert isinstance(created, UserModel)
        assert created.id == 2
        assert created.name == "Bob"

        # paginate with model
        paged = table.paginate(model=UserModel, page=1, page_size=10)
        assert len(paged.items) == 1
        assert isinstance(paged.items[0], UserModel)

        # sql queries with model
        kpis = client.sql.get("analytics", "kpi", model=ReportMetric)
        assert len(kpis) == 1
        assert isinstance(kpis[0], ReportMetric)
        assert kpis[0].value == 15000.0


@pytest.mark.asyncio
async def test_async_pydantic_mapping(mock_prest_config: PrestConfig):
    def handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if url_path == "/testdb/public/users":
            if method == "GET":
                return httpx.Response(200, json=[{"id": 1, "name": "Async Alice", "email": "async@test.com", "is_active": True}])
            elif method == "POST":
                payload = json.loads(request.content)
                return httpx.Response(201, json={"id": 10, **payload})

        return httpx.Response(404, json={"error": "Not found"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url=mock_prest_config.base_url)

    async with AsyncPrestClient(config=mock_prest_config, http_client=http_client) as client:
        table = client.table("users")

        users = await table.find(model=UserModel)
        assert len(users) == 1
        assert isinstance(users[0], UserModel)
        assert users[0].name == "Async Alice"

        created = await table.insert(
            {"name": "Async Bob", "email": "bob@async.com", "is_active": True},
            model=UserModel,
        )
        assert isinstance(created, UserModel)
        assert created.id == 10
