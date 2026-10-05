"""Canonical JSON and input hashing: exact text, platform and process stability.

Expected canonical strings are written by hand from the rules in ``weta_core.hashing``. The
golden SHA-256 was computed with ``hashlib`` directly from the hand-written string, so it does
not depend on the code under test. CI runs this file on Windows and Linux.
"""

import datetime as dt
import hashlib
import os
import subprocess
import sys
import textwrap
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

import pytest

from weta_core.errors import CanonicalizationError
from weta_core.hashing import canonical_json, compute_input_hash, content_hash
from weta_core.provenance import ProvenanceClass, TaintFlag
from weta_core.quantity import Quantity

DV1 = UUID("00000000-0000-7000-8000-000000000001")
DV2 = UUID("00000000-0000-7000-8000-000000000002")

GOLDEN_TEXT = (
    '{"dataset_version_ids":["00000000-0000-7000-8000-000000000001",'
    '"00000000-0000-7000-8000-000000000002"],'
    '"inputs":{"mass":{"distribution":null,"provenance":"OBSERVED","quality":null,'
    '"source_id":null,"taint":[],"unit":"t/yr","value":12.4}},'
    '"method_params":{"k":0.5},"model_version_id":null,"node_id":"demo.example",'
    '"node_version":"1.0.0","seed":42}'
)
GOLDEN_HASH = "c6694c35568d89337a04db60ef08f6fe040f4dad499f1eda8083bbe433ce88e7"


def golden_hash_inputs() -> dict[str, object]:
    return {
        "node_id": "demo.example",
        "node_version": "1.0.0",
        "inputs": {"mass": Quantity(value=12.4, unit="t/yr", provenance=ProvenanceClass.OBSERVED)},
        "method_params": {"k": 0.5},
        "dataset_version_ids": [DV2, DV1],
        "model_version_id": None,
        "seed": 42,
    }


class Colour(StrEnum):
    RED = "red"


class TestCanonicalJson:
    def test_sorting_whitespace_and_literals(self) -> None:
        obj = {"b": 1, "a": [1.5, -0.0, None, True, False], "c": "x"}
        assert canonical_json(obj) == '{"a":[1.5,0.0,null,true,false],"b":1,"c":"x"}'

    def test_keys_sort_by_code_point(self) -> None:
        assert canonical_json({"a": 1, "B": 2, "_": 3}) == '{"B":2,"_":3,"a":1}'

    def test_unicode_is_nfc_normalized_and_not_escaped(self) -> None:
        decomposed = "é"  # e + combining acute accent
        composed = "é"
        assert canonical_json(decomposed) == f'"{composed}"'
        assert canonical_json({decomposed: 1}) == canonical_json({composed: 1})

    @pytest.mark.parametrize(
        ("value", "text"),
        [(0.1, "0.1"), (1e-7, "1e-07"), (1e22, "1e+22"), (2.5, "2.5"), (3, "3"), (-0.0, "0.0")],
    )
    def test_float_representation(self, value: float, text: str) -> None:
        assert canonical_json(value) == text

    def test_special_types(self) -> None:
        aware = dt.datetime(2026, 1, 1, 12, 0, tzinfo=dt.timezone(dt.timedelta(hours=2)))
        obj = {
            "colour": Colour.RED,
            "id": DV1,
            "when": aware,
            "day": dt.date(2026, 10, 5),
            "set": frozenset({"b", "a"}),
            "tuple": (1, 2),
        }
        assert canonical_json(obj) == (
            '{"colour":"red","day":"2026-10-05","id":"00000000-0000-7000-8000-000000000001",'
            '"set":["a","b"],"tuple":[1,2],"when":"2026-01-01T10:00:00+00:00"}'
        )

    def test_quantity_serialization(self) -> None:
        quantity = Quantity(
            value=12.4,
            unit="t/yr",
            provenance=ProvenanceClass.PREDICTED,
            taint=frozenset({TaintFlag.USER_PROVIDED, TaintFlag.SYNTHETIC}),
        )
        assert canonical_json(quantity) == (
            '{"distribution":null,"provenance":"PREDICTED","quality":null,"source_id":null,'
            '"taint":["synthetic","user_provided"],"unit":"t/yr","value":12.4}'
        )

    @pytest.mark.parametrize(
        "bad",
        [
            float("nan"),
            float("inf"),
            dt.datetime(2026, 1, 1),  # noqa: DTZ001 - a naive datetime is the point of the test
            b"bytes",
            Decimal("1.0"),
            {1: "non-string key"},
            object(),
        ],
    )
    def test_unhashable_values_rejected(self, bad: object) -> None:
        with pytest.raises(CanonicalizationError):
            canonical_json(bad)

    def test_keys_colliding_after_normalization_rejected(self) -> None:
        with pytest.raises(CanonicalizationError):
            canonical_json({"é": 1, "é": 2})


class TestInputHash:
    def test_golden_text_hash_is_hashlib_sha256(self) -> None:
        assert hashlib.sha256(GOLDEN_TEXT.encode("utf-8")).hexdigest() == GOLDEN_HASH

    def test_golden_value(self) -> None:
        inputs = golden_hash_inputs()
        canonical_payload = {
            **inputs,
            "dataset_version_ids": frozenset(inputs["dataset_version_ids"]),  # type: ignore[arg-type]
        }
        assert canonical_json(canonical_payload) == GOLDEN_TEXT
        assert compute_input_hash(**inputs) == GOLDEN_HASH  # type: ignore[arg-type]

    def test_dataset_version_order_does_not_matter(self) -> None:
        inputs = golden_hash_inputs()
        reordered = {**inputs, "dataset_version_ids": [DV1, DV2]}
        assert compute_input_hash(**reordered) == GOLDEN_HASH  # type: ignore[arg-type]

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("node_version", "1.0.1"),
            ("seed", 43),
            ("model_version_id", DV1),
            ("method_params", {"k": 0.51}),
            ("dataset_version_ids", [DV1]),
        ],
    )
    def test_any_change_changes_the_hash(self, field: str, value: object) -> None:
        changed = {**golden_hash_inputs(), field: value}
        assert compute_input_hash(**changed) != GOLDEN_HASH  # type: ignore[arg-type]

    def test_content_hash_matches_sha256_of_canonical_json(self) -> None:
        obj = {"x": [1, 2.5]}
        expected = hashlib.sha256(b'{"x":[1,2.5]}').hexdigest()
        assert content_hash(obj) == expected

    def test_stable_across_processes_with_different_hash_seeds(self) -> None:
        # Set iteration order depends on PYTHONHASHSEED; the canonical hash must not.
        script = textwrap.dedent(
            """
            from weta_core.hashing import content_hash
            print(content_hash({"s": frozenset({"alpha", "beta", "gamma", "delta"})}))
            """
        )
        results = set()
        for seed in ("0", "1", "12345"):
            env = {**os.environ, "PYTHONHASHSEED": seed}
            out = subprocess.run(  # noqa: S603 - fixed interpreter and script
                [sys.executable, "-c", script], capture_output=True, text=True, env=env, check=True
            )
            results.add(out.stdout.strip())
        assert len(results) == 1
