# Production Deployment, Enterprise Security & Operations

Prompt 06 — the operational manual for running the multi-tenant platform
(Prompts 01–05) in production. This consolidates and extends the existing
infra docs (`deploy/README.md`, `docs/HTTPS.md`, `SECURITY.md`,
`docs/CUSTOM_DOMAINS.md`).

---

## Architecture

```
Internet
  │
CDN / Cloudflare (optional; proxy + cache static/media)
  │
Edge — Nginx (deploy/nginx) OR Traefik (deploy/docker-compose.traefik.yml)
  │     HTTPS-only · wildcard *.DOMAIN + custom domains · rate limits ·
  │     security headers · gzip · upload caps · /metrics blocked
  ├────────────► frontend (Next.js client zone — marketing + public sites)
  │                └── admin zone (Next.js, internal; reached via rewrites)
  └────────────► web (Django/DRF + Gunicorn)
                    ├── redis        cache · tenant/RBAC/membership lookups ·
                    │                sessions · Celery broker · throttle state
                    ├── celery_worker / celery_beat   (emails, backups, domain
                    │                revalidation, cleanup, reports)
                    ├── postgres     (or managed: Neon/RDS/Render)
                    └── object storage (media volume | S3/MinIO/R2)
```

Two supported topologies:

* **Managed (current production)** — Vercel (frontend zones) + Render (API) +
  managed Postgres/Redis. Git auto-deploy on merge to `main`.
* **Self-hosted VPS** — everything above via `deploy/docker-compose.prod.yml`
  with pre-built GHCR images and health-gated rollouts.

## Multi-tenant routing at the edge

Nginx serves `server_name ${DOMAIN} *.${DOMAIN}` **and** is the
`default_server`, so every workspace subdomain resolves automatically and
tenant custom domains land on the app with zero per-tenant edge config —
tenancy is decided by the tenant middleware from the Host header.

TLS:
* `*.DOMAIN` requires a **wildcard certificate** — Let's Encrypt **dns-01**
  (`deploy/certbot/` has issue + renew + deploy-hook automation).
* Custom domains: per-domain http-01 certs (certbot) appended to the served
  bundle, or use the **Traefik overlay** which issues them automatically on
  first request (`docker compose -f …prod.yml -f …traefik.yml up -d --scale nginx=0`).
* Django side: add activated customer domains to `ALLOWED_HOSTS` +
  `CSRF_TRUSTED_ORIGINS` in `deploy/.env` (the `.${DOMAIN}` wildcard entry is
  auto-added from `TENANT_BASE_DOMAIN`).

## Deployment (self-hosted)

CI (`.github/workflows/`): `ci.yml` (tests) → `build-images.yml` (backend,
client, admin images → GHCR, tagged `<tag>` + `<sha>`, with
`NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_TENANT_BASE_DOMAIN` baked in) →
`deploy-staging.yml` (push to main) / `deploy-production.yml` (release tag)
→ SSH → `deploy/deploy.sh` → `production-validation.yml` smoke checks.

`deploy.sh` is the zero-downtime rollout: pull images → **safety pg_dump** →
apply migrations (only here — replicas never migrate) → `compose up -d
--wait` (health-gated recreation) → verify `/health/*`; **any failure
auto-rolls back** to the recorded previous images (`rollback.sh` for manual
rollback). Graceful shutdown rides Docker's SIGTERM + Gunicorn's connection
draining.

## Statelessness & horizontal scaling

No local state on web/worker replicas:
* auth = JWT cookies (self-contained, workspace-bound);
* Django sessions (admin only) = cache-backed;
* cache/throttle/tenant/RBAC lookup state = Redis;
* media = named volume on single-host, **`STORAGE_BACKEND=s3`** (AWS S3 /
  MinIO / Cloudflare R2 via django-storages) for multi-replica — the bundled
  MinIO ships behind `--profile storage`.

Scale with `docker compose up -d --scale web=3 --scale celery_worker=2`
behind the edge (or split hosts). Postgres: `CONN_MAX_AGE` + health checks
are on; put pgbouncer (transaction pooling) in front past ~100 concurrent
connections; `DB_STATEMENT_TIMEOUT_MS` kills runaway queries. Read replicas:
add a `replica` DB alias + router when needed (no code depends on
single-DB).

## Security (enforced today)

Edge: HTTPS-only w/ permanent redirects, TLS 1.2/1.3 (`snippets/ssl.conf`),
HSTS incl. subdomains + preload, per-IP rate limits (tight on auth paths),
upload caps, `/metrics` blocked. App: strict CSP (nonce + strict-dynamic on
the frontend; locked-down API CSP), COOP/COEP/CORP, Permissions-Policy,
X-Frame-Options, nosniff, secure/httpOnly/SameSite cookies, CSRF on
cookie-borne writes, ORM-only queries, host validation (ALLOWED_HOSTS +
tenant middleware rejecting unknown workspace identifiers), django-axes
lockouts, DRF throttling (Redis-backed), workspace-bound tokens + pwv
(Prompt 02), per-tenant RBAC, honeypotted public forms, Pillow-verified
uploads, immutable audit trail with actor/workspace/IP/device (async
writes). Secrets live only in env files (`deploy/.env`, chmod 600) / CI
secrets — never in images or the repo; Docker secrets are a drop-in swap
(`env_file` → `secrets:`) when moving to Swarm/K8s.

