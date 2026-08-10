"""
Tests for synchronous PrestClient operations.
"""

import json

import httpx

from prestd.client import PrestClient
from prestd.models import PrestConfig, PrestSettings


def test_sync_client_full_lifecycle(mock_prest_config: PrestConfig):
    def handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if url_path == "/_health":
            return httpx.Response(200, json={"status": "UP", "version": "v2.0.0"})
        elif url_path == "/_ready":
            return httpx.Response(200, json={"status": "UP"})
        elif url_path == "/databases":
            return httpx.Response(200, json=[{"datname": "testdb"}])
        elif url_path == "/schemas":
            return httpx.Response(200, json=[{"schema_name": "public"}, {"schema_name": "analytics"}])
        elif url_path == "/tables":
            return httpx.Response(200, json=[
                {"table_name": "users", "table_schema": "public"},
                {"table_name": "events", "table_schema": "analytics"},
            ])
        elif url_path == "/show/testdb/public/users":
            return httpx.Response(200, json=[
                {"column_name": "id", "data_type": "integer"},
                {"column_name": "name", "data_type": "text"},
            ])
        elif url_path == "/testdb/public/users":
            if method == "GET":
                if request.url.params.get("_count"):
                    return httpx.Response(200, json=[{"count": 100}])
                return httpx.Response(200, json=[
                    {"id": 1, "name": "Alice"},
                    {"id": 2, "name": "Bob"},
                ])
            elif method == "POST":
                payload = json.loads(request.content)
                return httpx.Response(201, json={"id": 3, **payload})
            elif method in ("PATCH", "PUT"):
                payload = json.loads(request.content)
                return httpx.Response(200, json={"id": 1, **payload})
            elif method == "DELETE":
                return httpx.Response(200, json={"status": "deleted"})
        elif url_path == "/testdb/public/users/batch":
            if method == "POST":
                payload = json.loads(request.content)
                return httpx.Response(201, json=payload)
        elif url_path == "/_QUERIES/reports/daily":
            if method == "GET":
                return httpx.Response(200, json=[{"metric": "sales", "value": 5000}])
            elif method == "POST":
                return httpx.Response(200, json={"status": "report_generated"})

        return httpx.Response(404, json={"error": f"Path not found: {url_path}"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url=mock_prest_config.base_url)

    with PrestClient(config=mock_prest_config, http_client=http_client) as client:
        # Health & Ready probes
        health = client.health()
        assert health.status == "UP"
        assert health.database_connected is True

        ready = client.ready()
        assert ready.status == "UP"

        # Metadata
        dbs = client.databases()
        assert len(dbs) == 1
        assert dbs[0].datname == "testdb"

        schemas = client.schemas()
        assert len(schemas) == 2

        tables = client.tables()
        assert len(tables) == 2

        # Hierarchy accessors
        db_acc = client.database("testdb")
        public_schema = db_acc.schema("public")
        public_tables = public_schema.tables()
        assert len(public_tables) == 1
        assert public_tables[0].table_name == "users"

        # Direct table accessor
        users_table = client.table("users")
        all_users = users_table.find()
        assert len(all_users) == 2
        assert all_users[0]["name"] == "Alice"

        one_user = users_table.find_one()
        assert one_user is not None
        assert one_user["name"] == "Alice"

        user_by_id = users_table.get(1)
        assert user_by_id is not None
        assert user_by_id["id"] == 1

        created = users_table.insert({"name": "Charlie"})
        assert created["id"] == 3
        assert created["name"] == "Charlie"

        batch_created = users_table.insert_many([{"name": "D"}, {"name": "E"}])
        assert len(batch_created) == 2

        updated = users_table.update_by_id(1, {"name": "Alice New"})
        assert updated["name"] == "Alice New"

        deleted = users_table.delete_by_id(1)
        assert deleted["status"] == "deleted"

        count = users_table.count()
        assert count == 100

        paginated = users_table.paginate(page=1, page_size=2)
        assert len(paginated.items) == 2
        assert paginated.total_count == 100
        assert paginated.total_pages == 50
        assert paginated.has_next is True

        schema_meta = users_table.show()
        assert schema_meta.table_name == "users"
        assert schema_meta.columns is not None
        assert len(schema_meta.columns) == 2

        # Custom SQL queries
        sql_res = client.sql.get("reports", "daily")
        assert sql_res[0]["value"] == 5000

        sql_post_res = client.sql.post("reports", "daily", data={"date": "2026-08-10"})
        assert sql_post_res["status"] == "report_generated"


def test_sync_client_factory_from_settings(mock_prest_settings: PrestSettings):
    client = PrestClient.from_settings(mock_prest_settings, timeout=15.0)
    assert client.config.base_url == "http://mock-prest.test:3000"
    assert client.config.default_database == "testdb"
    assert client.config.timeout == 15.0
    client.close()
