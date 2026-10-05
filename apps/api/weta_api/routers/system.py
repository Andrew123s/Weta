"""System routes: ``/health``, ``/health/ready`` and ``/version`` (unauthenticated)."""

import platform
from importlib.metadata import PackageNotFoundError, version

from fastapi import APIRouter, Request, Response, status

from weta_api import API_VERSION, __version__
from weta_api.config import Settings
from weta_api.db import check_database
from weta_schemas.problem import ProblemDetail
from weta_schemas.system import CheckStatus, HealthResponse, ReadinessResponse, VersionResponse

router = APIRouter(tags=["system"])

# Packages whose versions can change a calculated result or an API contract.
VERSIONED_COMPONENTS = (
    "weta-core",
    "weta-schemas",
    "weta-api",
    "fastapi",
    "pydantic",
    "pint",
    "sqlalchemy",
)


def _component_versions() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in VERSIONED_COMPONENTS:
        try:
            out[name] = version(name)
        except PackageNotFoundError:
            out[name] = "not installed"
    return out


@router.get("/health", summary="Liveness")
async def health() -> HealthResponse:
    """The process is up. Does not touch dependencies."""
    return HealthResponse()


@router.get(
    "/health/ready",
    summary="Readiness",
    responses={503: {"model": ReadinessResponse, "description": "A dependency is not ready"}},
)
async def ready(request: Request, response: Response) -> ReadinessResponse:
    """Checks the dependencies needed for real work. Returns 503 unless all are ``ok``."""
    settings: Settings = request.app.state.settings
    db_check = await check_database(request.app.state.db_engine, settings.db_check_timeout_s)
    checks = [db_check]
    overall = next((c.status for c in checks if c.status is not CheckStatus.OK), CheckStatus.OK)
    if overall is not CheckStatus.OK:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(status=overall, checks=checks)


@router.get(
    "/version",
    summary="Application and component versions",
    responses={500: {"model": ProblemDetail}},
)
async def get_version(request: Request) -> VersionResponse:
    """Versions of the application and of the libraries that affect results."""
    settings: Settings = request.app.state.settings
    return VersionResponse(
        application=__version__,
        api_version=API_VERSION,
        environment=settings.environment,
        git_sha=settings.git_sha,
        python=platform.python_version(),
        components=_component_versions(),
    )
