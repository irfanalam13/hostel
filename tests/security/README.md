# Security tests

Security verification runs at three layers; together they cover the findings in
`AUDIT.md`.

## 1. SAST + dependency scanning (CI, already wired)

The `security` job in `.github/workflows/ci.yml`:

- **gitleaks** — committed-secret scanning
- **pip-audit** — Python dependency CVEs
- **npm audit** (`--audit-level=high`) — Node dependency CVEs

## 2. Application security regression tests (pytest)

`backend/apps/common/tests/test_security_regression.py` and
`test_tenant_isolation.py` lock in the remediated findings:

| Area                 | Guards                                             |
|----------------------|----------------------------------------------------|
| Multi-tenant isolation | spoofed `X-Hostel-Code`, membership, queryset leaks |
| Payment integrity (C4) | negative/zero amounts rejected                     |
| Authentication       | protected endpoints require auth; bad creds fail   |
| Security headers (M13) | `X-Content-Type-Options: nosniff` always on        |
| Rate limiting (H11/M5) | auth/signup/password-reset throttle scopes wired   |
| Input handling       | hostile query strings degrade to 4xx, never 500    |

Run: `cd backend && pytest apps/common/tests/`

## 3. DAST — OWASP ZAP baseline (CI, against a running app)

A passive baseline scan crawls the running SPA and reports XSS/SQLi/CSRF/header
issues. Rules live in [`zap-baseline.conf`](./zap-baseline.conf) — high-signal
rules `FAIL` the build, known false positives are `IGNORE`d.

Locally (Docker):

```bash
docker run --rm -v "$(pwd)/tests/security:/zap/wrk:rw" \
  --network host ghcr.io/zaproxy/zaproxy:stable \
  zap-baseline.py -t http://localhost:3000 \
  -c zap-baseline.conf -r zap-report.html
```

In CI it runs in the `e2e.yml` workflow (`security-dast` job) against the built
frontend + a live backend.

## What is intentionally NOT here

- **Active/attack scans & pentesting** — destructive; run manually against a
  disposable environment with authorization, not in CI.
- **Auth-token leakage in the SW** — covered by the Playwright service-worker
  spec (`does NOT cache cross-origin API responses`).
