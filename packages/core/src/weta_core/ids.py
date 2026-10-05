"""UUIDv7 identifiers (RFC 9562), generated in the application so keys sort by time.

docs/data-model.md section 1. Not for use inside engines: engines are pure and never
read the clock (docs/development-rules.md B.1). Repositories and services call this.
"""

import secrets
import threading
import time
from uuid import UUID

_UNIX_TS_MS_BITS = 48
_RAND_A_BITS = 12
_RAND_B_BITS = 62
_VERSION = 0x7
_VARIANT = 0b10
_RAND_A_MAX = (1 << _RAND_A_BITS) - 1


class _MonotonicState:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.last_ms = -1
        self.rand_a = 0


_state = _MonotonicState()


def _compose(unix_ts_ms: int, rand_a: int, rand_b: int) -> UUID:
    value = unix_ts_ms & ((1 << _UNIX_TS_MS_BITS) - 1)
    value = (value << 4) | _VERSION
    value = (value << _RAND_A_BITS) | (rand_a & _RAND_A_MAX)
    value = (value << 2) | _VARIANT
    value = (value << _RAND_B_BITS) | (rand_b & ((1 << _RAND_B_BITS) - 1))
    return UUID(int=value)


def uuid7() -> UUID:
    """Return a new UUIDv7.

    Within one process, identifiers are strictly increasing: when several are created in
    the same millisecond, ``rand_a`` is used as a counter (RFC 9562 section 6.2, method 1).
    If the counter overflows, the timestamp field is advanced by one millisecond.
    """
    with _state.lock:
        now_ms = time.time_ns() // 1_000_000
        if now_ms > _state.last_ms:
            _state.last_ms = now_ms
            # Start the counter in the lower half so there is headroom before overflow.
            _state.rand_a = secrets.randbits(_RAND_A_BITS - 1)
        else:
            _state.rand_a += 1
            if _state.rand_a > _RAND_A_MAX:
                _state.last_ms += 1
                _state.rand_a = 0
        return _compose(_state.last_ms, _state.rand_a, secrets.randbits(_RAND_B_BITS))


def uuid7_timestamp_ms(value: UUID) -> int:
    """Return the Unix timestamp in milliseconds embedded in a UUIDv7."""
    if value.version != _VERSION:
        msg = f"not a UUIDv7: {value}"
        raise ValueError(msg)
    return value.int >> (128 - _UNIX_TS_MS_BITS)
