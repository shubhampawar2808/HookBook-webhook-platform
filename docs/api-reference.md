# HookForge API Reference (Phase 2)

Base prefix: `/api/v1`
OpenAPI UI: `http://localhost:8000/docs` (non-production)

## Auth

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/auth/register` | none | Creates org + owner; returns JWT |
| POST | `/auth/login` | none | Body: `organization_slug`, `email`, `password` |
| GET | `/auth/me` | JWT | Current user + org name |

## Organizations

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/organizations/me` | JWT | Current tenant |
| PATCH | `/organizations/me` | JWT OWNER | Update name/slug |

## API Keys

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/api-keys` | JWT OWNER/ADMIN | Returns raw key once |
| GET | `/api-keys` | JWT | Paginated metadata only |
| DELETE | `/api-keys/{id}` | JWT OWNER/ADMIN | Revoke |
| POST | `/api-keys/{id}/rotate` | JWT OWNER/ADMIN | Revoke + new key |

Format: `Authorization: Bearer hfk_<prefix>_<secret>`

## Endpoints

| Method | Path | Auth |
|--------|------|------|
| POST | `/endpoints` | JWT |
| GET | `/endpoints` | JWT (paginated) |
| GET | `/endpoints/{id}` | JWT |
| PATCH | `/endpoints/{id}` | JWT |
| DELETE | `/endpoints/{id}` | JWT OWNER/ADMIN |

## Event Types

| Method | Path | Auth |
|--------|------|------|
| POST | `/event-types` | JWT OWNER/ADMIN |
| GET | `/event-types` | JWT |
| GET | `/event-types/{id}` | JWT |

## Subscriptions

| Method | Path | Auth |
|--------|------|------|
| POST | `/endpoints/{id}/subscriptions` | JWT |
| GET | `/endpoints/{id}/subscriptions` | JWT |
| DELETE | `/endpoints/{id}/subscriptions/{sub_id}` | JWT |

## Events

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| POST | `/events` | **API key** | Persists event; creates deliveries; workers deliver async |

Response includes `delivery=accepted|none` and `delivery_count`.

## Deliveries

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/deliveries` | JWT | Paginated; filters: status, event_id, endpoint_id, dates |
| GET | `/deliveries/dead-letter` | JWT | Dead-letter queue |
| GET | `/deliveries/{id}` | JWT | Detail |
| GET | `/deliveries/{id}/attempts` | JWT | Attempt history |
| POST | `/deliveries/{id}/replay` | JWT OWNER/ADMIN | Replay failed/dead-letter |

Signing secrets are never returned from delivery APIs. See [webhook-delivery.md](webhook-delivery.md).
