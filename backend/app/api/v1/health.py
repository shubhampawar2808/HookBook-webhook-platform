"""Health and readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.core.config import get_settings
from app.core.redis import check_redis_health
from app.db.session import check_database_health
from app.schemas.health import HealthResponse, ReadyResponse, ServiceStatus

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Liveness probe — process is up; does not check dependencies."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )


@router.get("/ready", response_model=ReadyResponse)
async def ready(response: Response) -> ReadyResponse:
    """Readiness probe — verifies PostgreSQL and Redis (when required)."""
    settings = get_settings()
    db_ok = await check_database_health()
    checks = [
        ServiceStatus(
            name="database",
            healthy=db_ok,
            detail=None if db_ok else "unreachable",
        ),
    ]
    if settings.REDIS_REQUIRED or settings.is_production:
        redis_ok = await check_redis_health()
        checks.append(
            ServiceStatus(
                name="redis",
                healthy=redis_ok,
                detail=None if redis_ok else "unreachable",
            )
        )
    else:
        redis_ok = await check_redis_health()
        checks.append(
            ServiceStatus(
                name="redis",
                healthy=redis_ok,
                detail=None if redis_ok else "unreachable (optional when REDIS_REQUIRED=false)",
            )
        )
        # Optional Redis: do not fail readiness solely on Redis in non-prod optional mode
        all_healthy = db_ok
        if not all_healthy:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadyResponse(
            status="ready" if all_healthy else "not_ready",
            checks=checks,
        )

    all_healthy = all(c.healthy for c in checks)
    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadyResponse(
        status="ready" if all_healthy else "not_ready",
        checks=checks,
    )
