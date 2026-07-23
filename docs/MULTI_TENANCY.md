# Multi-Tenant Workspace & Subdomain Architecture

Every hostel is an isolated **workspace** with a permanent URL:

```
Everest International Hostel  ->  workspace username "everest"  ->  https://everest.myhostel.com
```

The hostel *name* is editable; the **workspace username** (tenant slug) is the
permanent, globally-unique identifier used for routing. It doubles as the
subdomain label, so its rules are exactly the DNS-label rules.

---

## Architecture overview

| Concern              | Where it lives                                                                      |
| -------------------- | ----------------------------------------------------------------------------------- |
| Tenant model         | `apps/tenants/models.py` — `Hostel` (slug, status, owner, locale, soft delete) |
| Username rules       | `apps/tenants/validators.py` (pure, no DB)                                        |
| DB-touching services | `apps/tenants/services.py` (availability, suggestions, provisioning, lifecycle)   |
| Cached lookup        | `apps/tenants/cache.py` (Redis cache-aside + negative caching)                    |
| Request resolution   | `apps/tenants/middleware.py` — `TenantResolutionMiddleware`                    |
| Workspace API        | `apps/tenants/views.py` — `WorkspaceViewSet` (`/api/tenants/workspaces/`)    |
| Tests                | `apps/tenants/tests/` + `apps/common/tests/test_middleware.py`                  |

Legacy compatibility is preserved everywhere: `request.hostel`, the
`X-HOSTEL-CODE` / `X-HOSTEL-ID` headers, JWT hostel claims, and the
`HTL-XXXXXXXX` Hostel ID all keep working unchanged.

## Request lifecycle

```
Request to everest.myhostel.com
  │
  ├─ Django host validation (ALLOWED_HOSTS — ".myhostel.com" auto-added)
  │
  ├─ TenantResolutionMiddleware              <-- BEFORE authentication
  │    extract identifier (subdomain > X-WORKSPACE > X-HOSTEL-CODE > X-HOSTEL-ID)
  │    cached tenant lookup (Redis, ~<2ms; DB fallback ~<10ms)
  │    identifier presented but unknown  -> 404 workspace_not_found (request ends)
  │    suspended/expired/pending        -> 403 with machine-readable code
  │    archived / soft-deleted          -> 404 (treated as gone)
  │    ok -> request.tenant = request.hostel = <Hostel>
  │
  ├─ Authentication (CookieJWTAuthentication)
  │    token's hostel claims override request.hostel *after membership check*
  │    — a spoofed workspace header can never switch an authenticated session
  │
  ├─ Permissions (HasHostelContext / IsHostelResolved)
  │    caller must be an active member of the resolved workspace
  │
  └─ Business logic — all queries scoped by request.hostel
```

Exemptions: `OPTIONS` preflights and `/health/*` never resolve a tenant.
Requests to the root domain (or reserved subdomains like `www`/`api`) resolve
no tenant and proceed — that is where signup, marketing and auth endpoints
live.

### Resolution sources

1. **Subdomain** of `TENANT_BASE_DOMAIN` — canonical (`everest.myhostel.com`).
2. **`X-WORKSPACE: everest`** — for split-domain deployments (current
   topology: Vercel serves the SPA on the wildcard domain, the API lives on
   Render). The SPA forwards the workspace it is serving.
3. **`X-HOSTEL-CODE: HTL-XXXXXXXX`** — legacy header (existing SPA flows).
4. **`X-HOSTEL-ID: <uuid>`** — legacy header.

If *any* of these is present but does not resolve to a live workspace the
request is terminated — it never reaches auth or business logic.

## Workspace username rules

Configured in settings; enforced in `apps/tenants/validators.py`:

* globally unique (DB unique constraint on `tenants_hostel.slug`)
* lowercase letters, digits, hyphens; must start/end alphanumeric
* no spaces / underscores / unicode / symbols
* length: `WORKSPACE_USERNAME_MIN_LENGTH` (3) to
  `WORKSPACE_USERNAME_MAX_LENGTH` (32, hard-capped at 63 = DNS label limit)
* input is trimmed + lowercased automatically
* not reserved: built-in list (`admin`, `api`, `www`, `mail`, `root`,
  `dashboard`, `system`, `support`, `login`, `auth`, `docs`, `static`,
  `media`, `assets`, `cdn`, `status`, `health`, `monitor`, `test`, …) plus
  the `RESERVED_WORKSPACE_NAMES` env extension. Reserved names can be added
  per-deployment, never removed.
* **permanent** — `Hostel.save()` silently restores any attempted slug change
  (same mechanism as the legacy `code`).

## Workspace lifecycle & status

