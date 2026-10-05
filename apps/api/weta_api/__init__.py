"""Weta API: FastAPI application factory, configuration, middleware and routers."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("weta-api")
except PackageNotFoundError:  # pragma: no cover - only when run from an unbuilt tree
    __version__ = "0.0.0+unknown"

API_VERSION = "v1"
API_PREFIX = f"/api/{API_VERSION}"
