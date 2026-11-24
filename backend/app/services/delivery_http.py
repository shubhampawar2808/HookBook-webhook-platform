"""Execute a single outbound webhook HTTP attempt."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import Settings
from app.core.exceptions import ForbiddenError
from app.core.logging import get_logger
from app.models.delivery import WebhookDelivery
from app.models.endpoint import WebhookEndpoint
from app.models.event import Event
from app.services.delivery_retry import is_retryable_http_status, parse_retry_after
from app.services.delivery_sanitize import sanitize_text, summarize_response_body
from app.services.delivery_signing import sign_webhook_body
from app.services.delivery_ssrf import validate_webhook_destination

logger = get_logger(__name__)


@dataclass
class DeliveryHttpResult:
    outcome: str  # success | retryable_failure | permanent_failure
    http_status: int | None
    response_summary: str | None
    error_type: str | None
    error_message: str | None
    duration_ms: int
    retry_after_seconds: float | None = None
    request_body: bytes | None = None


def build_event_payload(event: Event, delivery: WebhookDelivery) -> dict[str, Any]:
    return {
        "id": event.event_id,
        "type": str(event.event_type_id),
        "created_at": event.created_at.astimezone(UTC).isoformat(),
        "data": event.payload,
        "delivery_id": str(delivery.id),
    }


async def execute_delivery_http(
    *,
    delivery: WebhookDelivery,
    event: Event,
    endpoint: WebhookEndpoint,
    settings: Settings,
    event_type_name: str | None = None,
) -> DeliveryHttpResult:
    started = time.perf_counter()
    try:
        validate_webhook_destination(endpoint.url, settings)
    except ForbiddenError as exc:
        return DeliveryHttpResult(
            outcome="permanent_failure",
            http_status=None,
            response_summary=None,
            error_type="ssrf_blocked",
            error_message=sanitize_text(exc.message),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    payload = build_event_payload(event, delivery)
    if event_type_name:
        payload["type"] = event_type_name
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    if len(body) > settings.DELIVERY_MAX_PAYLOAD_BYTES:
        return DeliveryHttpResult(
            outcome="permanent_failure",
            http_status=None,
            response_summary=None,
            error_type="payload_too_large",
            error_message="Outbound payload exceeds configured maximum size",
            duration_ms=int((time.perf_counter() - started) * 1000),
            request_body=body,
        )

    from app.core.secret_box import open_endpoint_secret

    timestamp = str(int(datetime.now(UTC).timestamp()))
    signing_secret = open_endpoint_secret(endpoint.signing_secret, settings)
    signature = sign_webhook_body(
        secret=signing_secret,
        timestamp=timestamp,
        body=body,
    )
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "HookForge-Delivery/1.0",
        "X-HookForge-Event-Id": event.event_id,
        "X-HookForge-Delivery-Id": str(delivery.id),
        "X-HookForge-Timestamp": timestamp,
        "X-HookForge-Signature": signature,
        "Idempotency-Key": delivery.idempotency_key,
    }

    timeout = httpx.Timeout(settings.DELIVERY_HTTP_TIMEOUT_SECONDS)
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
        ) as client:
            response = await client.post(endpoint.url, content=body, headers=headers)
        duration_ms = int((time.perf_counter() - started) * 1000)
        summary = summarize_response_body(response.content)
        if 200 <= response.status_code < 300:
            return DeliveryHttpResult(
                outcome="success",
                http_status=response.status_code,
                response_summary=summary,
                error_type=None,
                error_message=None,
                duration_ms=duration_ms,
                request_body=body,
            )

        retryable = is_retryable_http_status(response.status_code)
        retry_after = None
        if response.status_code == 429:
            retry_after = parse_retry_after(
                response.headers.get("Retry-After"),
                max_delay=settings.DELIVERY_RETRY_MAX_DELAY_SECONDS,
            )
        return DeliveryHttpResult(
            outcome="retryable_failure" if retryable else "permanent_failure",
            http_status=response.status_code,
            response_summary=summary,
            error_type="http_error",
            error_message=sanitize_text(f"HTTP {response.status_code}"),
            duration_ms=duration_ms,
            retry_after_seconds=retry_after,
            request_body=body,
        )
    except httpx.TimeoutException as exc:
        return DeliveryHttpResult(
            outcome="retryable_failure",
            http_status=None,
            response_summary=None,
            error_type="timeout",
            error_message=sanitize_text(type(exc).__name__),
            duration_ms=int((time.perf_counter() - started) * 1000),
            request_body=body,
        )
    except httpx.TransportError as exc:
        return DeliveryHttpResult(
            outcome="retryable_failure",
            http_status=None,
            response_summary=None,
            error_type="connection_error",
            error_message=sanitize_text(type(exc).__name__),
            duration_ms=int((time.perf_counter() - started) * 1000),
            request_body=body,
        )
    except Exception as exc:
        logger.exception("delivery_http_unexpected", delivery_id=str(delivery.id))
        return DeliveryHttpResult(
            outcome="retryable_failure",
            http_status=None,
            response_summary=None,
            error_type="unexpected_error",
            error_message=sanitize_text(type(exc).__name__),
            duration_ms=int((time.perf_counter() - started) * 1000),
            request_body=body,
        )
