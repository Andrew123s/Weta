"""Application factory. Run with ``uv run uvicorn weta_api.main:app --reload``."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic.json_schema import models_json_schema

from weta_api import API_PREFIX, __version__
from weta_api.config import Settings, get_settings
from weta_api.db import make_engine
from weta_api.errors import install_exception_handlers
from weta_api.log import configure_logging
from weta_api.middleware.request_id import RequestIdMiddleware
from weta_api.middleware.security_headers import SecurityHeadersMiddleware
from weta_api.routers import system
from weta_schemas.problem import ProblemDetail
from weta_schemas.quantity import QuantityOut

OPENAPI_URL = f"{API_PREFIX}/openapi.json"
DOCS_URL = f"{API_PREFIX}/docs"

# Shared contracts published in the OpenAPI document even before a route returns them, so the
# generated TypeScript types include them (docs/frontend.md: API types are generated).
SHARED_SCHEMAS = (QuantityOut, ProblemDetail)


def _custom_openapi(app: FastAPI) -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi  # noqa: PLC0415 - only needed once

    schema = get_openapi(
        title=app.title,
        version=app.version,
        summary=app.summary,
        description=app.description,
        routes=app.routes,
    )
    _, shared = models_json_schema(
        [(model, "serialization") for model in SHARED_SCHEMAS],
        ref_template="#/components/schemas/{model}",
    )
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    for name, definition in shared.get("$defs", {}).items():
        components.setdefault(name, definition)
    app.openapi_schema = schema
    return schema


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the FastAPI application. Pass ``settings`` in tests to avoid reading the env."""
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = make_engine(settings.database_url) if settings.database_url else None
        app.state.db_engine = engine
        try:
            yield
        finally:
            if engine is not None:
                await engine.dispose()

    app = FastAPI(
        title="Weta API",
        summary="Predictive EIA, LCA, GIS and ML for upstream industrial waste logistics",
        version=__version__,
        openapi_url=OPENAPI_URL,
        docs_url=DOCS_URL if settings.environment != "production" else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.db_engine = None

    install_exception_handlers(app)

    # Starlette runs the last-added middleware outermost: request id wraps everything.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "If-Match",
            "Idempotency-Key",
            "X-Request-ID",
        ],
        expose_headers=["X-Request-ID", "ETag"],
    )
    app.add_middleware(SecurityHeadersMiddleware, csp_exempt_paths=frozenset({DOCS_URL}))
    app.add_middleware(RequestIdMiddleware)

    app.include_router(system.router, prefix=API_PREFIX)

    app.openapi = lambda: _custom_openapi(app)  # type: ignore[method-assign]
    return app


app = create_app()
