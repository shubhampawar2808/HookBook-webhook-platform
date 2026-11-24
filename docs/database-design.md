# HookForge Database Design

Phase 2 implements the core domain schema via Alembic revision `0002_domain_tables` (after `0001_foundation`).

All timestamps are **timezone-aware UTC**.

## Tenant Strategy

Shared schema with `organization_id` on tenant-owned tables, plus composite foreign keys so child rows cannot reference parents from another organization.

## Entities

### Organization
| Column | Notes |
|--------|-------|
| id | UUID PK |
| name | Display name |
| slug | Globally unique |
| status | `active` / `suspended` |
| created_at, updated_at | UTC |

### User
| Column | Notes |
|--------|-------|
| id | UUID PK |
| organization_id | FK → organizations |
| email | Unique per organization |
| password_hash | Argon2id only |
| full_name | |
| role | `owner` / `admin` / `member` |
| status | `active` / `disabled` |
| last_login_at | Nullable |
| created_at, updated_at | UTC |

Unique `(id, organization_id)` supports composite FKs from API keys / endpoints.

### APIKey
| Column | Notes |
|--------|-------|
| id | UUID PK |
| organization_id | FK → organizations |
| name | Label |
| key_prefix | Non-secret display prefix |
| key_hash | Unique HMAC-SHA256 (peppered) |
| status | `active` / `revoked` / `expired` |
| last_used_at, expires_at, revoked_at | Nullable |
| created_by | Same-org user (composite FK) |
| created_at | UTC |

### WebhookEndpoint
| Column | Notes |
|--------|-------|
| id | UUID PK |
| organization_id | FK |
| name, url, description | URL validated in app |
| status | `active` / `disabled` |
| created_by | Same-org user |
| created_at, updated_at | UTC |

### EventType
| Column | Notes |
|--------|-------|
| id | UUID PK |
| organization_id | FK |
| name | Unique per organization |
| description | Optional |
| created_at | UTC |

### EndpointSubscription
| Column | Notes |
|--------|-------|
| id | UUID PK |
| organization_id | FK |
| endpoint_id | Composite FK with org → webhook_endpoints |
| event_type_id | Composite FK with org → event_types |
| created_at | UTC |

Unique `(endpoint_id, event_type_id)`.

### Event
| Column | Notes |
|--------|-------|
| id | UUID PK |
| organization_id | FK |
| event_type_id | Composite FK with org → event_types |
| event_id | Public unique id (`evt_...`) |
| payload | JSONB |
| status | `accepted` (delivery states come later) |
| created_at | UTC |

**No delivery / delivery_attempt tables in Phase 2.**

## Relationships

```
Organization
├── User (many)
├── APIKey (many)
├── WebhookEndpoint (many)
├── EventType (many)
├── EndpointSubscription (many) ── Endpoint + EventType
└── Event (many) ── EventType
```

## Migrations

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python ../scripts/verify_db_identity.py
alembic upgrade head
alembic current
```

Downgrade of `0002_domain_tables` drops the domain tables only (does not touch `0001_foundation`).
