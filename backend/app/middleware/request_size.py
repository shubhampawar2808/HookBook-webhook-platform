"""Reject oversized request bodies early (Content-Length and streaming)."""

from __future__ import annotations

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings


def _too_large_response() -> tuple[dict, dict]:
    start = {
        "type": "http.response.start",
        "status": 413,
        "headers": [(b"content-type", b"application/json")],
    }
    body = {
        "type": "http.response.body",
        "body": (b'{"error":{"code":"payload_too_large",' b'"message":"Request body too large"}}'),
    }
    return start, body


def _bad_length_response() -> tuple[dict, dict]:
    start = {
        "type": "http.response.start",
        "status": 400,
        "headers": [(b"content-type", b"application/json")],
    }
    body = {
        "type": "http.response.body",
        "body": (
            b'{"error":{"code":"invalid_content_length",'
            b'"message":"Invalid Content-Length header"}}'
        ),
    }
    return start, body


class RequestSizeLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_size: int | None = None) -> None:
        self.app = app
        self.max_body_size = max_body_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        max_size = self.max_body_size or get_settings().MAX_REQUEST_BODY_BYTES
        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])
        }
        content_length = headers.get("content-length")
        if content_length is not None:
            try:
                length = int(content_length)
            except ValueError:
                start, body = _bad_length_response()
                await send(start)
                await send(body)
                return
            if length < 0:
                start, body = _bad_length_response()
                await send(start)
                await send(body)
                return
            if length > max_size:
                start, body = _too_large_response()
                await send(start)
                await send(body)
                return

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                chunk = message.get("body", b"") or b""
                received += len(chunk)
                if received > max_size:
                    raise _BodyTooLargeError()
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _BodyTooLargeError:
            start, body = _too_large_response()
            await send(start)
            await send(body)


class _BodyTooLargeError(Exception):
    pass
