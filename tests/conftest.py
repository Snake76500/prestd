"""
Pytest configuration and shared test fixtures for prestd.
"""

import pytest

from prestd.models import PrestConfig, PrestSettings


@pytest.fixture
def mock_prest_config() -> PrestConfig:
    """Standard test configuration pointing to a mock pREST instance."""
    return PrestConfig(
        base_url="http://mock-prest.test:3000",
        default_database="testdb",
        default_schema="public",
        api_key="test-secret-token",
        timeout=5.0,
    )


@pytest.fixture
def mock_prest_settings() -> PrestSettings:
    """Standard test settings."""
    return PrestSettings(
        prest_base_url="http://mock-prest.test:3000",
        prest_default_database="testdb",
        prest_default_schema="public",
        prest_api_key="test-secret-token",
        prest_timeout=5.0,
    )
