# Edge Security & Rate Limiting Foundation (Prompt 07)

Enterprise, horizontally scalable, security-first rate limiting and edge
protection for the Hostel SaaS platform. This layer is the **foundation** for
every current and future surface (auth, APIs, AI, finance, portals);
endpoint-specific limits (login, signup, OTP, …) build on the primitives
documented here in the next document.

---

## 1. Layered architecture

Every layer independently detects abuse and protects the next one. No single
limiter is relied on.

```
Internet
  ↓
Cloudflare edge (optional, config-gated)     WAF · bot management · DDoS ·
  ↓                                          managed challenge · IP/ASN/country
Nginx reverse proxy                          conn limits · req limits · Slowloris
  ↓                                          timeouts · scanner-UA/method blocks
Redis distributed limiter (Lua, atomic)      shared truth for N containers
  ↓
EdgeGuardMiddleware (apps.security)          trusted-proxy IP · IP rules ·
  ↓                                          reputation · bots · WAF-lite ·
TenantResolutionMiddleware                   per-IP burst + sustained limits
  ↓
TenantRateLimitMiddleware                    per-workspace, plan-aware limit
  ↓
DRF throttles (SecurityScopedThrottle)       per-endpoint / per-user (next doc)
  ↓
Business logic → PostgreSQL                  audit log · security events
```

Where things live:

| Layer | Location |
|---|---|
| App security foundation | `backend/apps/security/` |
| Nginx zones/maps | `deploy/nginx/templates/00-security.conf.template` |
| Nginx server hardening | `deploy/nginx/snippets/security.conf` |
| Cloudflare real-IP | `deploy/nginx/snippets/cloudflare-real-ip.conf` |
| Env knobs | `.env.example`, `deploy/.env.prod.example` |
| Live verification | `backend/scripts/verify_edge_security.py` |
| Load test | `deploy/load/k6-rate-limit.js` |

---

## 2. Threat model → mitigations

| Threat | Mitigation (layer) |
|---|---|
| L3/L4 DDoS, TCP flood | Cloudflare DDoS protection; nginx `limit_conn` per-IP/per-server |
| L7 HTTP flood | Cloudflare rate rules; nginx `limit_req` (auth/api/global zones); Redis per-IP sliding window + token-bucket burst |
| Slowloris / slow-read | nginx `client_header_timeout 10s`, `client_body_timeout 15s`, `send_timeout 15s`, bounded header buffers |
| Credential stuffing / brute force / password spraying | nginx `auth` zone (5r/m); django-axes lockout (existing); `reputation.penalize(ip, "auth_failure")` hook + per-endpoint throttles (next doc) |
| Broken authentication / replay | Existing JWT-cookie auth + rotation/blacklist; idempotency middleware (existing); this layer adds per-IP budgets in front |
| SQLi / XSS / RCE / LFI / traversal (OWASP Top 10 injection class) | Cloudflare WAF managed rules; app WAF-lite on path+query (`waf.py`), monitor→enforce rollout; DRF serializer validation (existing) |
| Enumeration / scanner probes | WAF `scanner_probes` rules (/.env, /wp-*, /.git, …); nginx scanner-UA map → 403; reputation penalties compound into blocks |
| Bots (Selenium/Puppeteer/Playwright/headless, curl/wget/requests, scrapers, AI bots) | Cloudflare Super Bot Fight Mode + managed challenge (JS/CAPTCHA); app UA classification with allow/log/block per category; good bots allow-listed |
| IP rotation / botnets / proxy & TOR / VPN abuse | Cloudflare IP-reputation + ASN/country rules (edge is the right place — see §6); app per-tenant limits cap aggregate damage regardless of source IPs |
| Spoofed X-Forwarded-For (limiter bypass) | Rightmost-untrusted algorithm in `ip.py`; XFF ignored unless the peer is a trusted proxy; CF-Connecting-IP honoured only from Cloudflare ranges |
| Host / origin spoofing | `ALLOWED_HOSTS` fail-fast (existing); tenant middleware host validation (existing); nginx `server_name` routing |
| SSRF / CSRF | CSRF middleware + trusted origins (existing); SSRF surface limited to domain-verification DNS probes (already throttled) |
| Malicious tenants / noisy neighbours | `TenantRateLimitMiddleware`: each workspace has an isolated, plan-scaled budget; tenant-scoped `IPRule`s |
| Resource exhaustion (API abuse, excessive consumption) | Layered budgets (IP burst → IP sustained → tenant → endpoint); `MemoryBackend` key cap; upload/body size limits (existing + nginx) |
| Redis outage as an attack vector | Circuit breaker + configurable fail-open (degrade to per-container limits) / fail-closed (503); app cache already degrades to DB |

