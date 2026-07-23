# Enterprise DevOps Audit — Hostel SaaS

Roadmap Prompt 10. A full review of the repository and CI/CD configuration with
severities, concrete fixes, and a target architecture. Status reflects the
pipeline delivered across Prompts 01–09.

Severity: **P1** ship-blocker / reliability or security risk · **P2** important ·
**P3** hardening / nice-to-have.

---

## 1. Executive summary

The application is unusually mature for its stage: health endpoints, a disaster-
recovery/backup subsystem, strict security headers + CSP, fail-fast production
settings, and a broad automated test suite (pytest 80% gate + Playwright/Cypress/
Lighthouse/k6/ZAP). The CI/CD layer now matches that maturity — blocking lint,
test reporting, production-config validation, full-stack boot checks, layered
security scanning, registry-based deploys with auto-rollback, observability, and
branch protection.

The remaining risk is concentrated in **infrastructure topology** (single VPS =
single point of failure) and **dependency reproducibility** (unpinned Python
requirements). Both are called out below as P1.

---

## 2. Architecture

### Current (delivered)

```
 PR / push
   │
   ├─ ci.yml ................ lint (ruff/eslint/tsc) · pytest+cov+JUnit · vitest · docker build
   ├─ production-validation . hadolint · compose config · check --deploy · full stack boot+health
   ├─ security.yml .......... gitleaks · CodeQL · bandit · pip-audit · npm audit · Trivy(fs+img) · SBOM · dep-review
   ├─ e2e.yml ............... Playwright · Cypress · Lighthouse · k6 · ZAP
   └─ commit-lint.yml ....... Conventional Commits
        │
   develop ──▶ deploy-staging.yml ──▶ build→GHCR ──SSH──▶ Staging VPS (deploy.sh: backup→migrate→swap→verify)
        │
   tag v* ───▶ deploy-production.yml ─(manual approval)─▶ Production VPS (+ auto-rollback)
                                                              │
                                              monitoring/ (Prometheus·Grafana·Alertmanager·exporters)
```

### Target (recommended evolution)

- **Managed Postgres** (or a replicated pair) off the app host; automated PITR.
- **Two app hosts** behind a load balancer (or a second `web` replica + Nginx
  upstream) for true zero-downtime and host redundancy.
- **Object storage** for media + offsite encrypted backups (the DR subsystem
  already produces them — verify the destination is off-host).
- **Central logs + tracing** (Loki/ELK + OpenTelemetry) feeding the same Grafana.

---

## 3. Findings

### Reliability & infrastructure

- **P1 — Single VPS is a SPOF.** App, Celery, Postgres, and Redis share one host;
  loss of the host loses the database. *Fix:* move Postgres to a managed/replicated
  service or, at minimum, guarantee **off-host** encrypted backups + a documented
  restore drill (RTO/RPO). The `apps/backups` DR engine exists — confirm its
  storage target is not the same disk.
- **P1 — Unpinned Python dependencies** (`backend/requirements.txt` lists bare
  package names). Builds are non-reproducible and `pip-audit`/SBOM can't map to
  exact versions. *Fix:* compile a lockfile (`uv pip compile` or `pip-tools`) and
  install from it in Docker + CI; keep the top-level list as the input.
- **P2 — Deploy is near-zero-downtime, not zero.** Health-gated swap still has a
  brief cutover. *Fix:* second `web` replica + Nginx upstream, recreate one at a
  time. (Documented in `deploy/README.md`.)
- **P2 — Deploy workflows need secrets/environments wired.** They are correct
  templates; production gating depends on configuring the `production`
  Environment (required reviewers + `v*` branch policy).

### Security

- **Good:** fail-fast prod settings, HSTS/secure cookies/CSP, django-axes,
  throttling, gitleaks+CodeQL+Trivy+bandit+dep-review now blocking on CRITICAL.
- **P2 — Base images pinned by tag, not digest** (`python:3.13-slim`,
  `node:22-alpine`). *Fix:* pin by `@sha256:…` and let Dependabot/Renovate bump
  them; Trivy already scans the result.
- **P2 — No automated dependency-update bot.** *Fix:* add Dependabot/Renovate for
  pip, npm, Docker, and GitHub Actions (also pins action SHAs).
- **P3 — Pin third-party Actions to commit SHAs** (supply-chain). Currently on
  tags (`@v4`). Acceptable, but SHA-pinning is the hardened posture.
