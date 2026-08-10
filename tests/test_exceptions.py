"""
Tests for pREST exception mapping and status handling.
"""

import httpx
import pytest

from prestd.client import PrestClient
from prestd.exceptions import (
    PrestAuthenticationError,
    PrestConflictError,
    PrestConnectionError,
    PrestError,
    PrestNotFoundError,
    PrestServerError,
    PrestTimeoutError,
    PrestValidationError,
    raise_for_prest_status,
)
from prestd.models import PrestConfig


def test_status_mapping():
    # 200 should not raise
    raise_for_prest_status(200)
    raise_for_prest_status(201)

    # 401 / 403
    with pytest.raises(PrestAuthenticationError) as exc:
        raise_for_prest_status(401, {"error": "Invalid token"})
    assert "Invalid token" in str(exc.value)
    assert exc.value.status_code == 401

    with pytest.raises(PrestAuthenticationError):
        raise_for_prest_status(403)

    # 404
    with pytest.raises(PrestNotFoundError) as exc:
        raise_for_prest_status(404, {"error": "Table does not exist"})
    assert exc.value.status_code == 404

    # 400 / 422
    with pytest.raises(PrestValidationError):
        raise_for_prest_status(400, {"error": "Bad syntax in filter"})

    with pytest.raises(PrestValidationError):
        raise_for_prest_status(422, "Validation failed")

    # 409
    with pytest.raises(PrestConflictError):
        raise_for_prest_status(409, {"error": "Unique violation on email"})

    # 500
    with pytest.raises(PrestServerError):
        raise_for_prest_status(500, {"error": "Internal database crash"})

    # Other codes (e.g. 418)
    with pytest.raises(PrestError):
        raise_for_prest_status(418, "I'm a teapot")


def test_network_and_timeout_errors(mock_prest_config: PrestConfig):
    # Test timeout error wrapping
    def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("Socket timed out")

    transport = httpx.MockTransport(timeout_handler)
    http_client = httpx.Client(transport=transport, base_url=mock_prest_config.base_url)
    client = PrestClient(config=mock_prest_config, http_client=http_client)

    with pytest.raises(PrestTimeoutError):
        client.health()

    # Test connection error wrapping
    def conn_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    transport2 = httpx.MockTransport(conn_handler)
    http_client2 = httpx.Client(transport=transport2, base_url=mock_prest_config.base_url)
    client2 = PrestClient(config=mock_prest_config, http_client=http_client2)

    with pytest.raises(PrestConnectionError):
        client2.health()
