"""Fixtures for API tests. No database is needed in Phase 1."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from weta_api.config import Settings
from weta_api.main import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        environment="test",
        database_url=None,
        allowed_origins=["http://localhost:5173"],
    )


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings), raise_server_exceptions=False) as test_client:
        yield test_client