---

## 3. Application layer (`apps.security`)

### 3.1 Configuration — nothing hardcoded, hot reload

Resolution chain (later wins), rebuilt automatically on change:

1. `defaults.py` `DEFAULTS` — code baseline
2. `ENVIRONMENT_DEFAULTS[SECURITY_ENVIRONMENT]` — development / testing /
   staging / production overlays (dev = monitor + generous, prod = enforce)
3. YAML file (`SECURITY_CONFIG_FILE`) — infra-managed policy (PyYAML)
4. `SECURITY_*` env vars (`conf._ENV_OVERRIDES`, documented in `.env.example`)
5. **DB `SecuritySetting` rows** — dotted key → JSON value, editable in the
   Django admin at runtime

Hot reload: any `SecuritySetting`/`IPRule` save bumps a Redis generation
counter; every container re-checks it (≤ `SECURITY_CONFIG_RECHECK_SECONDS`,
default 5s) and rebuilds its snapshot — **no restart, all containers, within
seconds**. Verified live in `verify_edge_security.py`.

Feature flags (all runtime-switchable): `enabled`, `waf.enabled`,
`bots.enabled`, `reputation.enabled`, `ip_rules.enabled`,
`cloudflare.enabled`, every `rate_limits.<scope>.enabled`, plus
`mode`/`waf.mode`/`bots.mode` (enforce ↔ monitor).

### 3.2 Rate-limiting algorithms — and why each

All three are single-key, single-round-trip **atomic Lua scripts** on Redis
(correct under any container count, Cluster-safe) with an equivalent
thread-safe in-memory implementation for degraded/dev/test:

| Algorithm | Semantics | Chosen for |
|---|---|---|
| **Sliding window log** (ZSET) | exactly N per rolling window, no boundary bursts | default for abuse-facing limits (per-IP, per-tenant) — precision matters more than the O(limit) memory |
| **Token bucket** | bursts up to `capacity`, sustained `refill_rate`/s, O(1) | burst smoothing in front of the sliding window (`ip_burst`) |
| **Leaky bucket (GCRA)** | constant-rate output + burst tolerance, O(1), queue-free | expensive downstreams needing a smooth stream (AI, exports — next doc) |

Rules are pure config: `{algorithm, limit, window_seconds | capacity,
refill_rate | burst}` under `rate_limits.<scope>`; `engine.check(scope,
identity, multiplier=…)` is the single enforcement entry point.

### 3.3 Client IP resolution (`ip.py`)

Rightmost-untrusted algorithm: the socket peer is authoritative unless it is
a **trusted proxy** (`trusted_proxies` CIDRs; private ranges by default for
the compose/K8s network). Only then is `X-Forwarded-For` walked right-to-left
past trusted hops. `CF-Connecting-IP` is honoured only when Cloudflare
support is on **and** the peer is trusted. Malformed/oversized chains are
flagged (`proxy_suspect` events). This is what makes every IP-keyed control
non-bypassable.

### 3.4 IP rules, reputation, bots, WAF

* **IPRule** (DB, admin-managed): `trust` (skip everything) / `allow` (skip
  limits, keep WAF) / `deny` (block, even in monitor mode) — global or
  per-tenant, permanent or auto-expiring. Precedence: trust > allow > deny.
* **Reputation** (Redis): violations add configurable penalty points; scores
  decay by TTL (automatic recovery); crossing `block_threshold` sets a
  temporary hard block. `penalize(ip, "auth_failure")` is the hook the auth
  document will feed.
* **Bot detection**: UA classification into allowed / blocked (attack tools)
  / suspicious (curl, headless, Playwright/Puppeteer/Selenium…) with per-
  category actions. Real fingerprinting + challenges are delegated to
  Cloudflare (§6) — the origin never runs CAPTCHAs.
* **WAF-lite**: method allow-list, path/query length caps, and six rule
  groups (traversal, SQLi, XSS, RCE, LFI, scanner probes) over the
  URL-decoded request line (double-decode aware). Bodies are deliberately not
  scanned (false-positive + latency cost; Cloudflare WAF covers that).
  Ship `monitor` → soak → flip `waf.mode` to `enforce` at runtime.

### 3.5 Events & audit

Every decision emits a structured JSON log line (`apps.security.events`
logger: request id, tenant, user, ip, ua, CF country/ASN, decision, threat
score) and an immutable `SecurityEvent` row (async via Celery, inline
fallback; admin is read-only; daily retention prune + expired-IPRule reaping
at 05:00). Flood-safe: repeated identical events are deduped for 60s — the
limiter absorbs volume, not the event table.

