"""System endpoints: liveness, readiness and version (docs/deployment.md section 9)."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict


class CheckStatus(StrEnum):
    """Status of one readiness check."""

    OK = "ok"
    NOT_CONFIGURED = "not_configured"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


class HealthResponse(BaseModel):
    """Liveness: the process is up and serving requests."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"


class ComponentCheck(BaseModel):
    """Result of one readiness check. ``detail`` never contains credentials."""

    model_config = ConfigDict(extra="forbid")

    name: str
    status: CheckStatus
    detail: str | None = None
    version: str | None = None


class ReadinessResponse(BaseModel):
    """Readiness: whether the dependencies needed to serve real work are available."""

    model_config = ConfigDict(extra="forbid")

    status: CheckStatus
    checks: list[ComponentCheck]


class VersionResponse(BaseModel):
    """Versions of the application and the components that affect results."""

    model_config = ConfigDict(extra="forbid")

    application: str
    api_version: str
    environment: str
    git_sha: str | None
    python: str
    components: dict[str, str]
