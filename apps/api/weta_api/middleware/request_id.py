"""Request id middleware: accept or assign an id, expose it, and log one line per request."""

import logging
import re
import time
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from weta_api.log import request_id_var
from weta_core.ids import uuid7

HEADER = "x-request-id"
_VALID_INCOMING = re.compile(r"^[A-Za-z0-9._\-]{8,128}$")

logger = logging.getLogger("weta.api.request")


class RequestIdMiddleware:
    """Pure ASGI middleware so the id is available to every layer, including error handlers.

    An incoming ``X-Request-ID`` is reused only if it is a short, safe token; otherwise a new
    UUIDv7 is assigned. The id is stored in ``scope["state"]`` and in a context variable.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = _header(scope, HEADER)
        request_id = incoming if incoming and _VALID_INCOMING.match(incoming) else str(uuid7())
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_var.set(request_id)
        started = time.perf_counter()
        status_holder: dict[str, int] = {}

        async def send_with_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
                headers = list(message.get("headers", []))
                headers.append((HEADER.encode(), request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            logger.info(
                "request",
                extra={
                    "method": scope.get("method"),
                    "path": scope.get("path"),
                    "status": status_holder.get("status"),
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            request_id_var.reset(token)


def _header(scope: Scope, name: str) -> str | None:
    raw: Any
    for key, raw in scope.get("headers", []):
        if key.decode("latin-1").lower() == name:
            return str(raw.decode("latin-1"))
    return None
