# HookForge

**Webhook Delivery & Event Management Platform**

HookForge is an independent developer-infrastructure product for registering webhook endpoints, publishing events, managing subscriptions, and delivering signed HTTP notifications with retries, dead-letter handling, and an operator dashboard.

> Portfolio / local-development project. This repository has **not** been deployed to a public production environment as part of this release.

---

## Features

- **Multi-tenant organizations** with JWT operator auth and hashed API keys (`hfk_…`)
- **Endpoints, event types, and subscriptions** with organization isolation
- **Event publishing** that creates durable delivery records
- **Asynchronous webhook delivery** via Celery (HMAC-SHA256 signing, retries, backoff, DLQ, replay)
- **SSRF protections** for outbound delivery URLs
- **Operator dashboard** for overview, events, endpoints, deliveries, dead-letter, API keys, and settings
- **Production-oriented hardening** (rate limits, security headers, fail-closed production config, encrypted endpoint signing secrets at rest)

## Design identity — Industrial Precision

The frontend uses **Industrial Precision – The Webhook Observatory**:

- Carbon / graphite / moss surfaces with bone text and copper accents
- Display typography: Fraunces · UI: Source Sans 3 · Mono: JetBrains Mono
- Observatory-style delivery visibility rather than generic SaaS chrome

Design tokens live in `frontend/src/styles/tokens.css`.

## Architecture

```text
                    ┌─────────────────────────┐
                    │  React + Vite Dashboard │
                    │   (Industrial Precision)│
                    └────────────┬────────────┘
                                 │ HTTPS / JSON
                    ┌────────────▼────────────┐
                    │     FastAPI (/api/v1)    │
                    │  JWT · API keys · CRUD   │
                    └──────┬───────────┬──────┘
                           │           │
              ┌────────────▼──┐   ┌────▼─────────────┐
              │  PostgreSQL   │   │ Redis (broker)   │
              │  system of    │   │ Celery queues    │
              │  record       │   └────┬─────────────┘
              └────────────▲──┘        │
                           │     ┌─────▼──────────────┐
                           └─────┤ Celery Worker+Beat │
                                 │ signed HTTP POST   │
                                 │ retries · recovery │
                                 └─────────┬──────────┘
                                           │
                                 ┌─────────▼──────────┐
                                 │ Customer endpoints │
                                 └────────────────────┘
```

Deeper detail: [docs/architecture.md](docs/architecture.md) · [docs/webhook-delivery.md](docs/webhook-delivery.md) · [docs/database-design.md](docs/database-design.md)

## Technology stack

| Layer | Stack |
|-------|--------|
| Backend | Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2 async, Alembic, asyncpg |
| Data | PostgreSQL 16, Redis 7 (Compose) |
| Workers | Celery worker + Beat |
| Frontend | React 18, TypeScript, Vite, React Router, Redux Toolkit, Axios |
| Ops | Docker Compose, GitHub Actions |
| Quality | Pytest, HTTPX, Ruff, Vitest, Testing Library |

## Screenshots

Add captures under [`docs/screenshots/`](docs/screenshots/) and link them here for the portfolio.

| View | File (suggested) |
|------|------------------|
| Overview | `docs/screenshots/overview.png` |
| Deliveries | `docs/screenshots/deliveries.png` |
| Delivery detail | `docs/screenshots/delivery-detail.png` |
| Endpoints | `docs/screenshots/endpoints.png` |
| API keys | `docs/screenshots/api-keys.png` |

Example markdown once images exist:

```markdown
![Overview](docs/screenshots/overview.png)
```

## Repository layout

```text
HookForge/
├── backend/                 # FastAPI app, Alembic, tests, Celery
├── frontend/                # React + Vite dashboard
├── infrastructure/          # Docker helper assets (e.g. Postgres init)
├── docs/                    # Architecture, API, hardening, screenshots
├── scripts/                 # Windows launcher + local helpers
├── .github/workflows/       # CI
├── docker-compose.yml       # Local full stack
├── docker-compose.prod.yml  # Production-oriented overlay (local/staging sketch)
├── .env.example
└── README.md
```

## Local Windows setup

### Prerequisites

- Python **3.12+**
- Node.js **20+** (22 recommended)
- PostgreSQL with database `hookforge`, role `hookforge_app`, and test DB `hookforge_test`
- Redis (portable under `tools/redis/` for the Windows launcher, **or** Docker Redis 7, **or** another local Redis 6+/7)
- Optional: Docker Desktop for Compose

