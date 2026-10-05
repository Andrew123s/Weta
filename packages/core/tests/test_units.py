"""Unit handling: known conversions, round trips and dimensional errors.

Expected values come from unit definitions, not from the code under test:
1 t = 1000 kg (SI); 1 L = 1e-3 m3 (SI); T[K] = T[degC] + 273.15 (definition of Celsius);
1 year = 365.25 d (Julian year, assumption A-UNIT-01); 1 d = 86 400 s.
"""

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

from weta_core import units
from weta_core.errors import DimensionalityError, UnitParseError

JULIAN_YEAR_S = 365.25 * 86_400


@pytest.mark.parametrize(
    ("value", "from_unit", "to_unit", "expected"),
    [
        (1.0, "t", "kg", 1000.0),
        (2500.0, "g", "kg", 2.5),
        (1.0, "L", "m**3", 1e-3),
        (25.0, "degC", "K", 298.15),
        (1.0, "mg/L", "kg/m**3", 1e-3),
        (1.0, "t/yr", "kg/s", 1000.0 / JULIAN_YEAR_S),
        (12.0, "t/yr", "kg/d", 12_000.0 / 365.25),
        (50.0, "percent", "dimensionless", 0.5),
        (3.0, "kg/FU", "g/FU", 3000.0),
    ],
)
def test_known_conversions(value: float, from_unit: str, to_unit: str, expected: float) -> None:
    assert units.convert(value, from_unit, to_unit) == pytest.approx(expected, rel=1e-12)


ROUND_TRIP_PAIRS = [
    ("kg", "t"),
    ("g", "kg"),
    ("L", "m**3"),
    ("degC", "K"),
    ("t/yr", "kg/s"),
    ("mg/L", "kg/m**3"),
    ("km", "m"),
    ("kg/FU", "t/FU"),
]


@given(
    value=st.floats(min_value=-1e12, max_value=1e12, allow_nan=False, allow_infinity=False),
    pair=st.sampled_from(ROUND_TRIP_PAIRS),
)
def test_round_trip(value: float, pair: tuple[str, str]) -> None:
    a, b = pair
    back = units.convert(units.convert(value, a, b), b, a)
    assert math.isclose(back, value, rel_tol=1e-12, abs_tol=1e-9)


@pytest.mark.parametrize(
    ("from_unit", "to_unit"),
    [("kg", "m"), ("kg/s", "kg"), ("kg/FU", "kg"), ("K", "kg"), ("m**3", "m**2")],
)
def test_incompatible_dimensions_raise(from_unit: str, to_unit: str) -> None:
    with pytest.raises(DimensionalityError):
        units.convert(1.0, from_unit, to_unit)
    assert not units.is_compatible(from_unit, to_unit)


@pytest.mark.parametrize("bad", ["", "   ", "not_a_unit", "2 kg", "kg/", "**"])
def test_unparseable_units_raise(bad: str) -> None:
    with pytest.raises(UnitParseError):
        units.parse_unit(bad)
    assert not units.is_valid_unit(bad)


def test_affine_parameters() -> None:
    assert units.affine("degC", "K") == pytest.approx((1.0, 273.15))
    assert units.affine("kg", "t") == pytest.approx((1e-3, 0.0))


def test_canonical_units_are_si_base() -> None:
    assert units.canonical_unit("t/yr") == "kilogram / second"
    assert units.canonical_unit("degC") == "kelvin"
    assert units.canonical_unit("mg/L") == "kilogram / meter ** 3"


def test_functional_unit_is_its_own_dimension() -> None:
    assert units.dimensionality("kg/FU") == "[mass] / [functional_unit]"


def test_format_unit_round_trips_through_parser() -> None:
    parsed = units.parse_unit("kg * m / s**2")
    assert units.parse_unit(units.format_unit(parsed)) == parsed
