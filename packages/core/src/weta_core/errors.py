"""Error types raised by the core package.

Engines report missing data through ``NodeResult`` statuses, not exceptions. The
exceptions here are for programming and contract errors: an invalid unit, a
dimensionally inconsistent operation, or an attempt to silently drop uncertainty.
"""


class WetaError(Exception):
    """Base class for all Weta errors."""


class UnitError(WetaError, ValueError):
    """Base class for unit problems. A ``ValueError`` so pydantic reports it as a field error."""


class UnitParseError(UnitError):
    """A unit string could not be parsed by the unit registry."""


class DimensionalityError(UnitError):
    """Two units are not dimensionally compatible for the requested operation."""


class UnitArithmeticError(UnitError):
    """An operation is not defined for the given units (for example adding offset temperatures)."""


class MissingValueError(WetaError):
    """A calculation needed the value of a quantity whose value is not available."""


class UncertaintyPropagationError(WetaError):
    """Plain arithmetic was attempted on a quantity that carries a non-point distribution.

    Uncertainty is propagated only by ``engines/uncertainty`` (docs/development-rules.md A.5),
    so core arithmetic refuses instead of silently collapsing the distribution to a point.
    """


class CanonicalizationError(WetaError, TypeError):
    """A value cannot be represented in canonical JSON (and therefore cannot be hashed)."""


class NodeContractError(WetaError):
    """An engine node violated its declared contract (inputs, outputs, provenance or status)."""


class NodeRegistrationError(WetaError):
    """A node declaration is invalid or conflicts with an already registered node."""
