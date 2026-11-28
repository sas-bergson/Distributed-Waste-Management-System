"""Errors as RFC 9457 Problem Details (`application/problem+json`)."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

PROBLEM_BASE = "https://dwms.example/problems/"
# Where a validation error came from; not part of the field name shown to clients
_LOCATIONS = {"body", "query", "path", "header"}


class ProblemError(Exception):
    def __init__(
        self,
        status: int,
        slug: str,
        title: str,
        detail: str | None = None,
        *,
        errors: list[dict[str, str]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(detail or title)
        self.status = status
        self.slug = slug
        self.title = title
        self.detail = detail
        self.errors = errors
        self.headers = headers


def unauthorized(detail: str) -> ProblemError:
    return ProblemError(
        401, "unauthorized", "Unauthorized", detail, headers={"WWW-Authenticate": "Bearer"}
    )


def forbidden(detail: str) -> ProblemError:
    return ProblemError(403, "forbidden", "Forbidden", detail)


def not_found(detail: str) -> ProblemError:
    return ProblemError(404, "not-found", "Not found", detail)


def invalid(field: str, message: str) -> ProblemError:
    return ProblemError(
        422,
        "validation-error",
        "Validation error",
        "One or more fields are invalid.",
        errors=[{"field": field, "message": message}],
    )


def _response(problem: ProblemError, instance: str) -> JSONResponse:
    body: dict[str, Any] = {
        "type": PROBLEM_BASE + problem.slug,
        "title": problem.title,
        "status": problem.status,
        "instance": instance,
    }
    if problem.detail:
        body["detail"] = problem.detail
    if problem.errors:
        body["errors"] = problem.errors
    return JSONResponse(
        body,
        status_code=problem.status,
        headers=problem.headers,
        media_type="application/problem+json",
    )


def register_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(ProblemError)
    async def handle_problem(request: Request, exc: ProblemError) -> JSONResponse:
        return _response(exc, request.url.path)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = []
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"] if part not in _LOCATIONS)
            errors.append({"field": field or "body", "message": str(error["msg"])})
        problem = ProblemError(
            422,
            "validation-error",
            "Validation error",
            "One or more fields are invalid.",
            errors=errors,
        )
        return _response(problem, request.url.path)

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        problem = ProblemError(
            exc.status_code, "http-error", str(exc.detail), headers=dict(exc.headers or {})
        )
        return _response(problem, request.url.path)
