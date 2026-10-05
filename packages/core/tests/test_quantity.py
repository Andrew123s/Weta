"""The Quantity type: validation, conversion, and arithmetic that never drops information."""

import pytest
from pydantic import ValidationError

from weta_core.distributions import (
    LognormalDistribution,
    NormalDistribution,
    PointDistribution,
    TriangularDistribution,
)
from weta_core.errors import (
    DimensionalityError,
    MissingValueError,
    UncertaintyPropagationError,
    UnitArithmeticError,
)
from weta_core.provenance import ProvenanceClass as P
from weta_core.provenance import TaintFlag as T
from weta_core.quantity import DataQuality, Quantity


def q(value: float | None, unit: str, prov: P = P.OBSERVED, **kw: object) -> Quantity:
    return Quantity(value=value, unit=unit, provenance=prov, **kw)  # type: ignore[arg-type]


class TestValidation:
    @pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
    def test_rejects_non_finite(self, bad: float) -> None:
        with pytest.raises(ValidationError):
            q(bad, "kg")

    def test_rejects_unknown_unit(self) -> None:
        with pytest.raises(ValidationError):
            q(1.0, "furlongs_per_banana")

    def test_rejects_unknown_fields_and_is_frozen(self) -> None:
        with pytest.raises(ValidationError):
            Quantity(value=1, unit="kg", provenance=P.OBSERVED, colour="red")  # type: ignore[call-arg]
        quantity = q(1.0, "kg")
        with pytest.raises(ValidationError):
            quantity.value = 2.0  # type: ignore[misc]

    def test_provenance_is_required(self) -> None:
        with pytest.raises(ValidationError):
            Quantity(value=1.0, unit="kg")  # type: ignore[call-arg]

    def test_int_value_is_stored_as_float(self) -> None:
        assert isinstance(q(3, "kg").value, float)

    def test_unavailable_value_is_allowed_and_flagged(self) -> None:
        quantity = q(None, "kg")
        assert not quantity.is_available
        with pytest.raises(MissingValueError):
            quantity.magnitude_in("kg")

    def test_quality_is_scheme_neutral(self) -> None:
        quality = DataQuality(scheme="example-scheme", scheme_version="1", scores={"a": 2})
        assert q(1.0, "kg", quality=quality).quality == quality


class TestConversion:
    def test_value_and_distribution_convert_together(self) -> None:
        mass = q(2.0, "kg", distribution=TriangularDistribution(min=1, mode=2, max=4))
        in_t = mass.to("t")
        assert in_t.value == pytest.approx(0.002)
        assert in_t.unit == "t"
        assert in_t.distribution == TriangularDistribution(min=0.001, mode=0.002, max=0.004)

    def test_conversion_keeps_provenance_source_and_taint(self) -> None:
        mass = q(2.0, "kg", P.PREDICTED, taint=frozenset({T.SYNTHETIC}))
        converted = mass.to("g")
        assert converted.provenance is P.PREDICTED
        assert converted.taint == frozenset({T.SYNTHETIC})

    def test_offset_conversion_of_normal(self) -> None:
        temp = q(20.0, "degC", distribution=NormalDistribution(mean=20, sd=2))
        in_k = temp.to("K")
        assert in_k.value == pytest.approx(293.15)
        assert in_k.distribution == NormalDistribution(mean=293.15, sd=2)

    def test_offset_conversion_of_lognormal_refused(self) -> None:
        temp = q(20.0, "degC", distribution=LognormalDistribution(median=20, gsd=1.2))
        with pytest.raises(UnitArithmeticError):
            temp.to("K")

    def test_incompatible_conversion_raises(self) -> None:
        with pytest.raises(DimensionalityError):
            q(1.0, "kg").to("m")

    def test_to_canonical(self) -> None:
        rate = q(31.5576, "t/yr").to_canonical()  # 31.5576 t/yr = 1e-3 kg/s (Julian year)
        assert rate.unit == "kilogram / second"
        assert rate.value == pytest.approx(1e-3, rel=1e-12)

    def test_unavailable_value_converts_to_unavailable(self) -> None:
        assert q(None, "kg").to("t").value is None


class TestArithmetic:
    def test_sum_in_left_unit_and_derived(self) -> None:
        total = q(2.0, "kg") + q(500.0, "g")
        assert (total.value, total.unit) == (pytest.approx(2.5), "kg")
        assert total.provenance is P.DERIVED

    def test_difference(self) -> None:
        diff = q(1.0, "t") - q(250.0, "kg")
        assert (diff.value, diff.unit) == (pytest.approx(0.75), "t")

    def test_product_and_quotient(self) -> None:
        # 2 g/L x 3 m3 = 2 kg/m3 x 3 m3 = 6 kg (hand calculation)
        mass = q(2.0, "g/L") * q(3.0, "m**3")
        assert mass.magnitude_in("kg") == pytest.approx(6.0)
        ratio = q(2.0, "kg") / q(500.0, "g")
        assert ratio.magnitude_in("dimensionless") == pytest.approx(4.0)

    def test_taint_is_union_of_inputs(self) -> None:
        a = q(1.0, "kg", P.USER_PROVIDED)
        b = q(1.0, "kg", P.DERIVED, taint=frozenset({T.PREDICTED}))
        c = q(1.0, "kg", P.SYNTHETIC_DEMO)
        assert ((a + b) + c).taint == frozenset({T.USER_PROVIDED, T.PREDICTED, T.SYNTHETIC})

    def test_dimension_mismatch_raises(self) -> None:
        with pytest.raises(DimensionalityError):
            q(1.0, "kg") + q(1.0, "m")

    def test_offset_addition_refused(self) -> None:
        with pytest.raises(UnitArithmeticError):
            q(10.0, "degC") + q(10.0, "degC")

    def test_distribution_is_never_silently_dropped(self) -> None:
        uncertain = q(1.0, "kg", distribution=NormalDistribution(mean=1, sd=0.1))
        with pytest.raises(UncertaintyPropagationError):
            uncertain + q(1.0, "kg")
        with pytest.raises(UncertaintyPropagationError):
            q(1.0, "kg") * uncertain

    def test_point_distribution_counts_as_point(self) -> None:
        exact = q(1.0, "kg", distribution=PointDistribution())
        assert (exact + q(1.0, "kg")).value == pytest.approx(2.0)

    def test_missing_value_is_never_zero(self) -> None:
        with pytest.raises(MissingValueError):
            q(None, "kg") + q(1.0, "kg")

    def test_division_by_zero_raises(self) -> None:
        with pytest.raises(ZeroDivisionError):
            q(1.0, "kg") / q(0.0, "s")

    def test_non_quantity_operand_is_rejected(self) -> None:
        with pytest.raises(TypeError):
            q(1.0, "kg") + 1.0  # type: ignore[operator]
