

import logging
import re
import time
import uuid
from collections.abc import Callable, Iterable
from urllib.parse import urlsplit

from starlette.datastructures import Headers, MutableHeaders
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import PayloadTooLarge, error_body
from app.core.logging import request_id_ctx

log = logging.getLogger("app.access")
error_log = logging.getLogger("app.errors")

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{8,64}")


class RequestContextMiddleware:
    """Assigns/propagates ``X-Request-ID`` and writes one access-log line per request."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = Headers(scope=scope).get("x-request-id", "")
        # Only accept sane ids from the client – anything else could be used for log injection.
        request_id = incoming if _VALID_REQUEST_ID.fullmatch(incoming) else uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            path = scope["path"]
            if not path.endswith("/health"):
                log.info("%s %s -> %s (%.0f ms)", scope["method"], path, status, (time.perf_counter() - started) * 1000)
            request_id_ctx.reset(token)


class CatchAllErrorsMiddleware:
    """Turns unexpected exceptions into the JSON error body.

    Starlette's own 500 handler sits *outside* the CORS middleware, so a plain server error would reach
    the browser without CORS headers and surface as an opaque network error. Handling it here keeps
    the response inside the CORS layer.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            error_log.exception("Unhandled error while serving %s %s", scope["method"], scope["path"])
            if started:
                raise
            response = JSONResponse(
                error_body("internal_error", "Something went wrong on our side. Please try again."), status_code=500
            )
            await response(scope, receive, send)


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("Referrer-Policy", "no-referrer")
                # Every response is user-specific data; nothing should be cached by shared caches.
                headers.setdefault("Cache-Control", "no-store")
            await send(message)

        await self.app(scope, receive, send_wrapper)


class BodySizeLimitMiddleware:
    """Rejects oversized request bodies, both up-front (Content-Length) and while streaming."""

    def __init__(self, app: ASGIApp, *, limit_for: Callable[[Scope], int]) -> None:
        self.app = app
        self.limit_for = limit_for

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in _SAFE_METHODS:
            await self.app(scope, receive, send)
            return
        limit = self.limit_for(scope)
        declared = Headers(scope=scope).get("content-length")
        if declared is not None:
            try:
                too_large = int(declared) > limit
            except ValueError:
                response = JSONResponse(error_body("bad_request", "Invalid Content-Length header."), status_code=400)
                await response(scope, receive, send)
                return
            if too_large:
                response = JSONResponse(
                    error_body("payload_too_large", _too_large_message(limit)),
                    status_code=413,
                    headers={"Connection": "close"},
                )
                await response(scope, receive, send)
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:  # chunked upload without a Content-Length
                    raise PayloadTooLarge(_too_large_message(limit))
            return message

        await self.app(scope, limited_receive, send)


def _too_large_message(limit: int) -> str:
    return f"The request is larger than the {limit // (1024 * 1024)} MB limit."


class OriginCheckMiddleware:
    """CSRF defence for cookie authentication.

    Browsers attach an ``Origin`` header to every cross-site state-changing request. If it is present and is
    neither a configured frontend origin nor this server's own origin, the request is refused. Requests
    without ``Origin`` (curl, server-to-server) carry no ambient browser cookies and are allowed.
    """

    def __init__(self, app: ASGIApp, *, allowed_origins: Iterable[str]) -> None:
        self.app = app
        self.allowed = frozenset(allowed_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] not in _SAFE_METHODS:
            headers = Headers(scope=scope)
            origin = headers.get("origin")
            if origin is not None and origin not in self.allowed and urlsplit(origin).netloc != headers.get("host"):
                response = JSONResponse(
                    error_body(
                        "csrf_origin_mismatch", "This request was blocked because it came from an untrusted origin."
                    ),
                    status_code=403,
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
