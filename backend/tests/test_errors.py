"""Tests for centralized error handling."""

from __future__ import annotations

import pytest
from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import HookForgeError, NotFoundError


@pytest.mark.asyncio
async def test_not_found_route_returns_structured_error(
    client_no_db: AsyncClient,
) -> None:
    response = await client_no_db.get("/this-route-does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "http_error"
    assert "correlation_id" in body["error"]
    # Must not leak stack traces
    assert "traceback" not in body
    assert "exception" not in body


@pytest.mark.asyncio
async def test_unhandled_exception_hides_internals(configure_test_env) -> None:
    from unittest.mock import AsyncMock, patch

    from app.core.config import clear_settings_cache
    from app.main import create_app

    clear_settings_cache()

    with (
        patch("app.main.init_db", new_callable=AsyncMock),
        patch("app.main.close_db", new_callable=AsyncMock),
        patch("app.main.init_redis", new_callable=AsyncMock),
        patch("app.main.close_redis", new_callable=AsyncMock),
    ):
        app = create_app()
        boom = APIRouter()

        @boom.get("/__test/boom")
        async def boom_route() -> None:
            raise RuntimeError("sensitive internal detail should not leak")

        app.include_router(boom)

        # raise_app_exceptions=False so we assert the HTTP error envelope,
        # not the original exception re-raised by the test transport.
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/__test/boom")

    assert response.status_code == 500
    body = response.json()
    assert body["error"]["code"] == "internal_error"
    assert body["error"]["message"] == "An unexpected error occurred"
    assert "sensitive" not in response.text
    assert "RuntimeError" not in response.text


@pytest.mark.asyncio
async def test_hookforge_error_shape(configure_test_env) -> None:
    from unittest.mock import AsyncMock, patch

    from app.core.config import clear_settings_cache
    from app.main import create_app

    clear_settings_cache()

    with (
        patch("app.main.init_db", new_callable=AsyncMock),
        patch("app.main.close_db", new_callable=AsyncMock),
        patch("app.main.init_redis", new_callable=AsyncMock),
        patch("app.main.close_redis", new_callable=AsyncMock),
    ):
        app = create_app()
        router = APIRouter()

        @router.get("/__test/missing")
        async def missing() -> None:
            raise NotFoundError("Endpoint not found")

        app.include_router(router)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/__test/missing")

    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "not_found"
    assert body["error"]["message"] == "Endpoint not found"


def test_hookforge_error_attributes() -> None:
    err = HookForgeError("fail", code="custom", status_code=400, details={"field": "x"})
    assert err.message == "fail"
    assert err.code == "custom"
    assert err.details == {"field": "x"}