### 3.6 Distributed locks (`locks.py`)

`RedisLock`: SET NX PX + per-holder token, compare-and-set release/extend
(Lua), TTL deadlock-freedom, optional blocking acquire, fail-strategy-aware
degradation. For cross-container critical sections (reconciliation, future
billing jobs).

### 3.7 Fail strategy

`fail_strategy: open` (default) — Redis down ⇒ requests flow; limiting
degrades to per-container memory (documented under-counting) behind a 5s
circuit breaker. `closed` — rate-limited scopes reject with 503 + machine
code `fail_closed`. A system check warns when choosing `closed` without HA
Redis, and when running `monitor` in production.

---

## 4. Nginx edge layer

`00-security.conf.template` (http context, renders before `app.conf`):
per-IP `limit_req` zones **auth** (5r/m) / **api** (20r/s) / **global**
(100r/s), per-IP + per-server `limit_conn` zones, scanner-UA map, method
allow-list map. `snippets/security.conf` (server context): Slowloris
timeouts, keep-alive tuning, `server_tokens off`, header-buffer caps, and the
map enforcement (`403`/`405`). All rates/bursts/conn caps are env-tunable
(`NGINX_RATE_*`, `NGINX_BURST_*`, `NGINX_CONN_*` — defaults in
`deploy/docker-compose.prod.yml`, overridable in `deploy/.env`).

Validated: templates render via the image's envsubst and pass `nginx -t`
(only defined env vars are substituted, so `$binary_remote_addr` etc. pass
through untouched). The dev gateway is intentionally not rate-limited (HMR
websockets, local iteration); the app layer still runs there in monitor mode.

---

## 5. Multi-instance correctness & Kubernetes readiness

* Every limit decision is one atomic Lua call on shared Redis — correct for
  2, 5, 20 containers, Swarm, K8s, multi-VPS behind any LB. No app-local
  state participates in enforcement (memory backend is only the degraded
  mode, bounded at 50k keys).
* Redis topologies: `SECURITY_REDIS_MODE=standalone|sentinel|cluster`
  (Sentinel master discovery, Cluster single-key scripts), pooled
  connections, 1.5s socket bounds.
* K8s: config via env/ConfigMap (YAML file mounts cleanly), hot reload works
  across pods (shared generation counter), no local disk, existing
  `/health/` probes remain dependency-free and security-exempt, HPA-safe
  (stateless), rolling updates safe (config generation is monotonic).

---

## 6. Cloudflare deployment guide (config-gated, never hardcoded)

Enable when fronting with Cloudflare (orange cloud):

1. **Origin**: uncomment `include snippets/cloudflare-real-ip.conf` in
   `app.conf.template`; set `SECURITY_CLOUDFLARE_ENABLED=True`; firewall
   ports 80/443 to Cloudflare ranges only (origin protection / Zone
   Lockdown equivalent).
2. **WAF**: enable Managed Rules + OWASP Core Ruleset (paid) — the app WAF
   remains as defence-in-depth behind it.
3. **Bot management**: Bot Fight Mode / Super Bot Fight Mode; add a custom
   rule to *Managed Challenge* automated scores on `/api/auth/*`.
4. **Rate limiting rules** (edge): mirror the auth zone — e.g. 10 req/min on
   `/api/auth/login` per IP with Managed Challenge, then block.
5. **DDoS**: automatic (L3–L7); set Security Level ≥ Medium; enable Browser
   Integrity Check.
6. **IP/ASN/country**: use Cloudflare custom rules for country blocks, data
   center/VPN ASN challenges, threat-score challenges. The app's `IPRule` +
   `CF-IPCountry`/ASN enrichment in `SecurityEvent` give the audit trail.
7. **Analytics**: Firewall Events + Security Analytics complement
   `SecurityEvent` / the JSON security log.

The platform behaves identically with Cloudflare absent — every layer below
is independent.

---

## 7. High availability & disaster recovery

| Failure | Behaviour | Recovery |
|---|---|---|
| Redis down | Circuit breaker opens (5s retry); fail-open ⇒ per-container memory limits; fail-closed ⇒ 503 on limited scopes; `SecurityEvent` persistence falls back inline; caches already DB-degrade | Automatic on Redis return (breaker re-dials, snapshot resumes) |
| Redis restart (data loss) | Counters/reputation reset — window of leniency, never an outage | Self-heals as traffic refills windows |
| App container crash/restart | Stateless — limits live in Redis, config rebuilt from layers at boot | Compose/K8s restart policy |
| Nginx down | Compose `restart: unless-stopped`; multiple replicas supported (zones are per-instance — Redis layer stays global) | Automatic |
| Cloudflare outage | Grey-cloud DNS to origin; nginx + app layers keep protecting | Manual DNS flip |
| Bad security config pushed | `mode: monitor` flip via `SecuritySetting` (seconds, no deploy); system checks catch invalid values at boot | Runtime |

