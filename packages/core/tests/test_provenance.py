"""Provenance combination (docs/architecture.md section 10)."""

from dataclasses import dataclass

import pytest
from hypothesis import given
from hypothesis import strategies as st

from weta_core.provenance import (
    Layer,
    ProvenanceClass,
    TaintFlag,
    blocks_final,
    combine,
    combine_taint,
    own_taint,
)

P, T = ProvenanceClass, TaintFlag


@dataclass(frozen=True)
class Item:
    provenance: ProvenanceClass
    taint: frozenset[TaintFlag] = frozenset()


@pytest.mark.parametrize(
    ("cls", "expected"),
    [
        (P.OBSERVED, frozenset()),
        (P.IMPORTED, frozenset()),
        (P.DERIVED, frozenset()),
        (P.MODELLED, frozenset()),
        (P.USER_PROVIDED, frozenset({T.USER_PROVIDED})),
        (P.PREDICTED, frozenset({T.PREDICTED})),
        (P.SCENARIO_ASSUMPTION, frozenset({T.SCENARIO_ASSUMPTION})),
        (P.SYNTHETIC_DEMO, frozenset({T.SYNTHETIC})),
    ],
)
def test_taint_from_each_class(cls: ProvenanceClass, expected: frozenset[TaintFlag]) -> None:
    assert own_taint(cls) == expected


def test_layer_sets_class_and_inputs_set_taint() -> None:
    # A deterministic tonne-km built on a predicted tonnage is DERIVED with the predicted flag.
    cls, taint = combine(Layer.DERIVED, [Item(P.PREDICTED), Item(P.OBSERVED)])
    assert cls is P.DERIVED
    assert taint == frozenset({T.PREDICTED})


def test_taint_is_inherited_transitively() -> None:
    upstream = Item(P.DERIVED, frozenset({T.SYNTHETIC}))
    cls, taint = combine(Layer.MODELLED, [upstream])
    assert cls is P.MODELLED
    assert taint == frozenset({T.SYNTHETIC})


def test_ml_layer_outputs_are_predicted() -> None:
    assert Layer.PREDICTED.provenance is P.PREDICTED
    assert combine(Layer.PREDICTED, [Item(P.OBSERVED)])[0] is P.PREDICTED


def test_synthetic_blocks_final_reports() -> None:
    assert blocks_final(combine_taint([Item(P.SYNTHETIC_DEMO)]))
    assert not blocks_final(combine_taint([Item(P.PREDICTED), Item(P.USER_PROVIDED)]))


items = st.builds(
    Item,
    provenance=st.sampled_from(list(P)),
    taint=st.frozensets(st.sampled_from(list(T))),
)


@given(st.lists(items, max_size=6), st.lists(items, max_size=6))
def test_combination_is_order_independent_and_associative(a: list[Item], b: list[Item]) -> None:
    assert combine_taint(a + b) == combine_taint(b + a)
    assert combine_taint(a + b) == combine_taint(a) | combine_taint(b)
