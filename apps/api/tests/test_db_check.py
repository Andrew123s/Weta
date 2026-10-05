"""Readiness-check logic against a fake engine.

The real PostgreSQL + PostGIS integration test arrives with the schema in Phase 2; these tests
pin the classification logic (ok, degraded, unavailable on timeout) without a server.
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncEngine

from weta_api.db import check_database
from weta_schemas.system import CheckStatus


class _Result:
    def __init__(self, value: object) -> None:
        self.value = value

    def scalar_one(self) -> object:
        return self.value

    def scalar_one_or_none(self) -> object:
        return self.value


class _Conn:
    def __init__(self, postgis: str | None) -> None:
        self.postgis = postgis

    async def execute(self, statement: Any) -> _Result:
        sql = str(statement)
        return _Result("16.4" if "server_version" in sql else self.postgis)


class _Engine:
    def __init__(self, postgis: str | None = "3.4.3", delay_s: float = 0.0) -> None:
        self.postgis = postgis
        self.delay_s = delay_s

    @asynccontextmanager
    async def connect(self) -> AsyncIterator[_Conn]:
        await asyncio.sleep(self.delay_s)
        yield _Conn(self.postgis)


def _run(engine: _Engine, timeout_s: float = 1.0) -> Any:
    return asyncio.run(check_database(cast(AsyncEngine, engine), timeout_s))


def test_ok_reports_both_versions() -> None:
    check = _run(_Engine())
    assert check.status is CheckStatus.OK
    assert check.version == "PostgreSQL 16.4; PostGIS 3.4.3"


def test_missing_postgis_is_degraded() -> None:
    check = _run(_Engine(postgis=None))
    assert check.status is CheckStatus.DEGRADED
    assert "PostGIS" in check.detail


def test_timeout_is_unavailable() -> None:
    check = _run(_Engine(delay_s=1.0), timeout_s=0.05)
    assert check.status is CheckStatus.UNAVAILABLE
    assert check.detail == "no response within 0.05 s"
