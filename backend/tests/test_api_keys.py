"""API key lifecycle and authentication tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.api_key import APIKey
from tests.helpers import create_api_key, register_org


@pytest.mark.asyncio
async def test_api_key_created_once_and_listed(client: AsyncClient) -> None:
    data = await register_org(client, slug="key-org")
    created = await create_api_key(client, data["auth"])
    assert created["api_key"].startswith("hfk_")
    assert "key_hash" not in created

    listed = await client.get("/api/v1/api-keys", headers=data["auth"])
    assert listed.status_code == 200
    body = listed.json()
    assert body["total"] == 1
    assert "api_key" not in body["items"][0]
    assert body["items"][0]["key_prefix"] == created["key_prefix"]


@pytest.mark.asyncio
async def test_api_key_auth_and_invalid(client: AsyncClient) -> None:
    data = await register_org(client, slug="key-auth-org")
    # Need an event type to publish against
    et = await client.post(
        "/api/v1/event-types",
        headers=data["auth"],
        json={"name": "order.created"},
    )
    assert et.status_code == 201
    created = await create_api_key(client, data["auth"])
    raw = created["api_key"]

    ok = await client.post(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {raw}"},
        json={"event_type": "order.created", "payload": {"id": 1}},
    )
    assert ok.status_code == 202

    bad = await client.post(
        "/api/v1/events",
        headers={"Authorization": "Bearer hfk_deadbeef_invalid"},
        json={"event_type": "order.created", "payload": {}},
    )
    assert bad.status_code == 401


@pytest.mark.asyncio
async def test_revoked_and_expired_keys_rejected(client: AsyncClient, db_session) -> None:
    data = await register_org(client, slug="key-revoke-org")
    await client.post(
        "/api/v1/event-types",
        headers=data["auth"],
        json={"name": "ping.event"},
    )
    created = await create_api_key(client, data["auth"])
    raw = created["api_key"]
    key_id = created["id"]

    revoked = await client.delete(f"/api/v1/api-keys/{key_id}", headers=data["auth"])
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    after_revoke = await client.post(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {raw}"},
        json={"event_type": "ping.event", "payload": {}},
    )
    assert after_revoke.status_code == 401

    # Fresh key then expire it in DB
    created2 = await create_api_key(client, data["auth"])
    raw2 = created2["api_key"]
    result = await db_session.execute(select(APIKey).where(APIKey.id == created2["id"]))
    api_key = result.scalar_one()
    api_key.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    await db_session.commit()

    expired = await client.post(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {raw2}"},
        json={"event_type": "ping.event", "payload": {}},
    )
    assert expired.status_code == 401


@pytest.mark.asyncio
async def test_api_key_rotation(client: AsyncClient) -> None:
    data = await register_org(client, slug="key-rotate-org")
    await client.post(
        "/api/v1/event-types",
        headers=data["auth"],
        json={"name": "rotate.event"},
    )
    created = await create_api_key(client, data["auth"])
    old_raw = created["api_key"]
    rotated = await client.post(
        f"/api/v1/api-keys/{created['id']}/rotate",
        headers=data["auth"],
    )
    assert rotated.status_code == 201
    new_raw = rotated.json()["api_key"]
    assert new_raw != old_raw

    old_auth = await client.post(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {old_raw}"},
        json={"event_type": "rotate.event", "payload": {}},
    )
    assert old_auth.status_code == 401

    new_auth = await client.post(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {new_raw}"},
        json={"event_type": "rotate.event", "payload": {}},
    )
    assert new_auth.status_code == 202
