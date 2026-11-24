"""Request correlation ID middleware (pure ASGI)."""

from __future__ import annotations

import uuid

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

CORRELATION_HEADER = "X-Correlation-ID"


class CorrelationIdMiddleware:
    """Attach a correlation ID to every request/response for log tracing."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        header_value = None
        for key, value in scope.get("headers", []):
            if key.decode("latin-1").lower() == "x-correlation-id":
                header_value = value.decode("latin-1").strip()
                break

        correlation_id = header_value or str(uuid.uuid4())
        scope.setdefault("state", {})["correlation_id"] = correlation_id

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        async def send_with_correlation(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append(
                    (
                        b"x-correlation-id",
                        correlation_id.encode("latin-1"),
                    )
                )
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_with_correlation)
