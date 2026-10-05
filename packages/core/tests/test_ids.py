"""UUIDv7 layout (RFC 9562 section 5.7) and monotonicity."""

import itertools
import time
import uuid

import pytest

from weta_core.ids import uuid7, uuid7_timestamp_ms


def test_version_variant_and_timestamp() -> None:
    before = time.time_ns() // 1_000_000
    value = uuid7()
    after = time.time_ns() // 1_000_000
    assert value.version == 7
    assert value.variant == uuid.RFC_4122
    # The counter may push the timestamp at most one millisecond ahead.
    assert before <= uuid7_timestamp_ms(value) <= after + 1


def test_strictly_increasing_within_process() -> None:
    ids = [uuid7() for _ in range(20_000)]
    assert all(a < b for a, b in itertools.pairwise(ids))
    assert len(set(ids)) == len(ids)


def test_timestamp_of_non_v7_is_rejected() -> None:
    with pytest.raises(ValueError, match="UUIDv7"):
        uuid7_timestamp_ms(uuid.uuid4())
