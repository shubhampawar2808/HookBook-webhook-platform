"""Integration tests for webhook delivery engine (hookforge_test only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.models.delivery import WebhookDelivery, WebhookDeliveryAttempt
from app.models.enums import DeliveryStatus
from app.services.delivery_http import DeliveryHttpResult
from app.services.delivery_processor import DeliveryProcessor
from tests.helpers import create_api_key, register_org


async def _setup_subscribed_endpoint(client: AsyncClient, auth: dict[str, str]):
    et = await client.post(
        "/api/v1/event-types",
        headers=auth,
        json={"name": "order.created"},
    )
    assert et.status_code == 201, et.text
    ep = await client.post(
        "/api/v1/endpoints",
        headers=auth,
        json={"name": "Local", "url": "http://127.0.0.1:9999/hooks"},
    )
    assert ep.status_code == 201, ep.text
    assert "signing_secret" in ep.json()
    sub = await client.post(
        f"/api/v1/endpoints/{ep.json()['id']}/subscriptions",
        headers=auth,
        json={"event_type_id": et.json()["id"]},
    )
    assert sub.status_code == 201, sub.text
    return et.json(), ep.json(), sub.json()


@pytest.mark.asyncio
async def test_event_creates_delivery_for_matching_subscription(
    client: AsyncClient, db_session
) -> None:
    org = await register_org(client, slug="del-create")
    await _setup_subscribed_endpoint(client, org["auth"])
    key = await create_api_key(client, org["auth"])

    with patch("app.api.v1.events.enqueue_delivery_jobs", return_value={"queued": 0, "failed": 0}):
        pub = await client.post(
            "/api/v1/events",
            headers={"Authorization": f"Bearer {key['api_key']}"},
            json={"event_type": "order.created", "payload": {"n": 1}},
        )
    assert pub.status_code == 202, pub.text
    assert pub.json()["delivery"] == "accepted"
    assert pub.json()["delivery_count"] == 1

    rows = (await db_session.execute(select(WebhookDelivery))).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == DeliveryStatus.PENDING.value
    assert rows[0].idempotency_key.startswith("del_")


@pytest.mark.asyncio
async def test_inactive_endpoint_skipped(client: AsyncClient, db_session) -> None:
    org = await register_org(client, slug="del-inactive-ep")
    et, ep, _ = await _setup_subscribed_endpoint(client, org["auth"])
    disabled = await client.patch(
        f"/api/v1/endpoints/{ep['id']}",
        headers=org["auth"],
        json={"status": "disabled"},
    )
    assert disabled.status_code == 200
    key = await create_api_key(client, org["auth"])
    with patch("app.api.v1.events.enqueue_delivery_jobs", return_value={"queued": 0, "failed": 0}):
        pub = await client.post(
            "/api/v1/events",
            headers={"Authorization": f"Bearer {key['api_key']}"},
            json={"event_type": "order.created", "payload": {}},
        )
    assert pub.status_code == 202
    assert pub.json()["delivery_count"] == 0
    assert (await db_session.execute(select(WebhookDelivery))).scalars().first() is None


@pytest.mark.asyncio
async def test_successful_http_delivery(client: AsyncClient, db_session) -> None:
    org = await register_org(client, slug="del-ok")
    await _setup_subscribed_endpoint(client, org["auth"])
    key = await create_api_key(client, org["auth"])
    with patch("app.api.v1.events.enqueue_delivery_jobs", return_value={"queued": 0, "failed": 0}):
        await client.post(
            "/api/v1/events",
            headers={"Authorization": f"Bearer {key['api_key']}"},
            json={"event_type": "order.created", "payload": {"ok": True}},
        )
    delivery = (await db_session.execute(select(WebhookDelivery))).scalar_one()

    result = DeliveryHttpResult(
        outcome="success",
        http_status=200,
        response_summary="ok",
        error_type=None,
        error_message=None,
        duration_ms=12,
    )
    with patch(
        "app.services.delivery_processor.execute_delivery_http",
        new=AsyncMock(return_value=result),
    ):
        status = await DeliveryProcessor(db_session).process(delivery.id)
    assert status == DeliveryStatus.SUCCEEDED.value
    await db_session.refresh(delivery)
    assert delivery.status == DeliveryStatus.SUCCEEDED.value
    assert delivery.delivered_at is not None
    attempts = (await db_session.execute(select(WebhookDeliveryAttempt))).scalars().all()
    assert len(attempts) == 1
    assert attempts[0].outcome == "success"


@pytest.mark.asyncio
async def test_retryable_then_dead_letter(client: AsyncClient, db_session) -> None:
    org = await register_org(client, slug="del-dlq")
    await _setup_subscribed_endpoint(client, org["auth"])
    key = await create_api_key(client, org["auth"])
    with patch("app.api.v1.events.enqueue_delivery_jobs", return_value={"queued": 0, "failed": 0}):
        await client.post(
            "/api/v1/events",
            headers={"Authorization": f"Bearer {key['api_key']}"},
            json={"event_type": "order.created", "payload": {}},
        )
    delivery = (await db_session.execute(select(WebhookDelivery))).scalar_one()
    delivery.max_attempts = 2
    await db_session.flush()

    fail = DeliveryHttpResult(
        outcome="retryable_failure",
        http_status=500,
        response_summary="err",
        error_type="http_error",
        error_message="HTTP 500",
        duration_ms=5,
    )
    with patch(
        "app.services.delivery_processor.execute_delivery_http",
        new=AsyncMock(return_value=fail),
    ):
        first = await DeliveryProcessor(db_session).process(delivery.id)
        assert first == DeliveryStatus.RETRYING.value
        delivery.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
        await db_session.flush()
        second = await DeliveryProcessor(db_session).process(delivery.id)
    assert second == DeliveryStatus.DEAD_LETTER.value

    listed = await client.get("/api/v1/deliveries/dead-letter", headers=org["auth"])
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


@pytest.mark.asyncio
async def test_permanent_failure(client: AsyncClient, db_session) -> None:
    org = await register_org(client, slug="del-perm")
    await _setup_subscribed_endpoint(client, org["auth"])
    key = await create_api_key(client, org["auth"])
    with patch("app.api.v1.events.enqueue_delivery_jobs", return_value={"queued": 0, "failed": 0}):
        await client.post(
            "/api/v1/events",
            headers={"Authorization": f"Bearer {key['api_key']}"},
            json={"event_type": "order.created", "payload": {}},
        )
    delivery = (await db_session.execute(select(WebhookDelivery))).scalar_one()
    fail = DeliveryHttpResult(
        outcome="permanent_failure",
        http_status=404,
        response_summary="missing",
        error_type="http_error",
        error_message="HTTP 404",
        duration_ms=3,
    )
    with patch(
        "app.services.delivery_processor.execute_delivery_http",
        new=AsyncMock(return_value=fail),
    ):
        status = await DeliveryProcessor(db_session).process(delivery.id)
    assert status == DeliveryStatus.FAILED.value


@pytest.mark.asyncio
async def test_replay_dead_letter(client: AsyncClient, db_session) -> None:
    org = await register_org(client, slug="del-replay")
    await _setup_subscribed_endpoint(client, org["auth"])
    key = await create_api_key(client, org["auth"])
    with patch("app.api.v1.events.enqueue_delivery_jobs", return_value={"queued": 0, "failed": 0}):
        await client.post(
            "/api/v1/events",
            headers={"Authorization": f"Bearer {key['api_key']}"},
            json={"event_type": "order.created", "payload": {}},
        )
    delivery = (await db_session.execute(select(WebhookDelivery))).scalar_one()
    delivery.status = DeliveryStatus.DEAD_LETTER.value
    delivery.attempt_count = 6
    await db_session.flush()

    with patch(
        "app.services.delivery_management.enqueue_delivery_jobs",
        return_value={"queued": 1, "failed": 0},
    ):
        replay = await client.post(
            f"/api/v1/deliveries/{delivery.id}/replay",
            headers=org["auth"],
        )
    assert replay.status_code == 202, replay.text
    await db_session.refresh(delivery)
    assert delivery.status == DeliveryStatus.PENDING.value
    assert delivery.replay_count == 1


@pytest.mark.asyncio
async def test_duplicate_dispatch_idempotent(client: AsyncClient, db_session) -> None:
    org = await register_org(client, slug="del-dup")
    await _setup_subscribed_endpoint(client, org["auth"])
    key = await create_api_key(client, org["auth"])
    with patch("app.api.v1.events.enqueue_delivery_jobs", return_value={"queued": 0, "failed": 0}):
        first = await client.post(
            "/api/v1/events",
            headers={"Authorization": f"Bearer {key['api_key']}"},
            json={"event_type": "order.created", "payload": {"a": 1}},
        )
    event_pk = uuid.UUID(first.json()["id"])
    from app.models.event import Event
    from app.services.delivery_dispatch import DeliveryDispatchService

    event = await db_session.get(Event, event_pk)
    ids = await DeliveryDispatchService(db_session).create_deliveries_for_event(event)
    rows = (await db_session.execute(select(WebhookDelivery))).scalars().all()
    assert len(rows) == 1
    assert ids[0] == rows[0].id


@pytest.mark.asyncio
async def test_delivery_tenant_isolation(client: AsyncClient) -> None:
    org_a = await register_org(client, slug="del-iso-a", email="a@example.com")
    org_b = await register_org(client, slug="del-iso-b", email="b@example.com")
    await _setup_subscribed_endpoint(client, org_a["auth"])
    key = await create_api_key(client, org_a["auth"])
    with patch("app.api.v1.events.enqueue_delivery_jobs", return_value={"queued": 0, "failed": 0}):
        await client.post(
            "/api/v1/events",
            headers={"Authorization": f"Bearer {key['api_key']}"},
            json={"event_type": "order.created", "payload": {}},
        )
    listed_a = await client.get("/api/v1/deliveries", headers=org_a["auth"])
    listed_b = await client.get("/api/v1/deliveries", headers=org_b["auth"])
    assert listed_a.json()["total"] == 1
    assert listed_b.json()["total"] == 0
    delivery_id = listed_a.json()["items"][0]["id"]
    detail_b = await client.get(f"/api/v1/deliveries/{delivery_id}", headers=org_b["auth"])
    assert detail_b.status_code == 404
    replay_b = await client.post(f"/api/v1/deliveries/{delivery_id}/replay", headers=org_b["auth"])
    assert replay_b.status_code == 404


@pytest.mark.asyncio
async def test_stale_processing_recovery_query(client: AsyncClient, db_session) -> None:
    org = await register_org(client, slug="del-stale")
    await _setup_subscribed_endpoint(client, org["auth"])
    key = await create_api_key(client, org["auth"])
    with patch("app.api.v1.events.enqueue_delivery_jobs", return_value={"queued": 0, "failed": 0}):
        await client.post(
            "/api/v1/events",
            headers={"Authorization": f"Bearer {key['api_key']}"},
            json={"event_type": "order.created", "payload": {}},
        )
    delivery = (await db_session.execute(select(WebhookDelivery))).scalar_one()
    delivery.status = DeliveryStatus.PROCESSING.value
    delivery.processing_started_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.flush()

    from app.services.delivery_recovery import DeliveryRecoveryService

    with patch(
        "app.services.delivery_recovery.enqueue_delivery_jobs",
        return_value={"queued": 1, "failed": 0},
    ) as mocked:
        result = await DeliveryRecoveryService(db_session).recover_and_enqueue()
    assert result["found"] >= 1
    mocked.assert_called()
