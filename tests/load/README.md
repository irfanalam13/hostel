# Load tests (k6)

Performance/throughput tests for the Django API, written for [k6](https://k6.io).
They live outside the app so they can run from a load generator against any
environment.

> ⚠️ **Never run these against production.** `payment-write.js` mutates data.
> Point `BASE_URL` at a local or disposable staging/perf environment.

## Install

```bash
# macOS:  brew install k6     Windows:  winget install k6
# Linux/CI: see https://grafana.com/docs/k6/latest/set-up/install-k6/
```

## Run

```bash
# Smoke (default): 1 VU / 30s — just proves the script + target work.
k6 run tests/load/auth-login.js

# Expected production traffic:
SCENARIO=load BASE_URL=https://staging.example.com k6 run tests/load/dashboard-read.js

# Find the breaking point:
SCENARIO=stress k6 run tests/load/dashboard-read.js

# Sudden surge:
SCENARIO=spike k6 run tests/load/auth-login.js

# Soak (leaks / connection exhaustion):
SCENARIO=soak k6 run tests/load/dashboard-read.js
```

### Env vars

| Var        | Default                 | Meaning                          |
|------------|-------------------------|----------------------------------|
| `BASE_URL` | `http://localhost:8000` | API origin (no trailing `/api`)  |
| `SCENARIO` | `smoke`                 | `smoke\|load\|stress\|spike\|soak` |
| `HOSTEL_ID`| `HTL-ABC12345`          | Tenant code used at login        |
| `USERNAME` / `PASSWORD` | `warden` / `TestPass!234` | Load-test account |

## SLOs (thresholds)

Defined in `lib/config.js` — a run exits non-zero if breached, so CI can gate:

- `http_req_failed` &lt; 1%
- reads: p95 &lt; 800 ms, p99 &lt; 2 s
- writes: p95 &lt; 1.2 s, p99 &lt; 3 s
- login: p95 &lt; 1.5 s (password hashing is intentionally slow)

## Scripts

| Script              | Path under test                         | What it stresses                |
|---------------------|-----------------------------------------|---------------------------------|
| `auth-login.js`     | `/auth/login/`                          | password hashing + JWT issuance |
| `dashboard-read.js` | dashboard summary + list endpoints      | N+1 / missing indexes (H6/H7)   |
| `payment-write.js`  | `/payments/` (+ Idempotency-Key)        | ledger locking + idempotency    |
