"""Database connectivity for Phase 1: an async engine and a readiness check only.

The schema, repositories and migrations arrive in Phase 2 (``packages/db``). This module
never puts the connection URL or driver error text in a response, since either may contain
credentials or host details; those go to the log.
"""

import asyncio
import logging

from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from weta_schemas.system import CheckStatus, ComponentCheck

logger = logging.getLogger("weta.api.db")

CHECK_NAME = "database"


def make_engine(url: SecretStr) -> AsyncEngine:
    """Create the application's async engine (asyncpg driver)."""
    return create_async_engine(url.get_secret_value(), pool_pre_ping=True)


async def _probe(engine: AsyncEngine) -> ComponentCheck:
    async with engine.connect() as conn:
        server_version = (await conn.execute(text("SHOW server_version"))).scalar_one()
        postgis = (
            await conn.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'postgis'")
            )
        ).scalar_one_or_none()
    if postgis is None:
        return ComponentCheck(
            name=CHECK_NAME,
            status=CheckStatus.DEGRADED,
            detail="PostgreSQL reachable but the PostGIS extension is not installed",
            version=f"PostgreSQL {server_version}",
        )
    return ComponentCheck(
        name=CHECK_NAME,
        status=CheckStatus.OK,
        version=f"PostgreSQL {server_version}; PostGIS {postgis}",
    )


async def check_database(engine: AsyncEngine | None, timeout_s: float) -> ComponentCheck:
    """Report whether the database is configured, reachable and has PostGIS."""
    if engine is None:
        return ComponentCheck(
            name=CHECK_NAME,
            status=CheckStatus.NOT_CONFIGURED,
            detail="WETA_DATABASE_URL is not set",
        )
    try:
        return await asyncio.wait_for(_probe(engine), timeout=timeout_s)
    except TimeoutError:
        logger.warning("database readiness check timed out", extra={"timeout_s": timeout_s})
        detail = f"no response within {timeout_s:g} s"
    except Exception as exc:  # any driver or network failure means "unavailable"
        logger.warning("database readiness check failed", extra={"error": type(exc).__name__})
        detail = f"connection failed ({type(exc).__name__})"
    return ComponentCheck(name=CHECK_NAME, status=CheckStatus.UNAVAILABLE, detail=detail)
