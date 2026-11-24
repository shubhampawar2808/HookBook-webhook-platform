"""Application exception hierarchy and FastAPI handlers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger

logger = get_logger(__name__)


class HookForgeError(Exception):
    """Base application error."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "application_error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(HookForgeError):
    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        super().__init__(
            message,
            code=kwargs.pop("code", "not_found"),
            status_code=status.HTTP_404_NOT_FOUND,
            **kwargs,
        )


class ConflictError(HookForgeError):
    def __init__(self, message: str = "Conflict", **kwargs: Any) -> None:
        super().__init__(
            message,
            code=kwargs.pop("code", "conflict"),
            status_code=status.HTTP_409_CONFLICT,
            **kwargs,
        )


class UnauthorizedError(HookForgeError):
    def __init__(self, message: str = "Unauthorized", **kwargs: Any) -> None:
        super().__init__(
            message,
            code=kwargs.pop("code", "unauthorized"),
            status_code=status.HTTP_401_UNAUTHORIZED,
            **kwargs,
        )


class ForbiddenError(HookForgeError):
    def __init__(self, message: str = "Forbidden", **kwargs: Any) -> None:
        super().__init__(
            message,
            code=kwargs.pop("code", "forbidden"),
            status_code=status.HTTP_403_FORBIDDEN,
            **kwargs,
        )


class ServiceUnavailableError(HookForgeError):
    def __init__(self, message: str = "Service unavailable", **kwargs: Any) -> None:
        super().__init__(
            message,
            code=kwargs.pop("code", "service_unavailable"),
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            **kwargs,
        )


def _error_body(
    *,
    code: str,
    message: str,
    correlation_id: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
        }
    }
    if correlation_id:
        body["error"]["correlation_id"] = correlation_id
    if details:
        body["error"]["details"] = details
    return body


def _correlation_id(request: Request) -> str | None:
    return getattr(request.state, "correlation_id", None)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach centralized exception handlers to the FastAPI app."""

    @app.exception_handler(HookForgeError)
    async def hookforge_error_handler(request: Request, exc: HookForgeError) -> JSONResponse:
        correlation_id = _correlation_id(request)
        logger.warning(
            "application_error",
            code=exc.code,
            message=exc.message,
            status_code=exc.status_code,
            correlation_id=correlation_id,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(
                code=exc.code,
                message=exc.message,
                correlation_id=correlation_id,
                details=exc.details or None,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        correlation_id = _correlation_id(request)
        detail = exc.detail
        message = detail if isinstance(detail, str) else "Request failed"
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(
                code="http_error",
                message=message,
                correlation_id=correlation_id,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        correlation_id = _correlation_id(request)
        # Expose field paths only — never raw input bodies that may contain secrets
        safe_details = [
            {
                "loc": [str(part) for part in err.get("loc", ())],
                "msg": err.get("msg", "Invalid value"),
                "type": err.get("type", "value_error"),
            }
            for err in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                code="validation_error",
                message="Request validation failed",
                correlation_id=correlation_id,
                details={"errors": safe_details},
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        correlation_id = _correlation_id(request)
        logger.exception(
            "unhandled_exception",
            correlation_id=correlation_id,
            path=str(request.url.path),
            exc_type=type(exc).__name__,
        )
        # Never expose internal exception details to clients
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                code="internal_error",
                message="An unexpected error occurred",
                correlation_id=correlation_id,
            ),
        )