### 1. Environment

```powershell
copy .env.example .env
```

Edit `.env`:

- Set a strong local `SECRET_KEY`
- Set `DATABASE_URL` to your local role/password (never commit `.env`)
- Keep `VITE_API_BASE_URL=http://localhost:8000` for local UI

`.env.example` contains **placeholders only** (e.g. `CHANGE_ME`). Compose defaults such as `hookforge`/`hookforge` are for **local Docker only**.

### 2. Database migrations

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python ..\scripts\verify_db_identity.py
alembic upgrade head
```

Migrations: `0001_foundation` → `0002_domain_tables` → `0003_webhook_deliveries` → `0004_endpoint_secret_width`.

### 3. One-command Windows launcher (recommended)

```powershell
# From repo root — starts Redis + API + Celery worker/beat + local webhook receiver
.\scripts\dev-up.ps1

.\scripts\dev-status.ps1
.\scripts\dev-logs.ps1 -Service api
.\scripts\dev-down.ps1
```

The launcher verifies DB identity (`hookforge` / `hookforge_app`), tracks PIDs under `.run/` (gitignored), and does **not** stop PostgreSQL.

**Frontend** (separate terminal):

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

### 4. Manual Redis / Celery / API

```powershell
# API
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Worker — portable Redis 3.0 on Windows needs remote control disabled:
python ..\scripts\run_celery_worker_dev.py

# Beat (delivery recovery)
celery -A app.workers.celery_app.celery_app beat --loglevel=INFO
```

On Redis **6+/7**, a normal Celery worker (`--pool=solo` on Windows) is fine. Portable Redis 3.0 is a **local Windows convenience only**, not a production posture.

### 5. Docker Compose (optional)

```powershell
docker compose up --build
```

Includes Postgres, Redis 7, API (migrate on start), Celery worker, Celery Beat, and Vite.

Production-oriented overlay (still local/staging — **not** a verified public deploy):

```powershell
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Testing

```powershell
# Backend (uses hookforge_test — never point the normal API at the test DB)
cd backend
pytest -q
ruff check app tests

# Frontend
cd frontend
npm run typecheck
npm run test:run
npm run build
```

CI (`.github/workflows/ci.yml`) runs backend lint/tests with Postgres + Redis services and frontend typecheck/test/build.

## API documentation

With the API running in development:

| Resource | URL |
|----------|-----|
| OpenAPI UI | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Liveness | http://localhost:8000/health |
| Readiness | http://localhost:8000/ready |
| Versioned API | http://localhost:8000/api/v1/… |

Human-readable reference: [docs/api-reference.md](docs/api-reference.md)

## Security features

- Argon2id password hashing; JWT access tokens with required claims
- API keys stored as peppered HMAC hashes; raw key shown once
- Endpoint signing secrets encrypted at rest (Fernet) with legacy plaintext dual-read
- Organization scope taken from authenticated identity (not client-supplied org IDs)
- SSRF checks on delivery URLs; redirects disabled
- Redis-backed rate limiting on sensitive routes
- Streaming request body size limits
- Security headers (CSP frame-ancestors, nosniff, Referrer-Policy, HSTS in production config)
- Production fail-closed settings (`DEBUG`, `REDIS_REQUIRED`, SSRF localhost flags, registration)

Hardening notes: [docs/production-hardening.md](docs/production-hardening.md) · [docs/release-checklist.md](docs/release-checklist.md)

## Project limitations

- **Not production-hosted** in this release; no multi-region or managed-cloud verification claimed
- JWT stored in browser `localStorage` (XSS residual); httpOnly cookie sessions not implemented
- No JWT revocation denylist on logout
- Delivery is **at-least-once**; receivers must be idempotent
- Commit-then-enqueue: if the broker fails after DB commit, Beat recovers `PENDING` rows (short delay)
- Windows portable Redis 3.0 is incompatible with Celery remote control (launcher uses a compatibility worker)
- Self-service registration is for local/demo; disable in production (`ALLOW_PUBLIC_REGISTRATION=false`)
- OpenAPI docs are disabled when `APP_ENV=production`

## License

Proprietary / portfolio project — rights reserved by the author unless otherwise stated.
