"""Redis-backed (with in-memory fallback) fixed-window rate limiter."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_memory_buckets: dict[str, deque[float]] = defaultdict(deque)
_memory_lock = Lock()


def _client_ip(scope: Scope) -> str:
    headers = {
        k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])
    }
    forwarded = headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    client = scope.get("client")
    if client and client[0]:
        return str(client[0])
    return "unknown"


def _match_rule(path: str, method: str) -> tuple[int, int] | None:
    """Return (limit, window_seconds) for matching routes."""
    method = method.upper()
    if method == "POST" and path.endswith("/auth/login"):
        return (10, 60)
    if method == "POST" and path.endswith("/auth/register"):
        return (5, 60)
    if method == "POST" and (path.endswith("/events") or path.endswith("/events/")):
        return (120, 60)
    if method == "POST" and path.rstrip("/").endswith("/replay"):
        return (20, 60)
    if method == "POST" and path.endswith("/endpoints"):
        return (30, 60)
    return None


async def _redis_allow(key: str, limit: int, window: int) -> bool:
    try:
        from app.core.redis import get_redis

        client = get_redis()
        if client is None:
            return _memory_allow(key, limit, window)
        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        count, _ = await pipe.execute()
        return int(count) <= limit
    except Exception as exc:
        logger.warning("rate_limit_redis_fallback", error=type(exc).__name__)
        return _memory_allow(key, limit, window)


def _memory_allow(key: str, limit: int, window: int) -> bool:
    now = time.monotonic()
    with _memory_lock:
        bucket = _memory_buckets[key]
        while bucket and bucket[0] <= now - window:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


class RateLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        settings = get_settings()
        if settings.APP_ENV == "test" and not settings.RATE_LIMIT_ENABLED_IN_TEST:
            await self.app(scope, receive, send)
            return

        path = scope.get("path") or ""
        method = scope.get("method") or "GET"
        rule = _match_rule(path, method)
        if rule is None:
            await self.app(scope, receive, send)
            return

        limit, window = rule
        ip = _client_ip(scope)
        key = f"rl:{method}:{path}:{ip}"
        allowed = await _redis_allow(key, limit, window)
        if not allowed:
            body = (
                b'{"error":{"code":"rate_limited",'
                b'"message":"Too many requests. Try again later."}}'
            )
            await send(
                {
                    "type": "http.response.start",
                    "status": 429,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"retry-after", str(window).encode("ascii")),
                    ],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return

        await self.app(scope, receive, send)
