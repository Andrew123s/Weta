"""The API quantity object matches the shape in docs/api.md (conventions)."""

from uuid import UUID

import pytest
from pydantic import ValidationError

from weta_core.distributions import TriangularDistribution
from weta_core.provenance import ProvenanceClass, TaintFlag
from weta_core.quantity import Quantity
from weta_schemas.problem import ProblemDetail
from weta_schemas.quantity import QuantityOut, Taint

SOURCE = UUID("018f0000-0000-7000-8000-000000000001")
RESULT = UUID("018f0000-0000-7000-8000-000000000002")


def test_from_core_matches_documented_shape() -> None:
    core = Quantity(
        value=12.4,
        unit="t/yr",
        distribution=TriangularDistribution(min=10.1, mode=12.4, max=15.0),
        provenance=ProvenanceClass.DERIVED,
        source_id=SOURCE,
        taint=frozenset({TaintFlag.SCENARIO_ASSUMPTION, TaintFlag.USER_PROVIDED}),
    )
    payload = QuantityOut.from_core(core, result_id=RESULT).model_dump(mode="json")
    assert payload == {
        "value": 12.4,
        "unit": "t/yr",
        "uncertainty": {"kind": "triangular", "min": 10.1, "mode": 12.4, "max": 15.0},
        "provenance": "DERIVED",
        "taint": {
            "predicted": False,
            "scenario_assumption": True,
            "synthetic": False,
            "user_provided": True,
        },
        "source_ref": str(SOURCE),
        "result_id": str(RESULT),
    }


def test_taint_from_flags_covers_every_flag() -> None:
    taint = Taint.from_flags(frozenset(TaintFlag))
    assert all(taint.model_dump().values())


def test_unavailable_value_serializes_as_null_not_zero() -> None:
    core = Quantity(value=None, unit="kg", provenance=ProvenanceClass.OBSERVED)
    assert QuantityOut.from_core(core).model_dump()["value"] is None


@pytest.mark.parametrize("status", [200, 399, 600])
def test_problem_status_must_be_an_error(status: int) -> None:
    with pytest.raises(ValidationError):
        ProblemDetail(title="x", status=status)
