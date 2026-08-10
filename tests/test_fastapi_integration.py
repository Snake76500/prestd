"""
Tests for FastAPI dependency injection and exception handlers integration.
"""

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from prestd.client import AsyncPrestClient, PrestClient
from prestd.exceptions import (
    PrestConflictError,
    PrestNotFoundError,
    PrestValidationError,
)
from prestd.integrations.fastapi import (
    get_async_prest_client,
    get_prest_client,
    set_prest_settings,
    setup_prest_exception_handlers,
)
from prestd.models import PrestSettings


@pytest.fixture
def mock_app(mock_prest_settings: PrestSettings) -> FastAPI:
    set_prest_settings(mock_prest_settings)
    app = FastAPI(title="Test Microservice")
    setup_prest_exception_handlers(app)

    @app.get("/sync-users")
    def list_sync_users(client: PrestClient = Depends(get_prest_client)):
        return [{"client_type": "sync", "db": client.config.default_database}]

    @app.get("/async-users")
    async def list_async_users(client: AsyncPrestClient = Depends(get_async_prest_client)):
        return [{"client_type": "async", "db": client.config.default_database}]

    @app.get("/raise-not-found")
    def trigger_not_found():
        raise PrestNotFoundError("User record not found in pREST", status_code=404)

    @app.get("/raise-conflict")
    def trigger_conflict():
        raise PrestConflictError("Email already exists in database", status_code=409)

    @app.get("/raise-validation")
    def trigger_validation():
        raise PrestValidationError("Invalid query parameter filter", status_code=422)

    return app


def test_fastapi_dependency_and_exception_handlers(mock_app: FastAPI):
    client = TestClient(mock_app)

    # Test sync client dependency injection
    r1 = client.get("/sync-users")
    assert r1.status_code == 200
    assert r1.json() == [{"client_type": "sync", "db": "testdb"}]

    # Test async client dependency injection
    r2 = client.get("/async-users")
    assert r2.status_code == 200
    assert r2.json() == [{"client_type": "async", "db": "testdb"}]

    # Test 404 exception translation
    r_404 = client.get("/raise-not-found")
    assert r_404.status_code == 404
    assert r_404.json()["type"] == "PrestNotFoundError"
    assert "User record not found" in r_404.json()["detail"]

    # Test 409 exception translation
    r_409 = client.get("/raise-conflict")
    assert r_409.status_code == 409
    assert r_409.json()["type"] == "PrestConflictError"
    assert "Email already exists" in r_409.json()["detail"]

    # Test 422 exception translation
    r_422 = client.get("/raise-validation")
    assert r_422.status_code == 422
    assert r_422.json()["type"] == "PrestValidationError"
