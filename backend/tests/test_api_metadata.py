"""Tests for API metadata and OpenAPI surface."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_openapi_available_in_non_production(client_no_db: AsyncClient) -> None:
    response = await client_no_db.get("/openapi.json")
    assert response.status_code == 200
    payload = response.json()
    assert payload["info"]["title"] == "HookForge"
    assert "version" in payload["info"]


@pytest.mark.asyncio
async def test_docs_available_in_non_production(client_no_db: AsyncClient) -> None:
    response = await client_no_db.get("/docs")
    assert response.status_code == 200
