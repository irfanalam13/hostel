# Enterprise API Performance & Request-Pipeline Audit — Report

**Date:** 2026-07-10  **Branch:** `feature/dockerize-dev-stack`
**Target:** every API route < 100 ms; no pending/looping/hanging requests; full
request lifecycle observable browser → DB → back.

> Method: never guessed. Every number below comes from the in-process
> full-middleware benchmark (`manage.py benchmark_api`), `Server-Timing`
> response headers, the per-request structured log, and Django's query capture.

---

## 1. Executive summary

The request pipeline was already substantially hardened in prior work
(per-request tenant/membership/DR caches, async audit writes, request-timing
middleware, an `AbortController`-bounded + single-flight-refresh + GET-dedupe
frontend `apiClient`). This audit **measured every endpoint** and found the
pipeline already meeting the budget on all but one route — plus one N+1-adjacent
count cluster.

**One critical bottleneck was found and fixed:** `GET /api/dashboard/system-status/`
took **~1030 ms** because it pinged Celery workers **synchronously** on every
request. It now returns in **~20–30 ms** (a **~40× improvement**) and no request
ever blocks on Celery again.

After the fix, **every measured endpoint is < 35 ms median** — comfortably under
the 100 ms target and far under the audit's 200 ms avg / 500 ms P95 criteria.

---

## 2. Complete request lifecycle (as instrumented)

```
Browser
  │  apiClient.ts: AbortController timeout (20s), single-flight token refresh,
  │  in-flight GET dedupe, X-Request-ID minted + sent
  ▼
CORS ─► RequestTimingMiddleware ─► Security/GZip/WhiteNoise ─► Session/CSRF/Auth
  │        (mints/echoes X-Request-ID; wraps DB with execute_wrapper;
  │         emits Server-Timing: db;dur=…, app;dur=…, total;dur=…)
  ▼
DRModeMiddleware ─► TenantResolutionMiddleware ─► AuditLogMiddleware
  │  (DR state cached 30s; tenant cached 300s; membership cached 60s)
  ▼
IdempotencyMiddleware ─► AxesMiddleware
  ▼
DRF View  ─► CookieJWTAuthentication (cached tenant lookup)
          ─► Permissions (per-request memo + Redis membership cache)
          ─► Serializer (relations eager-loaded)
          ─► PostgreSQL (CONN_MAX_AGE reuse, statement_timeout guard)
  ▼
StandardJSONRenderer ─► GZip ─► Server-Timing + X-Request-ID on response
  ▼
Browser: apiClient resolves; structured log line written server-side
```

Each stage answers the audit's 18 "did it block?" questions: the per-request log
(`apps.requests`) records `duration_ms`, `db_ms`, `db_queries`, `status`, `user`,
`hostel`, `bytes`, `request_id`; `Server-Timing` splits app vs DB in the browser
Network panel; anything ≥ `SLOW_REQUEST_MS` (300) is logged at WARNING.

---

## 3. Measured results (before → after)

Full middleware stack, 50 residents / 150 dues / 50 payments, warm, median of 9:

| Endpoint | queries | median (before) | median (after) |
|---|---|---|---|
| `/api/dashboard/system-status/` | 9–10 | **1032 ms** | **20–33 ms** |
| `/api/dashboard/owner/` | 13 → 11 | 49 ms | 22 ms |
| `/api/residents/` | 4 | 24 ms | 15 ms |
| `/api/billing/dues/` | 3 | 24 ms | 16 ms |
| `/api/billing/payments/` | 3 | 25 ms | 17 ms |
| `/api/hostel/rooms/` | 4 | 23 ms | 15 ms |
| `/api/hostel/beds/` | 3 | 16 ms | 13 ms |
| `/api/residents/stays/` | 2 | 13 ms | 9 ms |
| `/api/auth/me/` | 1 | 6 ms | 8 ms |
| `/api/notices/`, `/attendance/`, `/complaints/`, `/notifications/`, `/audit/` | 1–2 | 5–13 ms | 5–12 ms |

**Query offenders (>12): none. Slow (>100 ms median): none.**

---

## 4. Root-cause findings & fixes

### 🔴 Critical — synchronous Celery ping on the dashboard hot path
**Where:** `apps/dashboard/system_views.py::_health()` (called by `SystemStatusView.get`).
**Evidence:** `Server-Timing` showed `db;dur≈15ms, total;dur≈1030ms` — ~1 s of
non-DB time. `_health()` ran `celery_app.control.ping(timeout=1.0)`, a broadcast
over the broker that **blocks for its full timeout on every request**. This is
the Phase-10 anti-pattern ("the frontend must never wait for Celery").
**Fix:** stale-while-revalidate. `_health()` now serves a cached snapshot
instantly and refreshes it in a **daemon thread**; a cold cache returns an
optimistic `"checking"` snapshot and kicks the background probe. Probe timeouts
cut to 0.5 s. **No request path ever blocks on Celery/Redis.**
**Result:** ~1030 ms → ~20–33 ms.

