"""Unit handling. The only place in Weta where units are parsed or converted.

docs/development-rules.md B.2: unit conversion happens only through this module. It wraps a
single pint registry and turns pint's exceptions into Weta errors, so callers never depend on
pint directly.

Unit conventions that matter scientifically are registered in docs/assumptions.md:

- ``year`` (``yr``, ``a``) is pint's Julian year of 365.25 days (assumption A-UNIT-01).
- ``FU`` (functional unit) is its own base dimension, so a per-FU quantity can never be
  silently converted to an absolute one.
"""

from functools import lru_cache
from typing import Any

import pint

from weta_core.errors import DimensionalityError, UnitArithmeticError, UnitParseError

# One registry for the whole process. Quantities from different registries cannot be mixed.
ureg: Any = pint.UnitRegistry()
ureg.define("functional_unit = [functional_unit] = FU")

DIMENSIONLESS = "dimensionless"


@lru_cache(maxsize=4096)
def parse_unit(unit: str) -> Any:
    """Parse a unit string into a pint unit. Raises ``UnitParseError`` if it is not a pure unit.

    Scaling factors ("2 kg") and empty strings are rejected: a dimensionless value must say
    ``dimensionless`` (or a ratio such as ``kg/kg``) explicitly.
    """
    if not isinstance(unit, str) or not unit.strip():
        msg = "unit must be a non-empty string; use 'dimensionless' for pure numbers"
        raise UnitParseError(msg)
    try:
        return ureg.parse_units(unit)
    except Exception as exc:  # pint raises several unrelated exception types for bad input
        msg = f"cannot parse unit {unit!r}: {exc}"
        raise UnitParseError(msg) from exc


def is_valid_unit(unit: str) -> bool:
    """True if ``unit`` parses as a unit."""
    try:
        parse_unit(unit)
    except UnitParseError:
        return False
    return True


def dimensionality(unit: str) -> str:
    """Dimensionality of a unit as a string, for example ``[mass] / [time]``."""
    return str(parse_unit(unit).dimensionality)


def is_compatible(unit_a: str, unit_b: str) -> bool:
    """True if values in ``unit_a`` can be converted to ``unit_b``."""
    return bool(parse_unit(unit_a).dimensionality == parse_unit(unit_b).dimensionality)


def _require_compatible(from_unit: str, to_unit: str) -> None:
    if not is_compatible(from_unit, to_unit):
        msg = (
            f"cannot convert {from_unit!r} ({dimensionality(from_unit)}) "
            f"to {to_unit!r} ({dimensionality(to_unit)})"
        )
        raise DimensionalityError(msg)


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a value between dimensionally compatible units.

    Handles offset units (for example degC to K) correctly for absolute values.
    """
    _require_compatible(from_unit, to_unit)
    try:
        return float(ureg.Quantity(value, parse_unit(from_unit)).to(parse_unit(to_unit)).magnitude)
    except pint.errors.OffsetUnitCalculusError as exc:
        msg = f"conversion {from_unit!r} -> {to_unit!r} is ambiguous for offset units: {exc}"
        raise UnitArithmeticError(msg) from exc


def affine(from_unit: str, to_unit: str) -> tuple[float, float]:
    """Return ``(scale, offset)`` such that ``convert(x) == scale * x + offset`` for all x.

    Every unit conversion is affine; ``offset`` is non-zero only for offset scales such as
    degrees Celsius. Used to transform distribution parameters exactly.
    """
    offset = convert(0.0, from_unit, to_unit)
    scale = convert(1.0, from_unit, to_unit) - offset
    return scale, offset


def canonical_unit(unit: str) -> str:
    """The SI base-unit form used for storage (docs/data-model.md section 1)."""
    return str(ureg.Quantity(1.0, parse_unit(unit)).to_base_units().units)


def format_unit(unit_obj: Any) -> str:
    """Render a pint unit as a string that ``parse_unit`` accepts again."""
    return str(unit_obj)
