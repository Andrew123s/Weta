"""Structured JSON logging with the request id (docs/development-rules.md section D).

Never log passwords, tokens or uploaded file contents.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

_RESERVED = set(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """One JSON object per line: time, level, logger, message, request_id and extras."""

    def format(self, record: logging.LogRecord) -> str:
        """Render ``record`` as a single JSON line."""
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        for key, value in vars(record).items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str) -> None:
    """Route the ``weta`` loggers to stdout as JSON lines."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("weta")
    root.handlers[:] = [handler]
    root.setLevel(level)
    root.propagate = False
