# HookForge Production Hardening (Prompt 5)

This document summarizes remediations applied after the Phase 0 audit
([production-readiness-audit.md](./production-readiness-audit.md)).

## What changed

### Security
- Production fail-closed settings (`DEBUG`, `REDIS_REQUIRED`, SSRF localhost flags, registration, CORS, `SECRET_KEY` entropy).
- Dedicated `API_KEY_PEPPER` (falls back to `SECRET_KEY` for migration).
- Endpoint signing secrets encrypted at rest (Fernet) with plaintext dual-read for legacy rows.
- Redis-backed rate limits on auth, publish, and replay paths.
- Streaming request body size enforcement (not Content-Length alone).
- Security headers (CSP frame-ancestors none, nosniff, Referrer-Policy, Permissions-Policy, HSTS in production).
- TrustedHost middleware in production.
- Login timing hardening (dummy Argon2 verify).
- Publish API keys kept in memory only (no `sessionStorage`).

### Delivery reliability
- Event publish and replay **commit delivery rows, then enqueue** on the request path (not fire-and-forget after the HTTP response).
- `enqueued_at` remains set only when a worker claims the row so Beat can recover broker failures (`PENDING` + `enqueued_at IS NULL`).
- Production requires Redis + Celery Beat; Compose includes Beat and Alembic migrate on API start.

### Observability & ops
- Org-scoped Prometheus text metrics at `/metrics` (authenticated).
- CI runs Postgres 16 + Redis with `hookforge_app` / `hookforge_test`.
- `docker-compose.prod.yml` overlay (no reload, production env gates).
- `.dockerignore` excludes secrets and local tooling.

## Residual risks (accepted for this phase)

| Item | Notes |
|------|--------|
| JWT in `localStorage` | XSS can steal tokens. Prefer httpOnly cookies in a future auth contract change. |
| No JWT denylist | Logout clears the browser token only; shorten TTL or add Redis denylist later. |
| Commit-then-enqueue window | If Redis dies after DB commit, deliveries stay PENDING until Beat (≤ recovery interval). Not lost. |
| Portable Redis 3.0 (Windows) | Local-only. Production must use Redis 6+/7. |
| OpenAPI disabled in production | Intentional; use separate internal docs if needed. |

## Production checklist (do not deploy without approval)

1. Generate strong `SECRET_KEY` (≥32 chars, not a placeholder) and optional `API_KEY_PEPPER` / `ENDPOINT_SECRET_ENCRYPTION_KEY`.
2. Set `APP_ENV=production`, `DEBUG=false`, `REDIS_REQUIRED=true`, `ALLOW_PUBLIC_REGISTRATION=false`.
3. Set `DELIVERY_ALLOW_HTTP_LOCALHOST=false` and `DELIVERY_SSRF_ALLOW_DEV_HTTP=false`.
4. Set explicit HTTPS `CORS_ORIGINS` and `TRUSTED_HOSTS`.
5. Run `alembic upgrade head` (includes `0004_endpoint_secret_width`).
6. Run Redis 7+, Celery worker, and Celery Beat.
7. Terminate TLS at a reverse proxy; confirm HSTS and health/ready probes.
8. Backup PostgreSQL on a schedule; test restore.
9. Rotate any credentials that ever appeared in shared logs or screenshots.

## Compose sketches

```powershell
# Development (reload, Beat, migrate on API start)
docker compose up --build

# Production-oriented overlay (review secrets first; no external deploy without approval)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Local Windows note

`scripts/dev-up.ps1` + portable Redis 3.0 + `run_celery_worker_dev.py` remain the supported **development** path. They are not a production posture.