- **P3 — `/metrics` auth.** Handled by network isolation + Nginx 404; if ever
  proxied, add bearer/basic auth.

### Docker

- **Good:** multi-stage, non-root, slim runtime, healthchecks on every service,
  `.dockerignore` assumed, hadolint now gates Dockerfiles.
- **P3 — `collectstatic` runs at build with `DEBUG=True`.** Harmless (no secrets,
  no DB) and documented, but worth a comment-level review if settings grow
  import-time side effects.

### Testing

- **P2 — Frontend unit coverage is thin** (2 vitest suites vs. a large app). E2E
  covers journeys, but component/logic coverage is low. *Fix:* add a frontend
  coverage threshold once meaningful suites exist.
- **P3 — Coverage gate is Track A only** (by design; Track B is being retired).
  Re-scope `.coveragerc` when Track B is removed.
- **P3 — Add a migration linter** (`django-migration-linter`) to CI to catch
  backward-incompatible migrations before they reach a deploy.

### CI/CD & performance

- **P2 — Duplicate image builds across workflows.** `production-validation`
  (stack boot) and `security` (image scan) both build images on every push, in
  addition to `ci` build. *Fix:* gate the heavy stack-boot + image-scan jobs to
  `pull_request` + `main`/`develop` (path filters), or build once and share via a
  registry/artifact. GHA layer cache is already scoped per service to soften this.
- **P3 — Path filters.** Skip backend jobs on docs-only/frontend-only changes and
  vice-versa to cut runner minutes.
- **Good:** least-privilege `permissions`, concurrency cancellation, reusable
  composite actions, JUnit/coverage/build summaries, matrix builds.

### Observability

- **P2 — No log aggregation or tracing yet.** Metrics + Sentry are wired; logs are
  per-container. *Fix:* ship logs to Loki/ELK; add OpenTelemetry traces for slow
  request analysis.
- **Good:** Prometheus/Grafana/Alertmanager + exporters, health-probe alerts,
  starter dashboard, post-deploy health verification gates the deploy.

---

## 4. Prioritized action list

| # | Action | Severity | Effort |
| --- | --- | --- | --- |
| 1 | Off-host/managed Postgres + verified offsite backups & restore drill | P1 | M |
| 2 | Lock Python deps (uv/pip-tools); install from lockfile in Docker+CI | P1 | S |
| 3 | Configure `staging`/`production` Environments + deploy secrets | P2 | S |
| 4 | Dependabot/Renovate (pip, npm, docker, actions) | P2 | S |
| 5 | Pin Docker base images + Actions by digest/SHA | P2/P3 | S |
| 6 | Gate heavy stack-boot/image-scan jobs with path/event filters | P2 | S |
| 7 | Second `web` replica + Nginx upstream for zero-downtime | P2 | M |
| 8 | Log aggregation (Loki) + OpenTelemetry tracing | P2 | M |
| 9 | Frontend coverage threshold; `django-migration-linter` in CI | P3 | S |
| 10 | One-shot repo-wide `ruff format`, then flip CI format check to blocking | P3 | S |

---

## 5. What was delivered (Prompts 01–09)

- **01** `ci.yml` hardened — blocking ruff, JUnit + coverage + build summaries,
  least-priv perms, matrix builds, composite actions.
- **02/05** `production-validation.yml` — Dockerfile lint, compose validation,
  `check --deploy`, full prod-shaped stack boot with health/volume/network checks.
- **03** Test reporting (dorny + coverage summary) on top of the existing 80% gate
  and `e2e.yml` suite.
- **04** `security.yml` — gitleaks, CodeQL, bandit, pip-audit, npm audit, Trivy
  fs+image with CRITICAL blocking, CycloneDX SBOM, dependency review, licenses.
- **06/07** `build-images.yml` + `deploy-staging.yml` + `deploy-production.yml`
  with `deploy.sh`/`rollback.sh`, prod compose, Nginx — backup, migrate, health-
  gated swap, auto-rollback, deployment history.
- **08** `monitoring/` — Prometheus/Grafana/Alertmanager/exporters, `/metrics` via
  django-prometheus, alerts, dashboard.
- **09** Branch protection script, CODEOWNERS, PR template, Conventional-Commits
  lint, GitFlow docs.

See `.github/CICD.md` for the workflow map and `docs/GIT_WORKFLOW.md` for branch
strategy.