---

## 8. Testing

* **Unit/integration (hermetic, CI-safe)** — `backend/apps/security/tests/`
  (88 tests): algorithm semantics (window slide, refill, GCRA burst),
  spoof-resistance, config layering/coercion/hot-reload, IPRule precedence +
  tenant scoping + expiry, WAF true/false-positive matrix, bot categories,
  middleware enforce/monitor/429 envelope/headers/exemptions, tenant
  isolation + plan multipliers, throttle foundation, lock fail strategy.
  Run: `cd backend && pytest apps/security --no-cov`.
* **Live stack** — `python manage.py shell < scripts/verify_edge_security.py`
  inside the web container: real Lua scripts, lock exclusion, hot reload,
  16/16 checks.
* **Load** — `k6 run deploy/load/k6-rate-limit.js`: flood scenario must be
  throttled (429 + Retry-After, never 5xx) while concurrent legit traffic
  sees <1% throttling and p95 <500ms.
* **Chaos** — stop Redis mid-load (`docker compose stop redis`): traffic must
  continue (fail-open) and the log shows the breaker + degraded decisions;
  `docker compose start redis` restores distributed limiting within ~5s.

---

## 9. Performance

Hot-path cost per request: config snapshot access (monotonic-clock check,
in-process), IP parse, a few in-memory pattern scans, and 1–2 Redis
round-trips (pipelined reputation read + one Lua call; sub-millisecond on the
compose network, bounded at 1.5s). Event writes are async; nothing blocks on
Postgres. Exempt paths (`/health/`, `/static/`, `/media/`, `/metrics`) skip
the layer entirely. Existing `RequestTimingMiddleware` p50 ~20ms is
preserved (verified via gateway smoke test).

---

## 10. Final implementation report

**Delivered** (this prompt — infrastructure & security foundation only):

* `apps.security` — 18 modules: layered hot-reload config, three atomic Lua
  algorithms + memory fallback, distributed engine with fail strategy +
  circuit breaker, spoof-resistant IP resolution, IP rules (DB), reputation,
  bot classification, WAF-lite, immutable event pipeline, EdgeGuard +
  TenantRateLimit middleware, DRF throttle foundation, distributed locks,
  Celery retention, admin, system checks, migration.
* Nginx: env-tunable zones/maps template, server hardening snippet,
  Cloudflare real-IP snippet, hardened `app.conf.template`, prod compose
  wiring; `nginx -t` validated.
* Config surface: `.env.example` + `deploy/.env.prod.example` sections;
  settings/beat wiring; PyYAML dependency.
* Tests: 88 new (all passing), full suite 521 passing (zero regressions),
  16/16 live checks, k6 scenario, chaos procedure.

**Key decisions**: dedicated raw Redis client (Lua needs; HA-reconfigurable
independent of the app cache) · sliding-window-log default (precision) +
GCRA for smoothing · WAF scans request line only (false-positive control;
bodies belong to Cloudflare/validation) · challenges delegated to Cloudflare
(an origin cannot meaningfully CAPTCHA) · deny rules act even in monitor
mode (operator intent is explicit) · dev overlay is monitor-mode so local
work is never blocked.

**Known risks / limitations**:

1. Fail-open + Redis down = per-container budgets (documented; choose
   fail-closed only with HA Redis).
2. UA-based bot detection is trivially evadable by sophisticated actors —
   by design; Cloudflare owns advanced bot management.
3. WAF rules are conservative; enforce only after a monitor soak per
   environment (staging overlay ships monitor for this reason).
4. Country/ASN blocking is edge-delegated; the app records CF enrichment but
   does not resolve GeoIP/ASN itself (no MaxMind dependency yet).
5. `SECURITY_ENVIRONMENT` in the running dev stack is `development`
   (monitor); flip a `SecuritySetting` (`mode: enforce`) to demo blocking.

**Recommendations / next steps**: implement endpoint-specific limits on
`SecurityScopedThrottle`/`IPScopedThrottle` (login, signup, OTP, password
reset, AI, exports) per the next document; feed `reputation.penalize(ip,
"auth_failure")` from the login flow; add a Grafana panel over the JSON
security log; consider Sentinel/Cluster for production Redis before any
fail-closed scope; periodic Cloudflare IP-range refresh (config, no deploy).
