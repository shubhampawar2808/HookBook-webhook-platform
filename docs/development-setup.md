# HookForge Development Setup

## Prerequisites

- Python **3.12+** recommended (3.11 works for local API work; Docker uses 3.12)
- Node.js **20+** (22 recommended)
- Docker Desktop (optional but recommended for Postgres/Redis/full stack)
- Git

## Quick start with Docker Compose

```powershell
cd <repo-root>
copy .env.example .env
docker compose up --build
```

Services:

| Service | URL / Port |
|---------|------------|
| Frontend | http://localhost:5173 |
| Backend | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Health | http://localhost:8000/health |
| Ready | http://localhost:8000/ready |
| PostgreSQL | 127.0.0.1:5432 |
| Redis | 127.0.0.1:6379 |

Validate compose file without starting:

```powershell
docker compose config
```

## Local backend (without Docker app containers)

1. Start PostgreSQL and Redis (Docker or local installs).
2. Copy environment file:

```powershell
copy .env.example .env
```

3. Create a virtualenv and install deps:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

4. Run migrations:

```powershell
alembic current
alembic upgrade head
```

5. Prefer the Windows launcher (binds API to localhost, tracks PIDs under `.run/`):

```powershell
.\scripts\dev-up.ps1
.\scripts\dev-status.ps1
```

Manual API:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

6. Celery worker (separate terminal). On portable Redis 3.0 (Windows), use:

```powershell
.\scripts\dev-celery.ps1
# equivalent: python scripts\run_celery_worker_dev.py
```

On Redis 6+/7:

```powershell
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO --pool=solo
```

Always run Beat for recovery:

```powershell
celery -A app.workers.celery_app.celery_app beat --loglevel=INFO
```

## Local frontend

```powershell
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Ensure `VITE_API_BASE_URL=http://localhost:8000` in `.env` or the shell.

## Testing

Backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest -q
ruff check app tests
```

Frontend:

```powershell
cd frontend
npm run test:run
npm run typecheck
```

## Windows notes

- Prefer binding Postgres/Redis to `127.0.0.1` (already set in Compose).
- If PowerShell blocks scripts, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- Docker Desktop must be running before `docker compose` commands.

## Environment variables

See `.env.example` for the full list. Never commit `.env`.
