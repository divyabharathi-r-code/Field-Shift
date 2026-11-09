"""Single error envelope for all non-2xx responses (docs/03 §0.2).

Shape: { "error": { "code", "message", "details", "warnings" } }
Machine-readable codes let the UI render actionable messages instead of
stack traces. Registered exception handlers live in `install_handlers`.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# Canonical codes from docs/03 §0.2. Not all are raised in Phase 1; they are
# declared here so routers/tests share one source of truth.
VALIDATION_ERROR = "VALIDATION_ERROR"
NOT_FOUND = "NOT_FOUND"
OUT_OF_DOMAIN = "OUT_OF_DOMAIN"
INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
EXPLAIN_UNAVAILABLE = "EXPLAIN_UNAVAILABLE"
SOURCE_DISABLED = "SOURCE_DISABLED"
UPSTREAM_INVALID_RESPONSE = "UPSTREAM_INVALID_RESPONSE"
CACHE_ERROR = "CACHE_ERROR"


class FieldShiftError(Exception):
    """Domain error carrying an envelope-ready payload."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
        warnings: list[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.warnings = warnings or []


def _envelope(code: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details or {}, "warnings": []}}


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(FieldShiftError)
    async def _domain_error(_: Request, exc: FieldShiftError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(
                exc.code, exc.message, {"details": exc.details, "warnings": exc.warnings}
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=_envelope(VALIDATION_ERROR, "Request body/query failed schema validation.",
                              {"errors": exc.errors()}),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = NOT_FOUND if exc.status_code == 404 else "HTTP_ERROR"
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(code, str(exc.detail)),
        )
