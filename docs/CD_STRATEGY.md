# Continuous Delivery Strategy — Hostel SaaS

**Status:** Decision of record (Phase 0). Supersedes the ambiguity between the
PaaS deploys and the VPS deploy workflows.
**Model:** **Continuous Delivery** — every change that passes CI is *always
releasable* and flows automatically to a preview/staging environment; promotion
to **production is a deliberate manual gate**, never automatic on merge.

> Why delivery, not deployment: production releases here affect live multi-tenant
> data (billing, RBAC, migrations). We keep the pipeline fully automated up to a
> human "promote" click so a person owns the go/no-go, while everything before it
> stays hands-off and fast.

---

## 1. Canonical platform (system of record)

Production runs on **managed PaaS**, git-driven. There is exactly one canonical
path:

| Component | Platform | Source | Notes |
| --- | --- | --- | --- |
| Client zone (`apps/client`) | **Vercel** project | `frontend/` | Next.js |
| Admin zone (`apps/admin`) | **Vercel** project | `frontend/` | Next.js |
| Django backend + Celery | **Render** (dashboard-managed) | `backend/` | web + worker services |
| AI service (`ML_hostel`) | **Render** | `ML_hostel/render.yaml` | Docker, `/health/` probe |
| Postgres · Redis | **Render** managed add-ons | — | off-host from app containers |

The GitHub Actions under `.github/workflows/deploy-*.yml` (SSH → VPS via
`deploy.sh`/`rollback.sh`) are the **self-host alternative**. They are complete
and correct but **INACTIVE**: no environment secrets are wired and they are not
part of the production path. Keep them as a documented fallback / portability
option — do **not** treat a red or unconfigured VPS deploy job as production
signal. (See `docs/DEVOPS_AUDIT.md` §2.)

---

## 2. Pipeline (merge → release)

```
 PR ──▶ CI gates (ci.yml · security.yml · e2e.yml · production-validation.yml)
        must be green to merge  ─────────────────────────────────────────────┐
                                                                              │
 merge to  main  ──▶ AUTOMATIC preview/staging deploy                         │
   • Vercel: Preview deployment per commit (both zones)                       │
   • Render: hostel-ml auto-deploys (autoDeploy: true) — staging-grade        │
        │                                                                     │
        │  smoke check: /health/, /health/database/, /health/cache/,          │
        │               /health/celery/  all 200                              │
        ▼                                                                     │
 ┌─────────────────── MANUAL PRODUCTION PROMOTION GATE ───────────────────┐   │
 │  A human promotes the verified build to production:                    │◀──┘
 │   • Vercel:  "Promote to Production" on the passing preview (per zone)  │
 │   • Render:  "Manual Deploy → Deploy latest commit" on prod services    │
 │              (set backend autoDeploy = OFF so main never auto-releases) │
 └────────────────────────────────────────────────────────────────────────┘
        │
        ▼
 post-promote verification: hit the four /health/ endpoints on prod → 200
```

### The gate, concretely
- **Turn OFF auto-deploy to production** on the Render backend service and set
  `autoDeploy: false` for `hostel-ml` in `ML_hostel/render.yaml` (currently
  `true`). Auto-deploy is fine for a *staging* service, not the prod one.
- **Vercel**: keep Preview deployments automatic; production is reached only via
  **Promote to Production**. (Do not set `main` as the auto-production branch.)
- One promotion = all surfaces together (client, admin, backend, AI) so tenants
  never see a half-released version.

---

## 3. Rollback

Fast, platform-native — no custom scripts on the canonical path:

- **Vercel:** *Instant Rollback* — re-promote the previous production deployment
  (both zones). Seconds, no rebuild.
- **Render:** *Rollback* to the previous deploy from the service's Deploys tab.
- **Database migrations:** forward-only by policy. A release that needs a schema
  change ships the migration in the same promotion; roll back code only if the
  migration is backward-compatible (it should be — see `docs/GIT_WORKFLOW.md`).
  Irreversible migrations require a maintenance window, not a rollback.

The VPS `deploy.sh` already does backup→migrate→health-gated swap→auto-rollback;
that logic only applies if/when the self-host path is activated.

---

## 4. Release checklist (manual gate)

Before clicking promote:

1. CI is green on the merge commit (all four workflows).
2. Preview/staging smoke passed: the four `/health/` endpoints return 200.
3. Migration plan reviewed (`python manage.py migrate --plan`) if models changed.
4. Secrets present on both Render services (esp. `ML_SHARED_SECRET` identical on
   backend and `hostel-ml`; provider API keys set, not in git).
5. Promote all surfaces, then re-run the four `/health/` checks against prod.
6. Watch Grafana/Alertmanager for the first ~15 min (error rate, latency).

---

## 5. Roadmap hooks (later phases)

This doc closes the Phase 0 **CD decision**. Later phases build on it:
- **Phase 3 (CD → 95%):** metric-based auto-rollback (Prometheus error-budget
  breach), progressive/canary promotion, feature-flag-gated releases via
  `apps/platformops`.
- **Phase 1 (§9 secrets):** move the `sync: false` Render secrets into a managed
  secret store with rotation. Note: a Gemini key was previously shared in chat —
  rotate it (already flagged in `ML_hostel/render.yaml`).

---

_Related: `.github/CICD.md` (workflow map) · `docs/DEVOPS_AUDIT.md` (findings) ·
`docs/GIT_WORKFLOW.md` (branch strategy) · `ML_hostel/DEPLOY_RENDER.md`._