## Monitoring & logging

* `/health/` liveness + readiness probes: `database`, `cache`, `celery`,
  **`storage`** (write/read/delete probe on the active media backend),
  **`queue`** (Celery backlog depth). None leak secrets — generic errors only.
* `PROMETHEUS_ENABLED=True` exposes `/metrics` (django-prometheus:
  request/DB/cache metrics) — scraped on the Docker network, blocked at the
  edge; point Prometheus + Grafana at it.
* Logs: structured per-request line (request id, duration, DB time/queries,
  user, workspace, bytes) from `RequestTimingMiddleware`; `X-Request-ID`
  echoes to clients for correlation; slow requests (> `SLOW_REQUEST_MS`) log
  at WARNING; Sentry via `SENTRY_DSN`; audit events queryable per workspace
  (Settings → Activity) and exportable via the audit API.
* Domain health: daily Celery task re-validates custom-domain DNS + SSL
  expiry and writes audit warnings (Prompt 05).

## Backups & disaster recovery

Three layers:
1. **Pre-deploy safety dump** — `deploy.sh` runs `pg_dump` before every
   rollout (`deploy/backups/`).
2. **Application DR system** (`apps/backups`, Phase 4): scheduled
   daily/weekly/monthly tenant backups with retention
   (`BACKUP_RETENTION_DAILY=7 / WEEKLY=4 / MONTHLY=12`), Fernet-encrypted at
   rest, restore engine + admin API/CLI, missed-backup monitor
   (`BACKUP_MAX_AGE_HOURS`, alerts to `DR_ALERT_EMAILS`), maintenance /
   emergency modes gating writes during restores.
3. **Volumes/object storage** — snapshot `postgres_data` + `media_data`
   (or rely on S3 versioning when `STORAGE_BACKEND=s3`).

**RPO ≤ 24h** (daily backups; pre-deploy dumps shrink it around releases).
**RTO ≈ 30–60 min** single host (runbook below). Restores: DB
(`psql < dump` or the app restore engine per workspace), media (volume
snapshot / S3), full workspace (apps/backups restore = data + settings +
website content + branding).

## Performance

Budgets: tenant resolution <10ms (Redis, warm <2ms), cached API p50 ~20ms
(observability memo), login <300ms, public site LCP-optimized (SSR + ISR 60s
+ lazy images + gzip/brotli at the edge; CDN-ready — static assets are
hashed/immutable via WhiteNoise + Next, media offloadable to S3+CDN via
`S3_PUBLIC_DOMAIN`). Run `frontend/lighthouserc.js` + k6 load tests
(`frontend/e2e`, Phase 7) against staging before releases.

## Runbooks

| Task | Steps |
| --- | --- |
| Deploy | push tag / run deploy workflow — or SSH: `deploy/deploy.sh <backend> <client> <admin>` |
| Rollback | automatic on failed health; manual: `deploy/rollback.sh` |
| Restore DB | `gunzip -c deploy/backups/<ts>.sql.gz \| docker compose exec -T postgres psql -U hostel hostel` |
| Restore one workspace | admin → Backups → restore (or `manage.py restore_backup`) — maintenance mode auto-gates writes |
| Issue wildcard cert | `deploy/certbot/init-letsencrypt.sh` (dns-01); renewals via `renew.sh` cron + deploy-hook reload |
| Add customer domain cert | certbot http-01 for the domain, reload nginx — or run the Traefik overlay (automatic) |
| Scale out | set `STORAGE_BACKEND=s3` (media off-host) → `docker compose … up -d --scale web=3` |
| Rotate secrets | edit `deploy/.env` → `docker compose … up -d` (recreates); SECRET_KEY rotation invalidates JWTs (users re-login) |
| Investigate an incident | `X-Request-ID` from the client → grep structured logs → audit trail per workspace → Sentry event |
| Suspend abusive tenant | Settings → Danger Zone, or `manage.py shell`: `services.suspend_workspace(h)` — takes effect immediately (cache invalidated) |

## Compliance preparation

Data export (per-workspace settings export + apps/exports + backup files),
deletion workflow (soft-delete → support-driven purge), retention policies
(backups + `ANALYTICS_RETENTION_DAYS` prune), immutable audits, tenant
isolation by construction. Legal workflows (GDPR requests UI) are
intentionally not implemented; the architecture supports them.

## Environment matrix

| | Dev | Test | Staging | Production |
| --- | --- | --- | --- | --- |
| Config | `.env` + compose override | `config/settings_test.py` | `deploy/.env` (staging values) | `deploy/.env` |
| DEBUG | True | forced True (fast paths) | False | False |
| DB | host Postgres | in-memory SQLite | compose Postgres | compose/managed Postgres |
| Media | volume | tmp dir | volume or S3 | S3 recommended |
| TLS | none / dev overlay | — | LE staging certs | LE wildcard + per-domain |
| Images | built locally | — | `staging-<sha>` | release tag |
