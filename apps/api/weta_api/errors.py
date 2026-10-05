"""Exception handlers that render every error as RFC 9457 problem details (docs/api.md).

Responses never contain stack traces or exception messages from unexpected errors; those go
to the log with the request id.
"""

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from weta_schemas.problem import PROBLEM_CONTENT_TYPE, FieldError, ProblemDetail

logger = logging.getLogger("weta.api.errors")


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def problem_response(problem: ProblemDetail, headers: dict[str, str] | None = None) -> JSONResponse:
    """Serialize a problem with the problem+json media type."""
    return JSONResponse(
        status_code=problem.status,
        content=problem.model_dump(mode="json", exclude_none=True),
        media_type=PROBLEM_CONTENT_TYPE,
        headers=headers,
    )


def _title(status: int) -> str:
    try:
        return HTTPStatus(status).phrase
    except ValueError:
        return "Error"


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render ``HTTPException`` (including routing 404 and 405) as a problem."""
    assert isinstance(exc, StarletteHTTPException)  # noqa: S101 - registered for this type only
    detail: str | None = exc.detail if isinstance(exc.detail, str) else None
    if detail == _title(exc.status_code):
        detail = None
    problem = ProblemDetail(
        title=_title(exc.status_code),
        status=exc.status_code,
        detail=detail,
        instance=request.url.path,
        request_id=_request_id(request),
    )
    return problem_response(problem, headers=getattr(exc, "headers", None))


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render request validation failures as a 422 problem with per-field errors.

    The offending input values are not echoed back, since they may be sensitive.
    """
    assert isinstance(exc, RequestValidationError)  # noqa: S101 - registered for this type only
    errors = [
        FieldError(loc=list(err.get("loc", ())), msg=str(err.get("msg", "")), type=err["type"])
        for err in exc.errors()
    ]
    problem = ProblemDetail(
        title="Request validation failed",
        status=HTTPStatus.UNPROCESSABLE_ENTITY,
        detail="One or more fields are invalid.",
        instance=request.url.path,
        errors=errors,
        request_id=_request_id(request),
    )
    return problem_response(problem)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last resort: log with the request id, return a generic 500 problem."""
    request_id = _request_id(request)
    logger.error(
        "unhandled exception", exc_info=exc, extra={"path": request.url.path, "rid": request_id}
    )
    problem = ProblemDetail(
        title="Internal Server Error",
        status=HTTPStatus.INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred. Quote the request id when reporting it.",
        instance=request.url.path,
        request_id=request_id,
    )
    headers = {"x-request-id": request_id} if request_id else None
    return problem_response(problem, headers=headers)


def install_exception_handlers(app: FastAPI) -> None:
    """Register the problem-details handlers on ``app``."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
