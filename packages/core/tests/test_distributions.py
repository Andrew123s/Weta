"""Distribution parameter validation and exact transformation under unit conversion."""

import pytest
from pydantic import TypeAdapter, ValidationError

from weta_core.distributions import (
    Distribution,
    EmpiricalDistribution,
    IntervalDistribution,
    LognormalDistribution,
    NormalDistribution,
    PointDistribution,
    TriangularDistribution,
    UniformDistribution,
)
from weta_core.errors import UnitArithmeticError

ADAPTER: TypeAdapter[Distribution] = TypeAdapter(Distribution)


@pytest.mark.parametrize(
    "payload",
    [
        {"kind": "uniform", "min": 2.0, "max": 1.0},
        {"kind": "uniform", "min": 1.0, "max": 1.0},
        {"kind": "triangular", "min": 0.0, "mode": 5.0, "max": 4.0},
        {"kind": "triangular", "min": 1.0, "mode": 1.0, "max": 1.0},
        {"kind": "normal", "mean": 0.0, "sd": 0.0},
        {"kind": "normal", "mean": float("nan"), "sd": 1.0},
        {"kind": "lognormal", "median": 0.0, "gsd": 2.0},
        {"kind": "lognormal", "median": 1.0, "gsd": 1.0},
        {"kind": "interval", "low": 3.0, "high": 2.0},
        {"kind": "empirical", "samples": [1.0]},
        {"kind": "empirical", "samples": [1.0, float("inf")]},
        {"kind": "beta", "a": 1.0, "b": 1.0},
        {"kind": "uniform", "min": 0.0, "max": 1.0, "extra": 1},
    ],
)
def test_invalid_parameters_rejected(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ADAPTER.validate_python(payload)


def test_discriminated_parsing() -> None:
    dist = ADAPTER.validate_python({"kind": "triangular", "min": 1, "mode": 2, "max": 4})
    assert isinstance(dist, TriangularDistribution)
    assert ADAPTER.validate_python({"kind": "interval", "low": 2, "high": 2}).low == 2.0


def test_affine_transforms() -> None:
    # kg -> g: scale 1000, offset 0
    assert UniformDistribution(min=1, max=2).transformed(1000, 0) == UniformDistribution(
        min=1000, max=2000
    )
    assert TriangularDistribution(min=1, mode=2, max=4).transformed(1000, 0) == (
        TriangularDistribution(min=1000, mode=2000, max=4000)
    )
    assert LognormalDistribution(median=2, gsd=1.5).transformed(1000, 0) == (
        LognormalDistribution(median=2000, gsd=1.5)
    )
    assert EmpiricalDistribution(samples=(1, 2)).transformed(10, 1) == EmpiricalDistribution(
        samples=(11, 21)
    )
    # degC -> K: scale 1, offset 273.15; a standard deviation is a difference, so no offset
    assert NormalDistribution(mean=20, sd=2).transformed(1, 273.15) == NormalDistribution(
        mean=293.15, sd=2
    )
    assert IntervalDistribution(low=0, high=10).transformed(1, 273.15) == IntervalDistribution(
        low=273.15, high=283.15
    )
    point = PointDistribution()
    assert point.transformed(5, 1) is point


def test_lognormal_refuses_offset_scales() -> None:
    with pytest.raises(UnitArithmeticError):
        LognormalDistribution(median=2, gsd=1.5).transformed(1, 273.15)
