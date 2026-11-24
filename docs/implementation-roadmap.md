# HookForge Implementation Roadmap

HookForge is delivered across five prompts/phases. This file is the source of truth for scope boundaries.

## Phase 1 — Architecture & Project Foundation (current)

**Goal:** Production-quality skeleton that boots, connects, and is ready to extend.

Includes:
- Repository structure (backend, frontend, infrastructure, docs, scripts)
- FastAPI app with health/ready, CORS, logging, correlation IDs, safe errors
- Pydantic Settings
- Async SQLAlchemy + Alembic foundation (no domain tables)
- Redis connection manager
- Celery configuration + health-check task
- React + TypeScript + Vite frontend with router, Redux, Axios, status page
- Docker Compose (Postgres, Redis, backend, Celery, frontend)
- GitHub Actions CI foundation
- Documentation and initial tests

Does **not** include:
- Domain CRUD APIs
- Webhook delivery engine
- Full operator dashboard
- Auth/SSO productization beyond config placeholders

## Phase 2 — Core Backend Domain (current implementation)

**Goal:** Persist and manage the core entities with tenant isolation.

Implemented:
- Alembic `0002_domain_tables` for Organization, User, APIKey, WebhookEndpoint, EventType, Event, EndpointSubscription
- Repository + service layers
- JWT auth (register/login/me) and API-key auth for event publish
- RBAC (OWNER / ADMIN / MEMBER)
- Tenant isolation with composite FKs and org-scoped queries
- Event ingest (persist only — no delivery)
- Automated tests for auth, keys, isolation, events, pagination

Deferred to later phases:
- Delivery / DeliveryAttempt / AuditLog tables
- Event idempotency keys (column planned; full semantics with delivery)

## Phase 3 — Delivery Engine (implemented)

**Goal:** Reliably deliver events to subscribed endpoints.

Implemented:
- `WebhookDelivery` / `WebhookDeliveryAttempt` + Alembic `0003_webhook_deliveries`
- Celery tasks `process_webhook_delivery` and `recover_deliveries` (+ Beat schedule)
- HMAC-SHA256 signing, SSRF validation, exponential backoff retries
- Dead-letter + replay APIs
- Delivery management endpoints under `/api/v1/deliveries`

## Phase 4 — Frontend Dashboard (implemented)

**Goal:** Operator UI for day-to-day management.

Implemented:
- Design system **Industrial Precision – The Webhook Observatory**
- Auth (login/register), JWT session, protected routes
- Application shell with collapsible sidebar + command palette
- Overview observatory metrics (derived from delivery APIs)
- Events ledger (delivery-derived; API-key publish)
- Endpoints, event types, subscriptions
- Deliveries detail + attempt timeline, dead-letter replay
- API key create/rotate/revoke with one-time secret reveal
- Settings (org profile + verified health probes)

## Phase 5 — Production Hardening (implemented)

**Goal:** Operate HookForge safely at scale without expanding product features.

Implemented:
- Phase 0 production-readiness audit (`docs/production-readiness-audit.md`)
- Fail-closed production config, rate limits, body-size streaming, security headers
- API key pepper + endpoint signing-secret encryption at rest
- Commit-then-enqueue delivery path; Compose Beat + migrate; prod Compose overlay
- CI with Postgres/Redis; org-scoped `/metrics`; release checklist
- Docs: `docs/production-hardening.md`, `docs/release-checklist.md`

Residual (documented, not blocking Prompt 5): JWT in `localStorage`, no token denylist, optional transactional outbox.

## Dependency Between Phases

```
Phase 1 foundation
    └── Phase 2 domain APIs + schema
            └── Phase 3 delivery workers
                    └── Phase 4 dashboard UX
                            └── Phase 5 hardening
```

Do not start a later phase until the previous phase is validated.
