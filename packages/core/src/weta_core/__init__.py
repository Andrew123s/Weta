"""Weta core package.

Shared foundation for every engine: the ``Quantity`` type, unit handling (pint),
provenance classes and taint flags, the engine node contract and canonical hashing.
This package depends on nothing internal (docs/architecture.md section 4, rule 1).
"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("weta-core")
except PackageNotFoundError:  # pragma: no cover - only when run from an unbuilt tree
    __version__ = "0.0.0+unknown"

__all__ = ["__version__"]