`Hostel.status`: `pending | trial | active | suspended | expired | archived`,
plus `is_active`, `is_deleted`/`deleted_at` (soft delete — tenant data is
never physically removed).

| Status / flag         | Middleware behaviour       |
| --------------------- | -------------------------- |
| `trial`, `active` | request served             |
| `suspended`         | 403`workspace_suspended` |
| `expired`           | 403`workspace_expired`   |
| `pending`           | 403`workspace_pending`   |
| `is_active=False`   | 403`workspace_inactive`  |
| `archived`/deleted  | 404`workspace_not_found` |

Transitions live in `services.py` (`activate_workspace`, `suspend_workspace`,
`archive_workspace`, `restore_workspace`, `soft_delete_workspace`) — each
writes an `AuditEvent` and invalidates the tenant cache.

## Workspace provisioning (signup)

`services.provision_workspace(...)` runs in **one transaction**: tenant +
workspace username + subdomain, owner FK, `UserHostel` membership link,
default settings/configuration (roles, permission groups, features seeded
into `Hostel.settings`), trial window (`TENANT_TRIAL_DAYS`, default 14), and
the initial audit/activity records. Any failure rolls back everything — no
orphan users or hostels.

Signup (`POST /api/auth/signup/`) accepts an optional `workspace_username`;
when omitted one is auto-generated from the hostel name (slugify + uniqueness
suffix). The signup response now includes
`workspace: {username, url, status}`.

## API

All under `/api/tenants/workspaces/` (responses use the standard
`{success, message, data, meta}` envelope):

| Endpoint                               | Auth                                           | Notes                                                                                                              |
| -------------------------------------- | ---------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `GET availability/?username=everest` | public, throttled`workspace_check` (30/min)  | `{available, reason, suggestions[]}`; reasons: `taken`, `reserved`, `invalid`, `too_short`, `too_long` |
| `POST /`                             | authenticated, throttled`workspace` (5/hour) | register a workspace (`hostel_name`, optional `workspace_username`, phone/address/locale)                      |
| `GET /`                              | member                                         | my workspaces                                                                                                      |
| `GET current/`                       | member                                         | the workspace resolved for this request                                                                            |
| `GET {id}/`                          | member                                         | detail                                                                                                             |
| `PATCH {id}/`                        | OWNER/ADMIN                                    | display fields only — never the slug                                                                              |
| `DELETE {id}/`                       | OWNER/ADMIN                                    | soft delete                                                                                                        |
| `POST {id}/suspend                     | archive                                        | restore/`                                                                                                          |

## Caching

Redis-backed (`CACHES` uses `REDIS_URL`; override with `CACHE_URL`). Tenants
are cached under `tenant:v1:{slug|code|id}:<value>` for `TENANT_CACHE_TTL`
(300s); unknown identifiers are negative-cached for
`TENANT_NEGATIVE_CACHE_TTL` (60s) so bursts at nonexistent subdomains can't
hammer the DB. `post_save`/`post_delete` signals invalidate all three keys on
any change (rename, status, subscription, archive). If Redis is down, lookup
falls through to the database — a cache outage never breaks requests.

## Database schema changes

Migration `tenants/0009` adds: `slug` (unique), `status` (indexed), `owner`
FK, `timezone`, `currency`, `language`, `logo`, `trial_ends_at`,
`is_deleted`, `deleted_at`, plus composite indexes
(`is_active,status` and `is_deleted`). Migration `tenants/0010` backfills
slugs for pre-existing hostels (slugified name, falling back to the lowercased
hostel code, with uniqueness suffixes; reserved names avoided).

## Tenant isolation

Defense in depth, unchanged in principle but now enforced earlier:

1. Middleware kills requests to unknown/suspended/archived workspaces before
   auth.
2. `CookieJWTAuthentication` binds the session to the hostel in the token and
   verifies membership — a client-supplied workspace header can never move an
   authenticated session to another tenant.
3. `HasHostelContext` / `IsHostelResolved` verify active membership of the
   resolved hostel; denials raise 403 and are audited (`ACCESS_DENIED`).
4. Every scoped model FK-links to `tenants.Hostel` (`HostelScopedModel`) and
   viewsets filter on `request.hostel`.

## Frontend architecture

The frontend mirrors the backend rules so feedback is instant, while the
backend stays authoritative:

| Concern                                                | Where it lives                                                                                                                                                              |
| ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Username rules + host parsing +`workspaceStore`      | `frontend/packages/utils/src/workspace.ts` (pure logic also exported as `@hostel/utils/workspace` for the Edge proxy)                                                   |
| `X-Workspace` request header + workspace error codes | `frontend/packages/api/src/apiClient.ts` (`isWorkspaceError`, `err.code`)                                                                                             |
| SSR workspace context                                  | `frontend/packages/config/src/securityProxy.ts` — derives `x-workspace` from the Host header (client-sent values are discarded) for both zones                         |
| Workspace API client + types                           | `frontend/apps/admin/src/features/tenants/{api/workspaces.api.ts, types/workspaces.types.ts}`                                                                             |
| Live availability UI                                   | `features/tenants/hooks/useWorkspaceAvailability.ts` (debounced + abortable) and `components/WorkspaceUsernameField.tsx`                                                |
| Signup integration                                     | `(public)/signup` — username auto-derived from the hostel name until edited, availability-gated submit; `(public)/verify-otp` persists the workspace and shows its URL |

Key behaviors:

* **`X-Workspace` header** is attached to every API call *only* when the page
  is served from a workspace subdomain — derived from `window.location`,
  never from stored state, so it always mirrors the URL. On the current
  single-domain topology nothing changes (legacy `X-Hostel-Code` + JWT claims
  keep working).
* **Availability checking** validates locally first (same rules as the
  backend: format, length, reserved list) and only then calls the public
  availability API, debounced 400 ms with request abortion. Taken names show
  the server's one-click suggestions.
* **Workspace errors**: envelope `meta.code` values
  (`workspace_not_found`, `workspace_suspended`, …) surface as `err.code`;
  use `isWorkspaceError(err)` from `@hostel/api` to branch on them.
* Config: `NEXT_PUBLIC_TENANT_BASE_DOMAIN` (keep in sync with the backend's
  `TENANT_BASE_DOMAIN`), optional `NEXT_PUBLIC_TENANT_URL_SCHEME` /
  `NEXT_PUBLIC_WORKSPACE_USERNAME_MIN_LENGTH` / `..._MAX_LENGTH`. Wired as
  build args + runtime env in both Dockerfiles and docker-compose.

## Local development

`TENANT_BASE_DOMAIN` defaults to `localhost` and `.localhost` is auto-added
to `ALLOWED_HOSTS`, so this works with zero DNS setup (browsers resolve
`*.localhost` to `127.0.0.1`):

```
http://everest.localhost:8000/api/...      # workspace request
http://localhost:8000/api/...              # root domain (signup, marketing)
curl -H "X-WORKSPACE: everest" http://localhost:8000/api/...
```

Tests: `cd backend && pytest apps/tenants/`.

## Production / infrastructure preparation

Current topology (Vercel SPA + Render API) needs **no infrastructure change**:
the SPA sends `X-WORKSPACE` (or the legacy headers) and everything works
today. To serve the API on the wildcard domain later:

1. **DNS**: `A`/`CNAME` record for `*.myhostel.com` -> the edge/proxy.
2. **TLS**: wildcard certificate (`*.myhostel.com`), e.g. Let's Encrypt
   DNS-01.
3. **Nginx**: `server_name .myhostel.com;` in the API server block —
   no per-tenant blocks needed; the middleware does the routing.
4. **Django**: set `TENANT_BASE_DOMAIN=myhostel.com` (the wildcard host entry
   is added to `ALLOWED_HOSTS` automatically) and add the wildcard origin
   pattern to CORS if the SPA calls cross-origin.
5. Vercel: add `*.myhostel.com` as a wildcard domain to the frontend project.

Custom (white-label) domains are intentionally **not** implemented yet; the
resolution pipeline is a single function (`extract_workspace_subdomain` +
cache lookup), so adding a `hostname -> tenant` table lookup later is a
non-structural change.

## Troubleshooting

| Symptom                                            | Cause / fix                                                                                                                                            |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `400 Bad Request` on a tenant subdomain          | Host failed`ALLOWED_HOSTS` — check `TENANT_BASE_DOMAIN` matches the domain being used                                                             |
| `404 workspace_not_found` on a valid-looking URL | slug doesn't exist, workspace archived/soft-deleted, or nested subdomain (`a.b.domain`)                                                              |
| `403 workspace_suspended/expired/pending`        | workspace status gate — see lifecycle table above                                                                                                     |
| Stale tenant after a change                        | cache invalidation happens via`post_save`; direct SQL updates bypass it — call `invalidate_tenant_cache(hostel)` or wait out `TENANT_CACHE_TTL` |
| Availability endpoint 429                          | `THROTTLE_WORKSPACE_CHECK` (default 30/min per IP)                                                                                                   |
| Tenant changes don't apply in Docker dev           | backend code is bind-mounted with auto-reload; for image-baked (prod) containers rebuild with`docker compose up -d --build`                          |
| Frontend edits not visible in Docker dev           | Windows bind mounts don't always propagate file-watch events into the container —`docker compose restart frontend admin` forces a fresh compile     |
