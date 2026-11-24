# HookForge Webhook Delivery (Prompt 3)

## Overview

When an event is published, HookForge creates one `WebhookDelivery` per matching **active** subscription on an **active** endpoint, then enqueues Celery jobs. Workers perform signed HTTP POSTs, record attempts, retry transient failures, and dead-letter exhausted deliveries.

**Delivery is at-least-once.** Receivers must treat `Idempotency-Key` / delivery id as idempotent. Exactly-once HTTP delivery is not claimed.

## Headers

| Header | Purpose |
|--------|---------|
| `Content-Type` | `application/json` |
| `X-HookForge-Event-Id` | Public event id (`evt_...`) |
| `X-HookForge-Delivery-Id` | Delivery UUID |
| `X-HookForge-Timestamp` | Unix timestamp (seconds) |
| `X-HookForge-Signature` | `sha256=<hex>` HMAC |
| `Idempotency-Key` | Stable per event+endpoint |

## Signature verification (receiver)

Signing input: `"{timestamp}.{raw_body}"` with UTF-8 bytes.

```python
import hashlib, hmac

def verify(secret: str, timestamp: str, body: bytes, signature_header: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header.strip())
```

Use the endpoint `signing_secret` shown once at endpoint creation.

## Retry policy

- Max attempts: 6 (configurable)
- Base delay: 5s, multiplier: 2, max delay: 1h, with jitter
- Retry: timeouts, connection errors, 408/425/429/5xx
- No auto-retry: 400/401/403/404/422 (and similar permanent 4xx)
- Respect `Retry-After` on 429 (capped)
- Exhaustion → `dead_letter`

PostgreSQL delivery status is the source of truth (not Celery retry counters).

## Dead letter & replay

- `GET /api/v1/deliveries/dead-letter`
- `POST /api/v1/deliveries/{id}/replay` (OWNER/ADMIN) resets to `pending` and re-enqueues; attempt history is preserved.

## SSRF protections

- HTTPS required in production
- HTTP allowed only for localhost in development/test when `DELIVERY_SSRF_ALLOW_DEV_HTTP=true`
- Blocks private/loopback/link-local/metadata addresses after DNS resolution
- Redirects disabled
- Remaining limitation: extremely advanced DNS-rebinding races during the connect window are mitigated by resolving before connect and disabling redirects; keep production on HTTPS only.

## Dispatch reliability

1. Event + delivery rows are committed.
2. Celery jobs are enqueued on the same request path (after commit).
3. If the broker is unavailable after commit, rows remain `PENDING` with `enqueued_at` null.
4. Celery Beat runs `recover_deliveries` and re-enqueues recoverable work.

Production must set `REDIS_REQUIRED=true` and run Beat. Prefer Redis 6+/7 (Compose uses `redis:7-alpine`). Portable Redis 3.0 is **local Windows only**.

## Local worker commands (PowerShell)

Preferred: `.\scripts\dev-up.ps1` (starts Redis, API, worker, Beat, receiver).

Manual:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000

# Windows + portable Redis 3.0: use remote-control-disabled worker
python ..\scripts\run_celery_worker_dev.py
# or: ..\scripts\dev-celery.ps1

# Beat (recovery)
celery -A app.workers.celery_app.celery_app beat --loglevel=INFO
```

On Redis 6+/7 you may use a normal Celery worker (`--pool=solo` on Windows).
