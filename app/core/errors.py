

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        body["details"] = details
    return body


class ApiError(StarletteHTTPException):
    """Domain error rendered as the standard error body.

    It subclasses Starlette's ``HTTPException`` on purpose: FastAPI re-raises those untouched
    while parsing a request body, whereas any other exception becomes a generic 400.
    """

    default_status = 400
    default_code = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: Any = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code or self.default_status, detail=message, headers=headers)
        self.code = code or self.default_code
        self.message = message
        self.details = details


class BadRequest(ApiError):
    default_status, default_code = 400, "bad_request"


class Unauthorized(ApiError):
    default_status, default_code = 401, "unauthorized"


class Forbidden(ApiError):
    default_status, default_code = 403, "forbidden"


class NotFound(ApiError):
    default_status, default_code = 404, "not_found"


class Conflict(ApiError):
    default_status, default_code = 409, "conflict"


class PayloadTooLarge(ApiError):
    default_status, default_code = 413, "payload_too_large"


class UnsupportedMediaType(ApiError):
    default_status, default_code = 415, "unsupported_media_type"


class Unprocessable(ApiError):
    default_status, default_code = 422, "unprocessable"


class TooManyRequests(ApiError):
    default_status, default_code = 429, "too_many_requests"


_STATUS_CODES = {
    401: ("unauthorized", "You need to sign in to continue."),
    403: ("forbidden", "You don't have permission to do that."),
    404: ("not_found", "The requested resource was not found."),
    405: ("method_not_allowed", "This method is not allowed for the requested resource."),
    413: ("payload_too_large", "The request is too large."),
    415: ("unsupported_media_type", "Unsupported content type."),
}


async def _http_exception_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    if isinstance(exc, ApiError):
        code, message, details = exc.code, exc.message, exc.details
    else:
        # Framework-raised errors (unknown route, wrong method…) only carry the bare HTTP phrase ("Not Found"):
        # use our own wording for the statuses we know, and the framework's text for anything else.
        known = exc.status_code in _STATUS_CODES
        code, fallback = _STATUS_CODES.get(exc.status_code, ("http_error", "The request could not be completed."))
        message = fallback if known or not (isinstance(exc.detail, str) and exc.detail) else exc.detail
        details = None
    return JSONResponse(
        error_body(code, message, details), status_code=exc.status_code, headers=getattr(exc, "headers", None)
    )


def _field_name(loc: tuple[Any, ...]) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "form")]
    return ".".join(parts) or "request"


async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"field": _field_name(tuple(e.get("loc", ()))), "message": _clean_message(e), "type": e.get("type", "")}
        for e in exc.errors()
    ]
    first = details[0] if details else {"field": "request", "message": "Invalid request."}
    # Messages raised by our own validators are already user-facing sentences – show them as is.
    own = exc.errors()[0].get("type") == "value_error" if exc.errors() else False
    message = first["message"] if own else f"Invalid value for “{first['field']}”: {first['message']}"
    return JSONResponse(error_body("validation_error", message, details), status_code=422)


def _clean_message(error: Any) -> str:
    msg = str(error.get("msg", "Invalid value"))
    return msg.removeprefix("Value error, ")


def install_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_handler)  # type: ignore[arg-type]
