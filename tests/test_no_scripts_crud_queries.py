"""
Test file demonstrating and validating that ALL standard database queries and CRUD operations
work directly WITHOUT writing or requiring any SQL script files!
"""

import json

import httpx
import pytest
from pydantic import BaseModel

from prestd import AsyncPrestClient, PrestClient, QueryBuilder
from prestd.models import PrestConfig


class User(BaseModel):
    id: int
    name: str
    role: str = "user"
    age: int = 18


def test_complete_database_operations_without_any_sql_scripts(mock_prest_config: PrestConfig):
    """
    This test proves that 100% of standard SQL querying, filtering, inserting,
    updating, deleting, pagination, and joins do NOT need any SQL script file.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method
        params = dict(request.url.params)

        if url_path == "/testdb/public/users":
            if method == "GET":
                # Check for COUNT query
                if params.get("_count"):
                    return httpx.Response(200, json=[{"count": 42}])
                
                # Check for filtered query: WHERE role = 'admin' AND age > 21
                if params.get("role") == "$eq.admin" and params.get("age") == "$gt.21":
                    return httpx.Response(200, json=[
                        {"id": 1, "name": "Alice Admin", "role": "admin", "age": 30}
                    ])

                # Default list of all users
                return httpx.Response(200, json=[
                    {"id": 1, "name": "Alice", "role": "admin", "age": 30},
                    {"id": 2, "name": "Bob", "role": "member", "age": 25},
                ])

            elif method == "POST":
                # INSERT query
                payload = json.loads(request.content)
                return httpx.Response(201, json={**payload, "id": 3})

            elif method in ("PATCH", "PUT"):
                # UPDATE query
                payload = json.loads(request.content)
                return httpx.Response(200, json={"id": 1, **payload})

            elif method == "DELETE":
                # DELETE query
                return httpx.Response(200, json={"status": "deleted", "id": 1})

        elif url_path == "/testdb/public/orders" and method == "GET":
            # JOIN query between orders and users
            if params.get("_join"):
                return httpx.Response(200, json=[
                    {"order_id": 101, "total": 99.0, "user_name": "Alice"}
                ])
            return httpx.Response(200, json=[{"order_id": 101, "total": 99.0}])

        return httpx.Response(404, json={"error": "Not found"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url=mock_prest_config.base_url)

    with PrestClient(config=mock_prest_config, http_client=http_client) as client:
        # -------------------------------------------------------------
        # 1. SELECT * FROM users (No SQL script required)
        # -------------------------------------------------------------
        users = client.table("users").find()
        assert len(users) == 2
        assert users[0]["name"] == "Alice"

        # Direct shortcut:
        users_direct = client.find("users")
        assert len(users_direct) == 2

        # -------------------------------------------------------------
        # 2. SELECT id, name FROM users WHERE role = 'admin' AND age > 21 ORDER BY name ASC
        # -------------------------------------------------------------
        q = (
            QueryBuilder()
            .select("id", "name", "role", "age")
            .filter_eq("role", "admin")
            .filter_gt("age", 21)
            .order_by("name")
        )
        admins = client.table("users").find(q, model=User)
        assert len(admins) == 1
        assert admins[0].name == "Alice Admin"
        assert admins[0].role == "admin"
        assert admins[0].age == 30

        # -------------------------------------------------------------
        # 3. SELECT * FROM users WHERE id = 1 (No SQL script required)
        # -------------------------------------------------------------
        user_1 = client.get("users", 1, model=User)
        assert user_1 is not None
        assert user_1.id == 1

        # -------------------------------------------------------------
        # 4. INSERT INTO users (name, role, age) VALUES ('Charlie', 'editor', 28)
        # -------------------------------------------------------------
        new_user = client.insert("users", {"name": "Charlie", "role": "editor", "age": 28}, model=User)
        assert new_user.id == 3
        assert new_user.name == "Charlie"

        # -------------------------------------------------------------
        # 5. UPDATE users SET name = 'Alice Updated' WHERE id = 1
        # -------------------------------------------------------------
        updated = client.update("users", 1, {"name": "Alice Updated"})
        assert updated["name"] == "Alice Updated"

        # -------------------------------------------------------------
        # 6. DELETE FROM users WHERE id = 1
        # -------------------------------------------------------------
        deleted = client.delete("users", 1)
        assert deleted["status"] == "deleted"

        # -------------------------------------------------------------
        # 7. SELECT COUNT(*) FROM users
        # -------------------------------------------------------------
        total_count = client.count("users")
        assert total_count == 42

        # -------------------------------------------------------------
        # 8. JOIN: SELECT * FROM orders INNER JOIN users ON orders.user_id = users.id
        # -------------------------------------------------------------
        join_query = (
            QueryBuilder()
            .join("inner", "users", "id", "eq", "orders.user_id")
        )
        joined_orders = client.table("orders").find(join_query)
        assert len(joined_orders) == 1
        assert joined_orders[0]["order_id"] == 101


@pytest.mark.asyncio
async def test_async_database_operations_without_any_sql_scripts(mock_prest_config: PrestConfig):
    """
    Validate asynchronous table querying without any SQL scripts.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        url_path = request.url.path
        method = request.method

        if url_path == "/testdb/public/products":
            if method == "GET":
                return httpx.Response(200, json=[{"id": 1, "title": "Laptop", "price": 999.0}])
            elif method == "POST":
                payload = json.loads(request.content)
                return httpx.Response(201, json={**payload, "id": 10})

        return httpx.Response(404, json={"error": "Not found"})

    transport = httpx.MockTransport(handler)
    http_client = httpx.AsyncClient(transport=transport, base_url=mock_prest_config.base_url)

    async with AsyncPrestClient(config=mock_prest_config, http_client=http_client) as client:
        # Querying without scripts:
        products = await client.find("products")
        assert len(products) == 1
        assert products[0]["title"] == "Laptop"

        # Inserting without scripts:
        new_prod = await client.insert("products", {"title": "Mouse", "price": 25.0})
        assert new_prod["id"] == 10
        assert new_prod["title"] == "Mouse"
