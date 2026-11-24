# HookForge Production-Readiness Audit (Prompt 5 — Phase 0)

**Date:** 2026-11-24
**Scope:** Full repository baseline before hardening changes.
**Rule:** Findings below are from inspected code/config only (not invented).

## Summary

HookForge’s domain APIs, tenant isolation, Argon2id passwords, hashed API keys, delivery locking (`FOR UPDATE SKIP LOCKED`), idempotent delivery inserts, SSRF guards, and Beat-driven recovery are solid foundations. Gaps cluster around **production fail-closed config**, **abuse controls** (rate limits / body size), **browser secret storage**, **Compose/CI production parity**, and **observability**.

Local portable Redis 3.0 + remote-control-disabled workers are **explicitly local-only**, not a production posture.

---

## CRITICAL

### C1. CI backend pytest cannot succeed as configured
| | |
|--|--|
| **Module** | `.github/workflows/ci.yml`, `backend/tests/conftest.py` |
| **Root cause** | Pytest env points at Postgres/`hookforge_app` on localhost; workflow defines no Postgres/Redis services and uses role `hookforge` ≠ `hookforge_app`. |
| **Impact** | CI does not validate the backend suite. |
| **Remediation** | Add Postgres 16 + Redis services; create `hookforge_app` / `hookforge_test`; align env. |
| **Code change** | Yes |

### C2. Compose stack is development-only (reload, DEBUG, no Beat/migrations)
| | |
|--|--|
| **Module** | `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` |
| **Root cause** | API uses `--reload`; DEBUG defaults true; frontend runs Vite dev; no Celery Beat; no Alembic entrypoint; no prod compose/images; containers run as root; no `.dockerignore`. |
| **Impact** | Treating Compose as production is unsafe and incomplete (stuck recoveries without Beat; empty schema on fresh up). |
| **Remediation** | Keep current compose as dev; add Beat + migrate path; add prod compose/multi-stage images; `.dockerignore`; non-root. |
| **Code change** | Yes |

---

## HIGH

### H1. No rate limiting on auth or publish
| | |
|--|--|
| **Module** | `backend/app/main.py`, `api/v1/auth.py`, `api/v1/events.py` |
| **Root cause** | No limiter middleware/dependencies. |
| **Impact** | Credential stuffing, registration spam, event flood. |
| **Remediation** | Redis-backed limits on login/register/publish/replay; `429` responses. |
| **Code change** | Yes |

### H2. Request body size only checks `Content-Length`
| | |
|--|--|
| **Module** | `backend/app/middleware/request_size.py` |
| **Root cause** | Chunked/missing length bypasses limit; invalid length coerced to `0`. |
| **Impact** | Large-body DoS risk. |
| **Remediation** | Streaming receive wrapper; reject invalid `Content-Length`. |
| **Code change** | Yes |

### H3. Weak production secret / DEBUG guards
| | |
|--|--|
| **Module** | `backend/app/core/config.py`, `.env.example` |
| **Root cause** | Production only rejects `SECRET_KEY` starting with `dev-only`; `DEBUG` and `REDIS_REQUIRED` unconstrained; placeholder `change-me…` would pass. |
| **Impact** | Production can boot with weak secrets, debug mode, or optional Redis while delivery depends on the broker. |
| **Remediation** | Fail closed: strong secret entropy, `DEBUG=false`, `REDIS_REQUIRED=true` in production; denylist placeholders. |
| **Code change** | Yes |

### H4. `SECRET_KEY` dual-use (JWT + API-key pepper)
| | |
|--|--|
| **Module** | `backend/app/core/security.py` |
| **Root cause** | Same key signs JWTs and peppers API-key HMAC hashes. |
| **Impact** | Coupled rotation; broader blast radius on leak. |
| **Remediation** | Dedicated `API_KEY_PEPPER` with documented fallback during migration. |
| **Code change** | Yes |

### H5. Endpoint signing secrets stored plaintext
| | |
|--|--|
| **Module** | `backend/app/models/endpoint.py`, `services/endpoint.py` |
| **Root cause** | Raw signing secret persisted (unlike hashed API keys). |
| **Impact** | DB compromise → forged webhooks. |
| **Remediation** | Encrypt at rest (Fernet/app key); decrypt for delivery; dual-read during migration. |
| **Code change** | Yes |

### H6. Frontend stores JWT in `localStorage` and API keys in `sessionStorage`
| | |
|--|--|
| **Module** | `frontend/src/features/auth/authSlice.ts`, `pages/ApiKeysPage.tsx`, `pages/EventsPage.tsx` |
| **Root cause** | Browser storage holds long-lived credentials. |
| **Impact** | XSS can exfiltrate JWT / publish keys. |
| **Remediation** | Prefer httpOnly cookies long-term; short-term: memory-only publish key, CSP, no `sessionStorage` for raw API keys. |
| **Code change** | Yes (incremental; cookie session is larger contract change) |

