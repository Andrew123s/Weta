"""Canonical JSON and content hashing.

docs/architecture.md section 6. A node run is identified by

    input_hash = sha256(node_id, node_version, canonical_json(inputs), method_params,
                        dataset_version_ids, model_version_id, seed)

The hash must be identical on every platform and Python process, so canonical JSON is
strictly defined:

- object keys are strings, sorted by code point; no insignificant whitespace; UTF-8;
- strings are NFC-normalized;
- floats use Python's shortest round-trip representation (platform independent);
  ``-0.0`` is written as ``0.0``; NaN and infinities are rejected;
- enums are written as their value, UUIDs as lowercase hyphenated strings,
  dates and times as ISO 8601 (datetimes must be timezone-aware and are written in UTC);
- sets are written as lists sorted by each element's canonical JSON;
- tuples and lists are written as lists; pydantic models as their field mapping.

Anything else (bytes, Decimal, arbitrary objects) raises ``CanonicalizationError``.
"""

import datetime as dt
import hashlib
import json
import math
import unicodedata
from collections.abc import Iterable, Mapping
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from weta_core.errors import CanonicalizationError

HASH_ALGORITHM = "sha256"


def canonicalize(obj: Any) -> Any:  # noqa: PLR0912 - one flat dispatch over JSON types
    """Convert ``obj`` to plain JSON types following the canonical rules above."""
    result: Any
    if obj is None or isinstance(obj, bool):
        result = obj
    elif isinstance(obj, Enum):
        result = canonicalize(obj.value)
    elif isinstance(obj, int):
        result = obj
    elif isinstance(obj, float):
        if not math.isfinite(obj):
            msg = f"non-finite float {obj!r} cannot be hashed"
            raise CanonicalizationError(msg)
        result = 0.0 if obj == 0 else obj
    elif isinstance(obj, str):
        result = unicodedata.normalize("NFC", obj)
    elif isinstance(obj, UUID):
        result = str(obj)
    elif isinstance(obj, dt.datetime):
        if obj.tzinfo is None or obj.utcoffset() is None:
            msg = "naive datetimes are ambiguous and cannot be hashed"
            raise CanonicalizationError(msg)
        result = obj.astimezone(dt.UTC).isoformat()
    elif isinstance(obj, dt.date):
        result = obj.isoformat()
    elif isinstance(obj, BaseModel):
        result = canonicalize(dict(obj))
    elif isinstance(obj, Mapping):
        result = _canonical_mapping(obj)
    elif isinstance(obj, set | frozenset):
        items = [canonicalize(item) for item in obj]
        result = sorted(items, key=_dumps)
    elif isinstance(obj, list | tuple):
        result = [canonicalize(item) for item in obj]
    else:
        msg = f"type {type(obj).__name__} has no canonical JSON form"
        raise CanonicalizationError(msg)
    return result


def _canonical_mapping(obj: Mapping[Any, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in obj.items():
        if isinstance(key, Enum):
            key = key.value  # noqa: PLW2901 - normalizing the loop variable is the intent
        if not isinstance(key, str):
            msg = f"mapping keys must be strings, got {type(key).__name__}"
            raise CanonicalizationError(msg)
        norm = unicodedata.normalize("NFC", key)
        if norm in out:
            msg = f"duplicate key after NFC normalization: {norm!r}"
            raise CanonicalizationError(msg)
        out[norm] = canonicalize(value)
    return out


def _dumps(obj: Any) -> str:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def canonical_json(obj: Any) -> str:
    """Canonical JSON text of ``obj``."""
    return _dumps(canonicalize(obj))


def sha256_hex(text: str) -> str:
    """Lowercase hex SHA-256 of the UTF-8 encoding of ``text``."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def content_hash(obj: Any) -> str:
    """SHA-256 of the canonical JSON of ``obj``."""
    return sha256_hex(canonical_json(obj))


def compute_input_hash(
    *,
    node_id: str,
    node_version: str,
    inputs: Any,
    method_params: Any,
    dataset_version_ids: Iterable[UUID] = (),
    model_version_id: UUID | None = None,
    seed: int | None = None,
) -> str:
    """The run identity of a node execution (docs/architecture.md section 6).

    ``dataset_version_ids`` is treated as a set: order does not change the hash.
    """
    return content_hash(
        {
            "node_id": node_id,
            "node_version": node_version,
            "inputs": inputs,
            "method_params": method_params,
            "dataset_version_ids": frozenset(dataset_version_ids),
            "model_version_id": model_version_id,
            "seed": seed,
        }
    )
