"""Organization registration and authentication tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import update

from app.models.enums import OrganizationStatus
from app.models.organization import Organization
from tests.helpers import register_org


@pytest.mark.asyncio
async def test_register_and_me(client: AsyncClient) -> None:
    data = await register_org(client, slug="acme-corp", email="owner@example.com")
    me = data["me"]
    assert me["email"] == "owner@example.com"
    assert me["role"] == "owner"
    assert me["organization_name"]
    assert "password" not in me
    assert "password_hash" not in me


@pytest.mark.asyncio
async def test_duplicate_slug_rejected(client: AsyncClient) -> None:
    await register_org(client, slug="dup-org", email="a@example.com")
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Dup Org 2",
            "organization_slug": "dup-org",
            "email": "b@example.com",
            "password": "secure-password-1",
            "full_name": "Other",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_success_and_invalid_password(client: AsyncClient) -> None:
    await register_org(
        client, slug="login-org", email="user@example.com", password="secure-password-1"
    )
    ok = await client.post(
        "/api/v1/auth/login",
        json={
            "organization_slug": "login-org",
            "email": "user@example.com",
            "password": "secure-password-1",
        },
    )
    assert ok.status_code == 200
    assert "access_token" in ok.json()

    bad = await client.post(
        "/api/v1/auth/login",
        json={
            "organization_slug": "login-org",
            "email": "user@example.com",
            "password": "wrong-password",
        },
    )
    assert bad.status_code == 401
    assert bad.json()["error"]["message"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_unknown_email_same_message(client: AsyncClient) -> None:
    await register_org(client, slug="hide-org", email="real@example.com")
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "organization_slug": "hide-org",
            "email": "missing@example.com",
            "password": "secure-password-1",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_suspended_organization_rejected(client: AsyncClient, db_session) -> None:
    data = await register_org(client, slug="susp-org", email="owner@example.com")
    org_id = data["me"]["organization_id"]
    await db_session.execute(
        update(Organization)
        .where(Organization.id == org_id)
        .values(status=OrganizationStatus.SUSPENDED.value)
    )
    await db_session.commit()

    me = await client.get("/api/v1/auth/me", headers=data["auth"])
    assert me.status_code == 401

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "organization_slug": "susp-org",
            "email": "owner@example.com",
            "password": "secure-password-1",
        },
    )
    assert login.status_code == 401
