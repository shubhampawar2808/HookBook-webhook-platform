"""Reusable async Redis connection manager."""

from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_redis_client: aioredis.Redis | None = None


async def init_redis(settings: Settings | None = None) -> aioredis.Redis | None:
    """Create the shared Redis client during application startup.

    Phase 2 does not require Redis. When REDIS_REQUIRED is false, connection
    failures are logged and the API continues without a live Redis client.
    """
    global _redis_client
    settings = settings or get_settings()
    if _redis_client is None:
        client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        try:
            await client.ping()
            _redis_client = client
            logger.info("redis_client_initialized")
        except Exception as exc:
            await client.aclose()
            if settings.REDIS_REQUIRED:
                raise
            logger.warning(
                "redis_unavailable_continuing",
                error=type(exc).__name__,
            )
            _redis_client = None
            return None
    return _redis_client


async def close_redis() -> None:
    """Close the Redis client during application shutdown."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        logger.info("redis_client_closed")
    _redis_client = None


def get_redis() -> aioredis.Redis | None:
    """Return the shared Redis client, or None when Redis is optional and offline."""
    return _redis_client


async def check_redis_health() -> bool:
    """Return True if Redis responds to PING."""
    try:
        client = _redis_client
        if client is None:
            return False
        result = await client.ping()
        return bool(result)
    except Exception as exc:
        logger.warning("redis_health_check_failed", error=type(exc).__name__)
        return False
