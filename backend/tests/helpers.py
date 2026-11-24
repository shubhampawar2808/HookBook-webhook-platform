"""Test helpers for registering tenants and authenticating."""

from __future__ import annotations

from typing import Any

from httpx import AsyncClient


async def register_org(
    client: AsyncClient,
    *,
    slug: str,
    email: str = "owner@example.com",
    password: str = "secure-password-1",
    name: str | None = None,
    full_name: str = "Owner User",
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": name or f"Org {slug}",
            "organization_slug": slug,
            "email": email,
            "password": password,
            "full_name": full_name,
        },
    )
    assert response.status_code == 201, response.text
    token = response.json()["access_token"]
    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text
    return {"token": token, "me": me.json(), "auth": {"Authorization": f"Bearer {token}"}}


async def create_api_key(client: AsyncClient, auth: dict[str, str]) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/api-keys",
        headers=auth,
        json={"name": "publish-key"},
    )
    assert response.status_code == 201, response.text
    return response.json()
