# HookForge Architecture

## Overview

HookForge is a webhook delivery and event management platform. Organizations register webhook endpoints, publish events, subscribe to event types, and (in Prompt 3) receive reliable HTTP deliveries.

This document covers Phase 1–2: foundation plus backend domain, authentication, and tenant isolation.

**Prompt 3 implements asynchronous webhook delivery** via Celery workers, with HMAC signing, retries, dead-letter, and replay. See [webhook-delivery.md](webhook-delivery.md).

## System Components

| Component | Responsibility |
|-----------|----------------|
| **Frontend (React + Vite)** | Status UI; dashboard arrives in Phase 4 |
| **Backend API (FastAPI)** | Versioned HTTP API (`/api/v1`), auth, domain CRUD, event ingest |
| **PostgreSQL** | System of record (shared schema, organization-scoped rows) |
| **Redis** | Optional in Phase 2; Celery broker/backend later — never source of truth |
| **Celery Worker** | Health task only until Prompt 3 delivery workers |
| **Alembic** | Schema migrations (`0001_foundation` → `0002_domain_tables`) |

## Authentication Flows

### JWT (operators)

1. `POST /api/v1/auth/register` creates organization + OWNER user in one transaction.
2. `POST /api/v1/auth/login` verifies Argon2id password hash; issues signed JWT (`sub`, `org`, `role`, `jti`, `exp`).
3. Protected routes use `Authorization: Bearer <jwt>`.
4. Organization context is taken **only** from token claims + DB — never from request body.

### API keys (machines)

1. OWNER/ADMIN creates a key via `POST /api/v1/api-keys`.
2. Raw key `hfk_<prefix>_<secret>` is returned **once**.
3. Only peppered HMAC-SHA256 hash is stored.
4. Event publish uses `Authorization: Bearer hfk_...`.
5. Revoked/expired keys are rejected. Rotation revokes the old key and issues a new one.

## Tenant Isolation Strategy

**Shared PostgreSQL schema with `organization_id` on every tenant-owned row.**

Why this strategy:
- Fits a single-product SaaS control plane without per-tenant database sprawl.
- Enables efficient cross-tenant ops/metrics later with explicit admin tooling.
- Composite foreign keys (e.g. `(event_type_id, organization_id)`) enforce same-org relationships at the database layer.

Trade-offs:
- Application bugs that omit `organization_id` filters are high impact — mitigated by repository helpers that always require org scope, JWT/API-key derived org, and composite FKs.
- No PostgreSQL RLS yet (can be added in Phase 5 hardening).
- Noisy-neighbor risk is shared-infra; mitigated later with quotas/rate limits.

Isolation rules:
- Every query for tenant data is scoped by authenticated `organization_id`.
- Client-supplied `organization_id` is ignored.
- Cross-org reads/updates/deletes return `404` (no existence leak across tenants).

## Domain Relationships

```
Organization
├── User
├── APIKey (created_by must share organization)
├── WebhookEndpoint
├── EventType
├── EndpointSubscription ──▶ Endpoint + EventType (same org)
└── Event ──▶ EventType (same org)
```

## Request Flow (authenticated)

1. Correlation ID middleware.
2. JWT or API-key dependency resolves principal + organization.
3. Suspended organizations are rejected.
4. Service layer enforces RBAC (OWNER / ADMIN / MEMBER).
5. Repository queries always include `organization_id`.
6. Session commits on success; rolls back on errors.

## Redis Responsibilities

Phase 2: optional. Startup continues if Redis is down when `REDIS_REQUIRED=false`.

Phase 3+: delivery coordination, retries, rate limits.

## Celery

Phase 2: no delivery tasks. Existing `hookforge.health_check` remains.

## Security Notes

- Argon2id passwords; JWT HS256 with expiry; API-key hashing with server pepper.
- Safe error envelopes; no password/API-key hashes in responses or logs.
- Request body size limit middleware.
- OpenAPI disabled when `APP_ENV=production`.
- SSRF hardening for outbound delivery is deferred to Prompt 3 (registration validates URL shape only and never makes outbound requests).

## Known Limitations (Phase 2)

- No webhook delivery, retries, DLQ, or replay.
- No refresh tokens / SSO.
- No PostgreSQL row-level security.
- Redis/Celery not required for API correctness in this phase.
