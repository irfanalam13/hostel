# CI/CD Pipeline

Enterprise-grade GitHub Actions pipeline for the Hostel SaaS (Django + Next.js +
Postgres + Redis + Celery + Docker). This document maps the roadmap prompts to
the workflows that implement them and records the engineering decisions behind
them.

## Workflows

| Workflow | File | Roadmap | Blocks merge on |
| --- | --- | --- | --- |
| **CI** | `.github/workflows/ci.yml` | 01, 03 | ruff lint, ESLint, `tsc`, pytest (≥80% cov), vitest, both Docker builds |
| **Production Validation** | `.github/workflows/production-validation.yml` | 02, 05 | hadolint, `compose config`, `check --deploy` (security), full stack boot + health |
| **Security** | `.github/workflows/security.yml` | 04 | gitleaks, CodeQL, bandit (high/high), pip-audit, npm audit, Trivy CRITICAL, dependency-review |
| **E2E & QA** | `.github/workflows/e2e.yml` | (Phase 7) | Playwright, Cypress, Lighthouse; k6 + ZAP advisory |
| **Commit lint** | `.github/workflows/commit-lint.yml` | 09 | Conventional Commits (PR commits + title) |
| **Build images** | `.github/workflows/build-images.yml` | 06, 07 | reusable — build + push backend/frontend to GHCR |
| **Deploy — Staging** | `.github/workflows/deploy-staging.yml` | 06 | auto on `develop`: build → SSH rollout → smoke |
| **Deploy — Production** | `.github/workflows/deploy-production.yml` | 07 | on `v*` tag, manual approval: backup → migrate → swap → auto-rollback |

Deploy infra: `deploy/` (prod compose, Nginx, `deploy.sh`/`rollback.sh`).
Observability: `monitoring/` (Prometheus/Grafana/Alertmanager/exporters).
Git workflow + branch protection: `docs/GIT_WORKFLOW.md`,
`scripts/setup-branch-protection.sh`. Full review: `docs/DEVOPS_AUDIT.md`.

Shared setup lives in reusable composite actions:
`.github/actions/setup-backend` and `.github/actions/setup-frontend`.

## Key decisions

- **Least privilege.** Every workflow defaults to `permissions: contents: read`;
  jobs escalate only what they need (`checks: write` for test reports,
  `security-events: write` for SARIF/CodeQL, `pull-requests: write` for the
  dependency-review comment).
- **No `|| true`.** Lint is now blocking. Backend linting is consolidated on
  **ruff** (replacing flake8 + black); the rule set is pinned in
  `backend/pyproject.toml [tool.ruff.lint]` so a ruff upgrade can't silently
  change the gate. The 51 pre-existing violations were fixed when the gate
  was enabled.
- **Deploy check scoped to `security`.** `manage.py check --deploy --tag security
  --fail-level WARNING` blocks on real deployment-security issues (DEBUG, hosts,
  secure cookies, HSTS, SSL redirect, secret key) without tripping on unrelated
  drf-spectacular schema warnings. `settings.py` itself raises on a missing
  SECRET_KEY / ALLOWED_HOSTS / CORS in production, so misconfig fails fast.
- **Stack boot relaxes only SSL redirect.** `production-validation.yml` boots the
  whole stack with `DEBUG=False`; the single relaxation is
  `SECURE_SSL_REDIRECT=False`, because there is no TLS terminator in front of the
  CI stack and HTTPS-only would 301 every plaintext health probe. The HTTPS-on
  posture is asserted separately by the `django-deploy-checks` job.
- **CRITICAL CVEs stop the build.** Trivy (filesystem + both images) fails on
  CRITICAL; SARIF uploads to the Security tab; a CycloneDX SBOM is archived per
  image for 90 days.

## Follow-ups (remaining — see docs/DEVOPS_AUDIT.md for the full list)

These are deliberate, post-implementation hardening items, not gaps in the
pipeline as built:

1. **Pin `backend/requirements.txt`** (P1). Dependencies are unpinned, weakening
   reproducibility and CVE attribution. Move to a lockfile (`uv pip compile` /
   pip-tools) installed in Docker + CI.
2. **`ruff format` adoption** (P3). A repo-wide format touches ~223/316 files, so
   the CI format check is advisory (`continue-on-error`). Do it in one dedicated
   commit, then flip the step to blocking.
3. **Wire deploy secrets + Environments** (P2). `deploy-staging`/`deploy-production`
   are complete but need the `staging`/`production` GitHub Environments (manual
   approval, `v*` branch policy) and SSH/GHCR secrets configured.
4. **Infra topology** (P1). Single VPS is a SPOF — move Postgres off-host /
   managed with verified offsite backups; add a second `web` replica for true
   zero-downtime.

Implemented in this roadmap: Prompts **01–09** plus the **Prompt 10** audit
(`docs/DEVOPS_AUDIT.md`). Deploy = single Ubuntu VPS via `docker compose` over
SSH; monitoring = Prometheus + Grafana stack.
