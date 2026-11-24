"""Cross-organization isolation regression tests."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from tests.helpers import create_api_key, register_org


@pytest.mark.asyncio
async def test_endpoints_isolated_between_orgs(client: AsyncClient) -> None:
    org_a = await register_org(client, slug="iso-a", email="a@example.com")
    org_b = await register_org(client, slug="iso-b", email="b@example.com")

    created = await client.post(
        "/api/v1/endpoints",
        headers=org_a["auth"],
        json={
            "name": "A Endpoint",
            "url": "http://localhost:9999/hooks",
            "description": "org a only",
        },
    )
    assert created.status_code == 201
    endpoint_id = created.json()["id"]

    # B cannot read
    read = await client.get(f"/api/v1/endpoints/{endpoint_id}", headers=org_b["auth"])
    assert read.status_code == 404

    # B cannot modify
    patch = await client.patch(
        f"/api/v1/endpoints/{endpoint_id}",
        headers=org_b["auth"],
        json={"name": "hijacked"},
    )
    assert patch.status_code == 404

    # B cannot delete
    delete = await client.delete(f"/api/v1/endpoints/{endpoint_id}", headers=org_b["auth"])
    assert delete.status_code == 404

    # A still sees it
    still = await client.get(f"/api/v1/endpoints/{endpoint_id}", headers=org_a["auth"])
    assert still.status_code == 200
    assert still.json()["name"] == "A Endpoint"


@pytest.mark.asyncio
async def test_cannot_subscribe_or_publish_cross_org(client: AsyncClient) -> None:
    org_a = await register_org(client, slug="iso2-a", email="a2@example.com")
    org_b = await register_org(client, slug="iso2-b", email="b2@example.com")

    et_a = await client.post(
        "/api/v1/event-types",
        headers=org_a["auth"],
        json={"name": "invoice.paid"},
    )
    assert et_a.status_code == 201
    event_type_a = et_a.json()["id"]

    ep_b = await client.post(
        "/api/v1/endpoints",
        headers=org_b["auth"],
        json={"name": "B Hook", "url": "https://example.com/hook"},
    )
    assert ep_b.status_code == 201
    endpoint_b = ep_b.json()["id"]

    # B cannot subscribe to A's event type
    sub = await client.post(
        f"/api/v1/endpoints/{endpoint_b}/subscriptions",
        headers=org_b["auth"],
        json={"event_type_id": event_type_a},
    )
    assert sub.status_code == 404

    # B cannot publish using A's event type name with B's API key
    await client.post(
        "/api/v1/event-types",
        headers=org_b["auth"],
        json={"name": "other.event"},
    )
    key_b = await create_api_key(client, org_b["auth"])
    publish = await client.post(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {key_b['api_key']}"},
        json={"event_type": "invoice.paid", "payload": {"x": 1}},
    )
    assert publish.status_code == 404

    # A cannot read B's event type by id
    get_et = await client.get(f"/api/v1/event-types/{event_type_a}", headers=org_b["auth"])
    assert get_et.status_code == 404


@pytest.mark.asyncio
async def test_client_supplied_org_id_ignored(client: AsyncClient) -> None:
    org_a = await register_org(client, slug="iso3-a", email="a3@example.com")
    # Extra fields should be ignored by Pydantic; org comes from JWT
    response = await client.post(
        "/api/v1/endpoints",
        headers=org_a["auth"],
        json={
            "name": "Safe",
            "url": "http://127.0.0.1:8080/hook",
            "organization_id": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 201
    assert response.json()["organization_id"] == org_a["me"]["organization_id"]
