"""Security headers on every response (docs/security.md section 5)."""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# The API serves JSON only, so the policy forbids everything. The interactive OpenAPI page
# loads its assets from a CDN and is served without CSP in development only.
API_CSP = "default-src 'none'; frame-ancestors 'none'; base-uri 'none'"

_STATIC_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
    (b"cross-origin-opener-policy", b"same-origin"),
)


class SecurityHeadersMiddleware:
    """Adds security headers. HSTS is set by the TLS-terminating reverse proxy."""

    def __init__(self, app: ASGIApp, *, csp_exempt_paths: frozenset[str] = frozenset()) -> None:
        self.app = app
        self.csp_exempt_paths = csp_exempt_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        exempt = scope.get("path") in self.csp_exempt_paths

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(_STATIC_HEADERS)
                if not exempt:
                    headers.append((b"content-security-policy", API_CSP.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)
