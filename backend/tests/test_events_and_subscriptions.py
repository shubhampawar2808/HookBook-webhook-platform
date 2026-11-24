"""Event publishing, subscriptions, pagination, and validation."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.helpers import create_api_key, register_org


@pytest.mark.asyncio
async def test_event_publish_and_invalid_type(client: AsyncClient) -> None:
    org = await register_org(client, slug="evt-org")
    et = await client.post(
        "/api/v1/event-types",
        headers=org["auth"],
        json={"name": "user.created", "description": "user signup"},
    )
    assert et.status_code == 201
    key = await create_api_key(client, org["auth"])

    accepted = await client.post(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {key['api_key']}"},
        json={"event_type": "user.created", "payload": {"user_id": "u1"}},
    )
    assert accepted.status_code == 202
    body = accepted.json()
    assert body["status"] == "accepted"
    assert body["event_id"].startswith("evt_")
    assert body["delivery"] in {"accepted", "none"}
    assert body["payload"]["user_id"] == "u1"

    missing = await client.post(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {key['api_key']}"},
        json={"event_type": "does.not.exist", "payload": {}},
    )
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_invalid_payload_rejected(client: AsyncClient) -> None:
    org = await register_org(client, slug="evt-val-org")
    key = await create_api_key(client, org["auth"])
    response = await client.post(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {key['api_key']}"},
        json={"event_type": "x", "payload": ["not", "an", "object"]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_subscription_create_duplicate_and_list(client: AsyncClient) -> None:
    org = await register_org(client, slug="sub-org")
    et = await client.post(
        "/api/v1/event-types",
        headers=org["auth"],
        json={"name": "payment.succeeded"},
    )
    ep = await client.post(
        "/api/v1/endpoints",
        headers=org["auth"],
        json={"name": "Billing", "url": "https://example.com/hooks/billing"},
    )
    event_type_id = et.json()["id"]
    endpoint_id = ep.json()["id"]

    first = await client.post(
        f"/api/v1/endpoints/{endpoint_id}/subscriptions",
        headers=org["auth"],
        json={"event_type_id": event_type_id},
    )
    assert first.status_code == 201

    dup = await client.post(
        f"/api/v1/endpoints/{endpoint_id}/subscriptions",
        headers=org["auth"],
        json={"event_type_id": event_type_id},
    )
    assert dup.status_code == 409

    listed = await client.get(
        f"/api/v1/endpoints/{endpoint_id}/subscriptions",
        headers=org["auth"],
    )
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    deleted = await client.delete(
        f"/api/v1/endpoints/{endpoint_id}/subscriptions/{first.json()['id']}",
        headers=org["auth"],
    )
    assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_pagination(client: AsyncClient) -> None:
    org = await register_org(client, slug="page-org")
    for i in range(5):
        resp = await client.post(
            "/api/v1/endpoints",
            headers=org["auth"],
            json={"name": f"EP {i}", "url": f"http://localhost:900{i}/h"},
        )
        assert resp.status_code == 201

    page1 = await client.get("/api/v1/endpoints?page=1&page_size=2", headers=org["auth"])
    assert page1.status_code == 200
    body = page1.json()
    assert body["page"] == 1
    assert body["page_size"] == 2
    assert body["total"] == 5
    assert body["total_pages"] == 3
    assert len(body["items"]) == 2


@pytest.mark.asyncio
async def test_organization_me_and_validation_errors(client: AsyncClient) -> None:
    org = await register_org(client, slug="org-me")
    me = await client.get("/api/v1/organizations/me", headers=org["auth"])
    assert me.status_code == 200
    assert me.json()["slug"] == "org-me"

    bad = await client.post(
        "/api/v1/endpoints",
        headers=org["auth"],
        json={"name": "Bad", "url": "ftp://example.com/hook"},
    )
    assert bad.status_code == 422
