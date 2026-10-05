"""Uncertainty distributions attached to a ``Quantity``.

docs/architecture.md section 4 and docs/data-model.md (``uncertainty_specs``). The kinds are
point, uniform, triangular, normal, lognormal, empirical and interval. Parameters are expressed
in the unit of the quantity that carries them, so a unit conversion transforms them too.

These classes only describe uncertainty. Sampling and propagation belong to
``engines/uncertainty``.
"""

import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from weta_core.errors import UnitArithmeticError


def _finite(*values: float) -> None:
    for v in values:
        if not math.isfinite(v):
            msg = f"distribution parameters must be finite, got {v!r}"
            raise ValueError(msg)


class _Distribution(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class PointDistribution(_Distribution):
    """No stated uncertainty: the quantity's value is used as given."""

    kind: Literal["point"] = "point"

    def transformed(self, scale: float, offset: float) -> "PointDistribution":  # noqa: ARG002
        """Unit conversion leaves a point distribution unchanged."""
        return self


class UniformDistribution(_Distribution):
    """Uniform between ``min`` and ``max``."""

    kind: Literal["uniform"] = "uniform"
    min: float
    max: float

    @model_validator(mode="after")
    def _check(self) -> "UniformDistribution":
        _finite(self.min, self.max)
        if not self.min < self.max:
            msg = "uniform distribution needs min < max"
            raise ValueError(msg)
        return self

    def transformed(self, scale: float, offset: float) -> "UniformDistribution":
        """Parameters after an affine unit conversion ``x -> scale * x + offset``."""
        return UniformDistribution(min=scale * self.min + offset, max=scale * self.max + offset)


class TriangularDistribution(_Distribution):
    """Triangular with lower limit ``min``, mode ``mode`` and upper limit ``max``."""

    kind: Literal["triangular"] = "triangular"
    min: float
    mode: float
    max: float

    @model_validator(mode="after")
    def _check(self) -> "TriangularDistribution":
        _finite(self.min, self.mode, self.max)
        if not (self.min <= self.mode <= self.max and self.min < self.max):
            msg = "triangular distribution needs min <= mode <= max and min < max"
            raise ValueError(msg)
        return self

    def transformed(self, scale: float, offset: float) -> "TriangularDistribution":
        """Parameters after an affine unit conversion ``x -> scale * x + offset``."""
        return TriangularDistribution(
            min=scale * self.min + offset,
            mode=scale * self.mode + offset,
            max=scale * self.max + offset,
        )


class NormalDistribution(_Distribution):
    """Normal with mean ``mean`` and standard deviation ``sd``."""

    kind: Literal["normal"] = "normal"
    mean: float
    sd: float

    @model_validator(mode="after")
    def _check(self) -> "NormalDistribution":
        _finite(self.mean, self.sd)
        if not self.sd > 0:
            msg = "normal distribution needs sd > 0"
            raise ValueError(msg)
        return self

    def transformed(self, scale: float, offset: float) -> "NormalDistribution":
        """Parameters after an affine unit conversion ``x -> scale * x + offset``."""
        return NormalDistribution(mean=scale * self.mean + offset, sd=scale * self.sd)


class LognormalDistribution(_Distribution):
    """Lognormal given by its median (geometric mean) and geometric standard deviation.

    ``ln(X)`` is normal with mean ``ln(median)`` and standard deviation ``ln(gsd)``.
    """

    kind: Literal["lognormal"] = "lognormal"
    median: float
    gsd: float

    @model_validator(mode="after")
    def _check(self) -> "LognormalDistribution":
        _finite(self.median, self.gsd)
        if not self.median > 0:
            msg = "lognormal distribution needs median > 0"
            raise ValueError(msg)
        if not self.gsd > 1:
            msg = "lognormal distribution needs gsd > 1"
            raise ValueError(msg)
        return self

    def transformed(self, scale: float, offset: float) -> "LognormalDistribution":
        """Parameters after a unit conversion. Only multiplicative conversions are defined."""
        if offset != 0:
            msg = "a lognormal distribution cannot be converted to an offset unit scale"
            raise UnitArithmeticError(msg)
        return LognormalDistribution(median=scale * self.median, gsd=self.gsd)


class IntervalDistribution(_Distribution):
    """Known bounds without a stated shape. ``low == high`` is allowed (degenerate)."""

    kind: Literal["interval"] = "interval"
    low: float
    high: float

    @model_validator(mode="after")
    def _check(self) -> "IntervalDistribution":
        _finite(self.low, self.high)
        if not self.low <= self.high:
            msg = "interval needs low <= high"
            raise ValueError(msg)
        return self

    def transformed(self, scale: float, offset: float) -> "IntervalDistribution":
        """Parameters after an affine unit conversion ``x -> scale * x + offset``."""
        return IntervalDistribution(low=scale * self.low + offset, high=scale * self.high + offset)


class EmpiricalDistribution(_Distribution):
    """An empirical distribution given by its samples."""

    kind: Literal["empirical"] = "empirical"
    samples: tuple[float, ...] = Field(min_length=2)

    @model_validator(mode="after")
    def _check(self) -> "EmpiricalDistribution":
        _finite(*self.samples)
        return self

    def transformed(self, scale: float, offset: float) -> "EmpiricalDistribution":
        """Samples after an affine unit conversion ``x -> scale * x + offset``."""
        return EmpiricalDistribution(samples=tuple(scale * s + offset for s in self.samples))


Distribution = Annotated[
    PointDistribution
    | UniformDistribution
    | TriangularDistribution
    | NormalDistribution
    | LognormalDistribution
    | IntervalDistribution
    | EmpiricalDistribution,
    Field(discriminator="kind"),
]
