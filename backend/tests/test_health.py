"""Tests for health and readiness endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client_no_db: AsyncClient) -> None:
    response = await client_no_db.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["app"] == "HookForge"
    assert "version" in data
    assert data["environment"] == "test"


@pytest.mark.asyncio
async def test_health_endpoint_v1(client_no_db: AsyncClient) -> None:
    response = await client_no_db.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_ready_when_dependencies_healthy(client_no_db: AsyncClient) -> None:
    with (
        patch("app.api.v1.health.check_database_health", new_callable=AsyncMock) as db,
        patch("app.api.v1.health.check_redis_health", new_callable=AsyncMock) as redis,
    ):
        db.return_value = True
        redis.return_value = True
        response = await client_no_db.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert all(c["healthy"] for c in data["checks"])


@pytest.mark.asyncio
async def test_ready_when_database_unhealthy(client_no_db: AsyncClient) -> None:
    with (
        patch("app.api.v1.health.check_database_health", new_callable=AsyncMock) as db,
        patch("app.api.v1.health.check_redis_health", new_callable=AsyncMock) as redis,
    ):
        db.return_value = False
        redis.return_value = True
        response = await client_no_db.get("/api/v1/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "not_ready"
    db_check = next(c for c in data["checks"] if c["name"] == "database")
    assert db_check["healthy"] is False


@pytest.mark.asyncio
async def test_correlation_id_header(client_no_db: AsyncClient) -> None:
    response = await client_no_db.get("/health", headers={"X-Correlation-ID": "test-corr-123"})
    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == "test-corr-123"
