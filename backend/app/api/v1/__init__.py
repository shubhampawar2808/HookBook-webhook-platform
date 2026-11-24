"""API v1 router aggregation."""

from fastapi import APIRouter

from app.api.v1 import (
    api_keys,
    auth,
    deliveries,
    endpoints,
    event_types,
    events,
    health,
    metrics,
    organizations,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(metrics.router)
api_router.include_router(auth.router)
api_router.include_router(organizations.router)
api_router.include_router(api_keys.router)
api_router.include_router(endpoints.router)
api_router.include_router(event_types.router)
api_router.include_router(events.router)
api_router.include_router(deliveries.router)
