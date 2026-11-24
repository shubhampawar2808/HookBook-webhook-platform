# HookForge Release Checklist

Use before any staging or production cutover. **Do not deploy externally without explicit approval.**

## Pre-release

- [ ] Phase 0 audit reviewed; CRITICAL/HIGH items remediated or accepted with owners
- [ ] `pytest` green on `hookforge_test`
- [ ] Frontend `npm run typecheck`, `npm run test -- --run`, `npm run build` green
- [ ] CI green on the release commit
- [ ] Alembic head applied (`0004_endpoint_secret_width` or later)
- [ ] `.env` / secrets managed outside git; `.env.example` placeholders only
- [ ] No plaintext production passwords in docs or tickets

## Configuration gates

- [ ] `APP_ENV=production`
- [ ] `DEBUG=false`
- [ ] Strong `SECRET_KEY`
- [ ] `REDIS_REQUIRED=true`
- [ ] `ALLOW_PUBLIC_REGISTRATION=false`
- [ ] SSRF localhost flags false
- [ ] Explicit HTTPS CORS origins
- [ ] Celery worker + Beat running against Redis 6+/7

## Runtime verification

- [ ] `/health` returns ok
- [ ] `/ready` requires DB + Redis
- [ ] Publish → delivery → signed HTTP → attempt history
- [ ] Forced Redis blip leaves PENDING rows recovered by Beat
- [ ] Rate limit returns 429 on auth abuse path
- [ ] Metrics endpoint reachable for an authenticated operator

## Rollback

- [ ] Previous image/tag known
- [ ] DB backup taken before migrate
- [ ] Documented reverse of any irreversible data change
