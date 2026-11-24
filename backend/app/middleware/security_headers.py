"""HTTP security headers for browser and intermediary hardening."""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import get_settings


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        settings = get_settings()

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers") or [])
                extra = [
                    (b"x-content-type-options", b"nosniff"),
                    (b"referrer-policy", b"strict-origin-when-cross-origin"),
                    (b"x-frame-options", b"DENY"),
                    (b"permissions-policy", b"camera=(), microphone=(), geolocation=()"),
                    (
                        b"content-security-policy",
                        (
                            b"default-src 'none'; "
                            b"frame-ancestors 'none'; "
                            b"base-uri 'none'; "
                            b"form-action 'self'"
                        ),
                    ),
                ]
                if settings.is_production:
                    extra.append(
                        (
                            b"strict-transport-security",
                            b"max-age=31536000; includeSubDomains",
                        )
                    )
                # Avoid duplicating headers if already set
                existing = {h[0].lower() for h in headers}
                for key, value in extra:
                    if key not in existing:
                        headers.append((key, value))
                message = {**message, "headers": headers}
            await send(message)

        await self.app(scope, receive, send_wrapper)