### 🟡 Minor — 3 separate bed COUNT round-trips
**Where:** `apps/dashboard/views.py::OwnerDashboardView` (legacy Track B).
**Fix:** collapsed `total`/`occupied`/`available` into one conditional aggregate
(`Count(..., filter=Q(...))`). 13 → 11 queries; 49 ms → 22 ms.

### ✅ Verified already-optimized
- `ResidentViewSet` prefetches `bed_history` (the only serialized relation);
  `current_bed` is a raw FK id (no traversal). No N+1.
- Billing/rooms/notices/etc. serializers expose scalar fields or raw FK ids — no
  relation traversal on list endpoints. Query counts 1–4, all paginated.
- Auth is 1–2 queries (cached tenant + cached membership).

---

## 5–8. Subsystem analyses

- **Database:** PostgreSQL only; `CONN_MAX_AGE=600` + `CONN_HEALTH_CHECKS`;
  optional `statement_timeout`. Warm query counts 1–4 on list endpoints. No
  sequential-scan hot paths surfaced at this data size; no N+1 remaining.
- **Redis:** cache ops bounded by `socket_connect_timeout`/`socket_timeout`
  (1.5 s) and **degrade to DB** on failure — a Redis outage never 500s or hangs.
  Tenant (300 s), membership (60 s), DR-state (30 s), permissions (300 s) caches.
- **Authentication:** cookie JWT; access lifetime 15 min, refresh rotated +
  blacklisted; frontend refresh is **single-flight** (no refresh storm). Tenant
  read from cache, not a live DB hit.
- **Middleware:** timing middleware sits first so it brackets the whole stack;
  audit writes are enqueued to Celery (sync fallback) — off the response path.

---

## 9. Bottlenecks ranked by severity
1. **(Fixed)** Synchronous Celery ping — 1030 ms → 30 ms.
2. **(Fixed)** Bed count fan-out — 3 queries → 1.
3. None remaining above the 100 ms / 12-query budget.

---

## 10–13. Monitoring, logging, tracing (Phases 13/14/18)
- **Structured logs:** one line per request with request-id, route, method, user,
  duration, db time/queries, size, status (`apps.common.observability`).
- **Tracing:** `X-Request-ID` accepted from the browser or minted, echoed on the
  response and exposed via CORS; `Server-Timing` visible in DevTools.
- **Metrics (Prometheus):** `/metrics` is wired via `django-prometheus`
  (installed, 2.5.0), gated behind `PROMETHEUS_ENABLED` and restricted to the
  internal scraper at the proxy. Verified: `GET /metrics` → 200, 124 metric lines
  incl. `django_http_requests_latency_*` histograms and per-view/method counters.
- **Errors:** Sentry activates when `SENTRY_DSN` is set.

---

## 14. Validation — reproduce these numbers
```bash
# Full-stack per-endpoint benchmark + budget guard (fails CI on regression):
docker compose exec -T web python manage.py benchmark_api
docker compose exec -T web python manage.py benchmark_api --residents 200 --slo-ms 100 --max-queries 12

# Prometheus metrics:
PROMETHEUS_ENABLED=True  →  GET /metrics

# Per-request timing in the browser: DevTools ▸ Network ▸ any /api/ call ▸
# Timing / Response headers ▸ Server-Timing + X-Request-ID.
```
`benchmark_api` exits non-zero if any 200 endpoint exceeds the query budget
(default 12) or the latency SLO (default 100 ms median) — wire it into CI to keep
the budget from silently regressing.

---

## Success-criteria checklist
- [x] No request pending indefinitely (AbortController timeout + bounded Redis).
- [x] No infinite routing/rendering loops; single-flight refresh (no auth storm).
- [x] All API requests have measurable latency (Server-Timing + structured log).
- [x] Avg API response ≪ 200 ms; every measured route < 35 ms median (< 100 ms target).
- [x] No N+1 queries; no >12-query endpoints.
- [x] No middleware bottleneck (timing middleware brackets the stack).
- [x] Frontend never waits for Celery (audit async; health probe off hot path).
- [x] Every request has structured logs + trace id; lifecycle observable end-to-end.
