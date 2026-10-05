"""Provenance classes, taint flags and the combination rule.

docs/architecture.md section 10. Every stored numeric fact has a provenance class. A node's
output class is set by the node's layer; the classes and taints of its inputs are carried
forward as taint flags, so a deterministic result built on a prediction stays visibly
dependent on that prediction.
"""

from collections.abc import Iterable
from enum import StrEnum
from typing import Protocol


class ProvenanceClass(StrEnum):
    """The eight provenance classes (PostgreSQL enum ``provenance_class``)."""

    OBSERVED = "OBSERVED"
    USER_PROVIDED = "USER_PROVIDED"
    IMPORTED = "IMPORTED"
    DERIVED = "DERIVED"
    MODELLED = "MODELLED"
    PREDICTED = "PREDICTED"
    SCENARIO_ASSUMPTION = "SCENARIO_ASSUMPTION"
    SYNTHETIC_DEMO = "SYNTHETIC_DEMO"


class TaintFlag(StrEnum):
    """Flags inherited by a result from the classes of the inputs it was built on."""

    PREDICTED = "predicted"
    SCENARIO_ASSUMPTION = "scenario_assumption"
    SYNTHETIC = "synthetic"
    USER_PROVIDED = "user_provided"


class Layer(StrEnum):
    """Layer of a calculation node; it fixes the provenance class of the node's outputs."""

    DERIVED = "DERIVED"
    MODELLED = "MODELLED"
    PREDICTED = "PREDICTED"

    @property
    def provenance(self) -> ProvenanceClass:
        """The provenance class stamped on every output quantity of a node in this layer."""
        return ProvenanceClass(self.value)


# Which input classes taint a downstream result, and with which flag.
TAINT_FROM_CLASS: dict[ProvenanceClass, TaintFlag] = {
    ProvenanceClass.PREDICTED: TaintFlag.PREDICTED,
    ProvenanceClass.SCENARIO_ASSUMPTION: TaintFlag.SCENARIO_ASSUMPTION,
    ProvenanceClass.SYNTHETIC_DEMO: TaintFlag.SYNTHETIC,
    ProvenanceClass.USER_PROVIDED: TaintFlag.USER_PROVIDED,
}

# Taints that block a report from being issued with status FINAL (architecture section 10, rule 3).
BLOCKING_TAINTS: frozenset[TaintFlag] = frozenset({TaintFlag.SYNTHETIC})


class HasProvenance(Protocol):
    """Anything that carries a provenance class and taint flags (for example a ``Quantity``)."""

    @property
    def provenance(self) -> ProvenanceClass: ...

    @property
    def taint(self) -> frozenset[TaintFlag]: ...


def own_taint(provenance: ProvenanceClass, taint: Iterable[TaintFlag] = ()) -> frozenset[TaintFlag]:
    """Taint flags a value passes on downstream: its inherited flags plus the flag of its class."""
    flags = set(taint)
    flag = TAINT_FROM_CLASS.get(provenance)
    if flag is not None:
        flags.add(flag)
    return frozenset(flags)


def combine_taint(inputs: Iterable[HasProvenance]) -> frozenset[TaintFlag]:
    """Union of the taint each input passes on (architecture section 10, rule 2)."""
    flags: set[TaintFlag] = set()
    for item in inputs:
        flags |= own_taint(item.provenance, item.taint)
    return frozenset(flags)


def combine(
    layer: Layer, inputs: Iterable[HasProvenance]
) -> tuple[ProvenanceClass, frozenset[TaintFlag]]:
    """Provenance of a node output: class from the node layer, taint from the inputs."""
    return layer.provenance, combine_taint(inputs)


def blocks_final(taint: Iterable[TaintFlag]) -> bool:
    """True if a result with these taints must not appear in a report issued as FINAL."""
    return not BLOCKING_TAINTS.isdisjoint(taint)
