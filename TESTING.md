# Testing & QA strategy (Phase 7)

This project is verified at every layer of the test pyramid. Each tool owns the
thing it's best at — no redundant coverage — and CI gates on the deterministic
suites while treating environment-dependent ones (load, DAST) as advisory.

```
            ╱╲      Lighthouse CI ........ perf / a11y / PWA budgets
           ╱  ╲     k6 ................... load / stress / spike / soak
          ╱ E2E╲    Playwright ........... auth · SW · offline · push · sync · visual
         ╱──────╲   Cypress .............. user-journey + component (2nd signal)
        ╱  Integ ╲  pytest (DRF APIClient) full multi-step API flows
       ╱──────────╲ ZAP baseline ......... passive DAST
      ╱    Unit    ╲ vitest (frontend) · pytest (backend)  + gitleaks/pip-audit/npm-audit
     ╱──────────────╲
```

## Coverage map (the Phase 7 checklist)

| Requirement            | Where                                                            | Tool            |
|------------------------|-----------------------------------------------------------------|-----------------|
| **Playwright**         | `frontend/e2e/*.spec.ts`                                         | Playwright      |
| **Cypress**            | `frontend/cypress/e2e/*.cy.ts`, `cypress/component/*.cy.tsx`     | Cypress         |
| **Lighthouse CI**      | `frontend/lighthouserc.js`                                       | @lhci/cli       |
| **Offline tests**      | `frontend/e2e/offline.spec.ts`                                   | Playwright+CDP  |
| **Service Worker**     | `frontend/e2e/service-worker.spec.ts`                            | Playwright      |
| **Push notifications** | `frontend/e2e/push.spec.ts`                                      | Playwright (SW worker.evaluate) |
| **Sync tests**         | `frontend/e2e/sync.spec.ts`                                      | Playwright      |
| **Authentication**     | `frontend/e2e/auth.spec.ts`, `cypress/e2e/auth.cy.ts`, backend `test_security_regression.py` | Playwright/Cypress/pytest |
| **Load tests**         | `tests/load/*.js`                                                | k6              |
| **Security tests**     | `tests/security/`, `backend/.../test_security_regression.py`, `test_tenant_isolation.py`, CI `security` job | ZAP + pytest + gitleaks/audit |
| **Regression tests**   | `frontend/e2e/regression.spec.ts` (visual), `smoke.spec.ts`, backend coverage gate | Playwright + pytest |

## Running locally

### Frontend unit (vitest)
```bash
cd frontend && npm test            # or: npm run test:coverage
```

### Playwright E2E (auth, SW, offline, push, sync, visual, smoke)
```bash
cd frontend
npm run e2e:install                # one-time: download browsers
npm run e2e                        # headless, builds + starts the app itself
npm run e2e:ui                     # interactive
npm run e2e:update-snapshots       # after an intentional UI change
```
PWA specs (`@chromium-only`) need Chromium for the Background Sync API; they're
skipped on Firefox/WebKit automatically.

### Cypress
```bash
cd frontend
npm run build && npm run cy:ci     # headless E2E (start-server-and-test)
npm run cy:open                    # interactive
npm run cy:component               # component tests
```

### Lighthouse
```bash
cd frontend && npm run build && npm run lhci
```

### Backend (pytest — unit, integration, security, RBAC, tenant isolation)
```bash
cd backend && pytest               # 80% coverage gate on the canonical Track A
cd backend && pytest apps/common/tests/   # just the security/isolation suite
```

### Load (k6) — never against production
```bash
SCENARIO=load BASE_URL=https://staging k6 run tests/load/dashboard-read.js
```
See [`tests/load/README.md`](tests/load/README.md).

### Security DAST (ZAP)
See [`tests/security/README.md`](tests/security/README.md).

## CI

- **`.github/workflows/ci.yml`** — lint, unit/integration (pytest 80% gate +
  vitest), Docker builds, migration validation, SAST/dependency scanning.
- **`.github/workflows/e2e.yml`** — Playwright, Cypress, Lighthouse (blocking,
  hermetic), plus load smoke + ZAP baseline (advisory, `continue-on-error`).

## Design decisions

- **Hermetic browser tests.** The Django API is mocked at the network layer
  (`frontend/e2e/support/mock-api.ts`, Cypress `cy.intercept`) so E2E is fast and
  deterministic in CI without Postgres/Redis/Celery. A `PW_LIVE=1` Playwright
  project runs the same specs against a real backend for pre-release smoke.
- **Playwright vs Cypress.** Playwright owns the PWA-heavy flows (it can run code
  inside the service worker and toggle the network via CDP); Cypress provides a
  fast component harness and a second, independent E2E signal on the core
  journeys. They don't duplicate the PWA suite.
- **Push without a push service.** Real FCM isn't deterministic in CI, so the SW
  `push`/`notificationclick` handlers are driven directly via `worker.evaluate`,
  and the subscription flow is asserted with a stubbed `pushManager`.
