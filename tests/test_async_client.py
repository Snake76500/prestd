"""
Tests for asynchronous AsyncPrestClient operations.
"""

import json

import httpx
import pytest

from prestd.client import AsyncPrestClient
from prestd.models import PrestConfig, PrestSettings


@pytest.mark.asyncio
async def test_async_client_full_lifecycle(mock_prest_config: PrestConfig):
    def handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if url_path in ("/_health", "/_ready"):
            return httpx.Response(200, json={"status": "UP"})
        elif url_path == "/databases":
            return httpx.Response(200, json=[{"datname": "testdb"}])
        elif url_path == "/schemas":
            return httpx.Response(200, json=[{"schema_name": "public"}])
        elif url_path == "/tables":
            return httpx.Response(200, json=[{"table_name": "orders", "table_schema": "public"}])
        elif url_path == "/show/testdb/public/orders":
            return httpx.Response(200, json=[
                {"column_name": "id", "data_type": "integer"},
                {"column_name": "amount", "data_type": "numeric"},
            ])
        elif url_path == "/testdb/public/orders":
            if method == "GET":
                if request.url.params.get("_count"):
                    return httpx.Response(200, json=[{"count": 50}])
                return httpx.Response(200, json=[
                    {"id": 1, "amount": 99.99},
                    {"id": 2, "amount": 149.50},
                ])
            elif method == "POST":
                payload = json.loads(request.content)
                return httpx.Response(201, json={"id": 3, **payload})
            elif method in ("PATCH", "PUT"):
                payload = json.loads(request.content)
                return httpx.Response(200, json={"id": 1, **payload})
            elif method == "DELETE":
                return httpx.Response(200, json={"status": "deleted"})
        elif url_path == "/testdb/public/orders/batch":
            if method == "POST":
                payload = json.loads(request.content)
                return httpx.Response(201, json=payload)
        elif url_path == "/_QUERIES/finance/quarterly":
            if method == "GET":
                return httpx.Response(200, json=[{"revenue": 120000}])
            elif method == "POST":
                return httpx.Response(200, json={"job_id": "calc_99"})

        return httpx.Response(404, json={"error": f"Path not found: {url_path}"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url=mock_prest_config.base_url)

    async with AsyncPrestClient(config=mock_prest_config, http_client=http_client) as client:
        # Health probes
        health = await client.health()
        assert health.status == "UP"

        ready = await client.ready()
        assert ready.status == "UP"

        # Metadata
        dbs = await client.databases()
        assert len(dbs) == 1

        schemas = await client.schemas()
        assert len(schemas) == 1

        tables = await client.tables()
        assert len(tables) == 1

        # Table accessor
        orders = client.table("orders")
        all_orders = await orders.find()
        assert len(all_orders) == 2
        assert all_orders[0]["amount"] == 99.99

        one_order = await orders.find_one()
        assert one_order is not None
        assert one_order["id"] == 1

        order = await orders.get(1)
        assert order is not None
        assert order["amount"] == 99.99

        created = await orders.insert({"amount": 250.0})
        assert created["id"] == 3
        assert created["amount"] == 250.0

        batch_created = await orders.insert_many([{"amount": 10.0}, {"amount": 20.0}])
        assert len(batch_created) == 2

        updated = await orders.update_by_id(1, {"amount": 105.0})
        assert updated["amount"] == 105.0

        deleted = await orders.delete_by_id(1)
        assert deleted["status"] == "deleted"

        count = await orders.count()
        assert count == 50

        paged = await orders.paginate(page=1, page_size=2)
        assert len(paged.items) == 2
        assert paged.total_count == 50
        assert paged.total_pages == 25

        schema_info = await orders.show()
        assert schema_info.table_name == "orders"
        assert len(schema_info.columns) == 2

        # SQL Queries
        sql_get = await client.sql.get("finance", "quarterly")
        assert sql_get[0]["revenue"] == 120000

        sql_post = await client.sql.post("finance", "quarterly", data={"year": 2026})
        assert sql_post["job_id"] == "calc_99"


@pytest.mark.asyncio
async def test_async_client_factory_from_settings(mock_prest_settings: PrestSettings):
    client = AsyncPrestClient.from_settings(mock_prest_settings, default_database="otherdb")
    assert client.config.default_database == "otherdb"
    assert client.config.base_url == "http://mock-prest.test:3000"
    await client.aclose()
