"""The quantity object returned by the API (docs/api.md, conventions).

Every numeric field in an API response is a ``QuantityOut``: value, unit, uncertainty,
provenance class, taint flags, and references to its source and to the stored result.
"""

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from weta_core.distributions import Distribution
from weta_core.provenance import ProvenanceClass, TaintFlag
from weta_core.quantity import Quantity


class Taint(BaseModel):
    """Which kinds of input a value was built on (docs/architecture.md section 10)."""

    model_config = ConfigDict(extra="forbid")

    predicted: bool = False
    scenario_assumption: bool = False
    synthetic: bool = False
    user_provided: bool = False

    @classmethod
    def from_flags(cls, flags: frozenset[TaintFlag]) -> Self:
        """Build from the core taint flag set."""
        return cls(**{flag.value: True for flag in flags})


class QuantityOut(BaseModel):
    """A quantity as serialized in API responses."""

    model_config = ConfigDict(extra="forbid")

    value: float | None
    unit: str
    uncertainty: Distribution | None = None
    provenance: ProvenanceClass
    taint: Taint
    source_ref: UUID | None = None
    result_id: UUID | None = None

    @classmethod
    def from_core(cls, q: Quantity, *, result_id: UUID | None = None) -> Self:
        """Serialize a core ``Quantity``."""
        return cls(
            value=q.value,
            unit=q.unit,
            uncertainty=q.distribution,
            provenance=q.provenance,
            taint=Taint.from_flags(q.taint),
            source_ref=q.source_id,
            result_id=result_id,
        )