### H7. Commit-then-enqueue failure window
| | |
|--|--|
| **Module** | `api/v1/events.py`, `services/delivery_dispatch.py`, `services/delivery_recovery.py` |
| **Root cause** | Deliveries commit in DB; Celery enqueue runs in `BackgroundTasks` after response. Redis outage → `enqueue` fails; rows stay `PENDING` with `enqueued_at` null until Beat recovery. |
| **Impact** | Latency until recovery interval if Redis blips; acceptable if Beat runs and `REDIS_REQUIRED` fails fast in prod. |
| **Remediation** | Keep/strengthen recovery; mark successful enqueue; require Redis+Beat in production; optional outbox later. |
| **Code change** | Yes (harden; outbox optional) |

### H8. Compose missing Celery Beat + migrations
| | |
|--|--|
| **Module** | `docker-compose.yml` |
| **Root cause** | Worker only; no migrate job. |
| **Impact** | No scheduled recovery under Compose; fresh DBs lack schema. |
| **Remediation** | Add `celery-beat`; migrate entrypoint/docs. |
| **Code change** | Yes |

---

## MEDIUM

### M1. No HTTP security headers / TrustedHost
| Module | `backend/app/main.py` |
| Remediation | Security-header middleware; TrustedHost in production |
| Code change | Yes |

### M2. JWT `jti` unused (no revocation/logout denylist)
| Module | `core/security.py`, `api/deps.py` |
| Remediation | Redis denylist on logout or shorter TTL + refresh |
| Code change | Yes (optional for this pass: document + shorten default) |

### M3. Open self-service registration
| Module | `api/v1/auth.py` |
| Remediation | Feature flag / disable in production or CAPTCHA + rate limits |
| Code change | Yes |

### M4. Login timing oracle
| Module | `services/auth.py` |
| Remediation | Dummy Argon2 verify when user missing |
| Code change | Yes |

### M5. `JWT_ALGORITHM` unconstrained
| Module | `core/config.py` |
| Remediation | Allow-list `HS256` |
| Code change | Yes |

### M6. Password policy length-only
| Module | `utils/validators.py` |
| Remediation | Stronger checks (without breaking existing users on login) |
| Code change | Yes (register path) |

### M7. `/ready` always requires Redis ignoring `REDIS_REQUIRED`
| Module | `api/v1/health.py` |
| Remediation | Align readiness with production Redis requirement |
| Code change | Yes |

### M8. Dual API mount (`/` and `/api/v1`)
| Module | `main.py` |
| Remediation | Prefer versioned prefix; keep unprefixed health if needed |
| Code change | Careful (contract) — document; optional |

### M9. No scrapeable metrics
| Module | backend app |
| Remediation | Minimal Prometheus `/metrics` counters for delivery outcomes |
| Code change | Yes |

### M10. Docs / launcher dual Celery paths
| Module | `scripts/dev-celery.ps1`, docs |
| Remediation | Point Windows local at `run_celery_worker_dev.py` |
| Code change | Yes (docs/scripts) |

---

## LOW

### L1. Org suspended login message differs from invalid credentials
### L2. Incomplete production config tests
### L3. Thin frontend security tests
### L4. `dev-backend.ps1` binds `0.0.0.0`

---

## INFORMATIONAL (positive / local-only)

### I1. Tenant isolation
JWT and API-key paths scope by authenticated org; composite FKs on deliveries/subscriptions.

### I2. Auth crypto baselines
Argon2id passwords; API keys stored as HMAC hashes; raw key once on create/rotate.

### I3. Delivery concurrency
`with_for_update(skip_locked=True)`; unique `(event_id, endpoint_id)`; recovery includes `enqueued_at IS NULL` and stale `PROCESSING`.

### I4. Portable Redis 3.0
`tools/redis` + `run_celery_worker_dev.py` are Windows local workarounds. Production must use Redis 6+/7 (Compose `redis:7-alpine` or managed).

### I5. `.env` not tracked
`.gitignore` ignores `.env`; `git ls-files` shows it untracked. No secret printed in this audit.

### I6. CORS production guard
Wildcard CORS rejected when `APP_ENV=production`.

---

## Remediation order for Prompt 5 implementation

1. Production config fail-closed + tests
2. Rate limits + streaming body limits + security headers
3. Login timing + registration production flag + API_KEY_PEPPER
4. Signing-secret encryption (dual-read)
5. Enqueue bookkeeping + Redis/Beat production requirements
6. CI services + Compose Beat + `.dockerignore` + prod compose sketch
7. Frontend: remove `sessionStorage` for API keys; document JWT XSS residual risk
8. Minimal metrics + docs refresh

**Preserve** existing API contracts and the automated backend test suite.

---

## Remediation status (Prompt 5 implementation)

| ID | Status |
|----|--------|
| C1 CI Postgres/Redis | Done |
| C2 Compose Beat/migrate/prod overlay/dockerignore | Done (dev compose retained; prod overlay added) |
| H1 Rate limits | Done |
| H2 Streaming body size | Done |
| H3 Production fail-closed | Done |
| H4 API_KEY_PEPPER | Done |
| H5 Signing-secret encryption | Done (Fernet + dual-read) |
| H6 Browser storage | Partial — publish key memory-only; JWT still `localStorage` (documented) |
| H7 Commit-then-enqueue window | Hardened — sync enqueue after commit; Beat recovers; outbox deferred |
| H8 Compose Beat + migrate | Done |
| M1–M10 | Done or documented residual (JWT denylist / dual mount) |

Details: [production-hardening.md](./production-hardening.md).
