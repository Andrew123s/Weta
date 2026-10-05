"""The ``Quantity`` type: every numeric value that crosses an engine boundary.

docs/architecture.md section 4. A quantity is a value with a unit, an optional uncertainty
distribution, a provenance class, a source reference, optional data-quality scores and the
taint flags it inherited. A bare float never crosses an engine boundary.
"""

import math
from collections.abc import Mapping
from typing import Any
from uuid import UUID

import pint
from pydantic import BaseModel, ConfigDict, Field, field_validator

from weta_core import units
from weta_core.distributions import Distribution, PointDistribution
from weta_core.errors import (
    DimensionalityError,
    MissingValueError,
    UncertaintyPropagationError,
    UnitArithmeticError,
)
from weta_core.provenance import ProvenanceClass, TaintFlag, combine_taint


class DataQuality(BaseModel):
    """Data-quality scores under a named scheme.

    Scheme-neutral on purpose: which pedigree-style scheme to use is open decision D-09
    (docs/assumptions.md), so no indicator names are fixed here.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    scheme: str = Field(min_length=1, max_length=100)
    scheme_version: str = Field(min_length=1, max_length=50)
    scores: Mapping[str, int | str]


class Quantity(BaseModel):
    """A value with unit, uncertainty, provenance, source and inherited taint.

    ``value`` may be ``None`` when the quantity is not available or is known only as an
    interval; arithmetic on such a quantity raises ``MissingValueError`` instead of
    treating it as zero.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    value: float | None
    unit: str
    distribution: Distribution | None = None
    provenance: ProvenanceClass
    source_id: UUID | None = None
    quality: DataQuality | None = None
    taint: frozenset[TaintFlag] = frozenset()

    @field_validator("value")
    @classmethod
    def _finite_value(cls, v: float | None) -> float | None:
        if v is not None and not math.isfinite(v):
            msg = "quantity value must be finite; use value=None for an unavailable value"
            raise ValueError(msg)
        return v

    @field_validator("unit")
    @classmethod
    def _valid_unit(cls, v: str) -> str:
        units.parse_unit(v)  # raises UnitParseError, which pydantic reports as a validation error
        return v

    # ------------------------------------------------------------------ properties

    @property
    def is_available(self) -> bool:
        """True if the quantity has a value."""
        return self.value is not None

    @property
    def is_point(self) -> bool:
        """True if the quantity carries no uncertainty distribution beyond a point."""
        return self.distribution is None or isinstance(self.distribution, PointDistribution)

    @property
    def dimensionality(self) -> str:
        """Dimensionality of the unit, for example ``[mass] / [time]``."""
        return units.dimensionality(self.unit)

    # ------------------------------------------------------------------ conversion

    def to(self, unit: str) -> "Quantity":
        """The same quantity expressed in ``unit``.

        Provenance, source, quality and taint are unchanged: a unit conversion is not a
        derivation. Distribution parameters are transformed exactly.
        """
        scale, offset = units.affine(self.unit, unit)
        value = None if self.value is None else units.convert(self.value, self.unit, unit)
        dist = None if self.distribution is None else self.distribution.transformed(scale, offset)
        return self.model_copy(update={"value": value, "unit": unit, "distribution": dist})

    def to_canonical(self) -> "Quantity":
        """The same quantity in its SI base-unit form, as stored in the database."""
        return self.to(units.canonical_unit(self.unit))

    def magnitude_in(self, unit: str) -> float:
        """The value converted to ``unit``. Raises ``MissingValueError`` if unavailable."""
        if self.value is None:
            msg = "quantity has no value"
            raise MissingValueError(msg)
        return units.convert(self.value, self.unit, unit)

    # ------------------------------------------------------------------ arithmetic

    def _operand(self) -> Any:
        if self.value is None:
            msg = "arithmetic on a quantity without a value; report insufficient_data instead"
            raise MissingValueError(msg)
        if not self.is_point:
            msg = (
                "plain arithmetic would drop this quantity's distribution; "
                "propagate uncertainty through engines/uncertainty"
            )
            raise UncertaintyPropagationError(msg)
        return units.ureg.Quantity(self.value, units.parse_unit(self.unit))

    def _derived(self, other: "Quantity", magnitude: float, unit: str) -> "Quantity":
        if not math.isfinite(magnitude):
            msg = "arithmetic produced a non-finite value"
            raise ArithmeticError(msg)
        return Quantity(
            value=magnitude,
            unit=unit,
            provenance=ProvenanceClass.DERIVED,
            taint=combine_taint([self, other]),
        )

    def _binary(self, other: object, op: str) -> "Quantity":
        if not isinstance(other, Quantity):
            msg = f"cannot combine a Quantity with {type(other).__name__}; wrap it in a Quantity"
            raise TypeError(msg)
        a, b = self._operand(), other._operand()
        try:
            if op in {"add", "sub"}:
                # Sums keep the left operand's unit text exactly as written.
                b_in_a = b.to(a.units)
                result = a + b_in_a if op == "add" else a - b_in_a
                return self._derived(other, float(result.magnitude), self.unit)
            result = (a * b if op == "mul" else a / b).to_reduced_units()
        except pint.errors.DimensionalityError as exc:
            msg = f"cannot {op} {self.unit!r} and {other.unit!r}: {exc}"
            raise DimensionalityError(msg) from exc
        except pint.errors.OffsetUnitCalculusError as exc:
            msg = f"{op} is not defined for offset units {self.unit!r}, {other.unit!r}: {exc}"
            raise UnitArithmeticError(msg) from exc
        return self._derived(other, float(result.magnitude), units.format_unit(result.units))

    def __add__(self, other: object) -> "Quantity":
        """Sum, in this quantity's unit. Provenance DERIVED, taint from both operands."""
        return self._binary(other, "add")

    def __sub__(self, other: object) -> "Quantity":
        """Difference, in this quantity's unit. Provenance DERIVED, taint from both operands."""
        return self._binary(other, "sub")

    def __mul__(self, other: object) -> "Quantity":
        """Product. Provenance DERIVED, taint from both operands."""
        return self._binary(other, "mul")

    def __truediv__(self, other: object) -> "Quantity":
        """Quotient. Provenance DERIVED, taint from both operands."""
        return self._binary(other, "div")
