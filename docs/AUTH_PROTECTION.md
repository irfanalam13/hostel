# Authentication Protection & API Rate Limiting (Prompt 08)

Enterprise protection for every authentication flow and every API endpoint,
built **on top of** the edge-security foundation (Prompt 07 —
`docs/EDGE_SECURITY.md`). Same principles: nothing hardcoded, everything
config-driven and hot-reloadable, fully tenant/plan aware, monitor→enforce
rollout, and 100% backward compatible (556 tests green, zero regressions).

This layer does **not** replace what already existed — it composes with it:

| Existing (kept) | Added here |
|---|---|
| django-axes per-(ip,username) login lockout | progressive multi-tier lockout + CAPTCHA escalation |
| SimpleJWT rotation + blacklist + `pwv` fingerprint | replay primitive for non-JWT surfaces (webhooks/signed) |
| httpOnly cookie JWT + CSRF + tenant binding | per-role/plan/method global API budget |
| enumeration-safe auth responses (unchanged) | detection of the enumeration/stuffing *behaviour* |
| DRF `throttle_scope` (still works everywhere else) | config-driven security throttle classes on auth views |

---

## 1. Where it plugs in

```
EdgeGuard (Prompt 07: IP rules, reputation, bots, WAF, per-IP limits)
  ↓
TenantRateLimit (Prompt 07: per-workspace, plan-scaled)
  ↓
DRF throttles:
   • RoleRateThrottle           global per-role/plan/method budget (all views)
   • LoginRateThrottle etc.     per-IP ceilings on each auth endpoint
   • Tenant*Throttle            expensive surfaces (exports/AI/search/…)
  ↓
auth_guard (in the login/OTP serializers):
   progressive lockout  →  CAPTCHA escalation  →  credential-stuffing /
   enumeration detection  →  enumeration-safe response
  ↓
CookieJWTAuthentication (unchanged) → RBAC → business logic
```

New code lives in `backend/apps/security/`: `progressive.py`, `captcha.py`,
`abuse.py`, `replay.py`, `auth_guard.py`, `throttles.py`, `exceptions.py`
(+ auth policies in `defaults.py`, wiring in `accounts/views.py`).

---

## 2. Authentication endpoint policies

Every sensitive auth endpoint now carries a dedicated, config-mapped throttle
(per client IP) — replacing the coarse legacy `auth`/`signup`/`password_reset`
DRF scopes:

| Endpoint | Throttle → config scope | Default |
|---|---|---|
| `POST /auth/login/`, `/auth/token/` | `auth_login` | 10 / 5 min |
| `POST /auth/token/refresh/` | `auth_token_refresh` | 60 (token bucket, 1/s refill) |
| `POST /auth/signup/` | `auth_signup` | 5 / hr |
| `POST /auth/signup/request-otp/` | `auth_signup_otp` | 6 / hr |
| `POST /auth/password/reset/` (OTP verify) | `auth_otp_verify` | 10 / 10 min |
| `POST /auth/password/forgot/` | `auth_password_reset` | 5 / hr |
| `POST /auth/password/change/` | `auth_password_change` (per user) | 10 / hr |
| `POST /auth/hostel-id/forgot/` | `auth_forgot_hostel` | 5 / hr |
| `DELETE /auth/sessions/{id}/` | `auth_session_revoke` (per user) | 30 / 5 min |

All limits are pure config (`rate_limits.<scope>`), hot-reloadable, and
overridable per environment (dev ships relaxed). MFA verification
(`auth_mfa_verify`) is pre-wired for when a factor ships.

### Progressive lockout (login + OTP verify)

Never a fixed block. Cumulative failures within a rolling window
(`auth.progressive_lockout`) escalate: **5→30s, 10→2m, 15→10m, 20→1h,
30→24h** (default, fully configurable). Tracked **per IP and per
(workspace,identifier)** — the longer active block wins, so neither a single
account nor a single source can be attacked around the edge. Applied *before*
credential verification (a locked caller never reaches the DB). A successful
auth clears the counters. This complements django-axes (still the primary
fixed cool-off); progressive lockout adds escalation, feeds CAPTCHA, and
generalises to OTP brute-forcing.

### CAPTCHA escalation

Turnstile / reCAPTCHA / hCaptcha, verified server-side (`captcha.py`). A
challenge is required **only** after `trigger_after_failures` failures or when
the source IP reputation is suspicious/blocked — never on a first clean login.
Hard no-op until `SECURITY_CAPTCHA_SECRET` is set (enabling the flag alone
can't lock anyone out); verification network errors honour `fail_open`. The
login response carries `captcha_required` so the SPA knows when to show the
widget; the client submits the token in the body (`captcha_token` / provider
field) or `X-Captcha-Token`.

---

## 3. API rate limiting

### Per role / plan / method (global)

`RoleRateThrottle` (added to `DEFAULT_THROTTLE_CLASSES`) gives **every**
authenticated request a budget resolved from the caller's role
(`role_limits.roles`), scaled by the workspace plan multiplier, with writes
costing more than reads (`method_costs`; `OPTIONS`=0). Anonymous callers use
`role_limits.anon`. This delivers per-user, per-role, per-plan and per-method
policy across the whole API without touching individual views. Config-gated
(`role_limits.enabled`; off in dev) and monitor-mode-aware.

### Expensive / abuse-prone surfaces (tenant-scoped, plan-scaled)

Ready-to-attach throttle classes back these scopes: `exports`, `reports`,
`analytics`, `search`, `notifications_send`, `ai`, `payment`, `file_upload`.
Attach to any view with `throttle_classes = [ExportRateThrottle]` — the budget
is shared per workspace and scaled by plan. (GraphQL/WebSocket are not part of
the current stack; the same base classes cover them when added.)

### Replay protection

`replay.seen_before(scope, nonce, ttl)` — atomic single-use for webhooks,
signed requests and OTP races. JWT replay itself is already handled
structurally (SimpleJWT rotation + blacklist-after-rotation + the `pwv`
password fingerprint that dies every prior token on password change).

---

## 4. Abuse detection

| Signal | Detection | Response |
|---|---|---|
| Brute force | repeated failures / identity | progressive lockout + `auth_failure` reputation penalty |
| Credential stuffing | many DISTINCT identities from one IP (`auth.credential_stuffing`) | reputation penalty → CAPTCHA / reputation block; event |
| Password spraying | one identity across many IPs + per-IP identity spread | per-IP identity-cardinality + reputation compounding |
| Enumeration | many DISTINCT lookup targets from one IP against reset/forgot/signup-otp | reputation penalty + event (responses stay uniform) |
| Bot / automation | Prompt-07 UA classification + edge | challenge (Cloudflare) / block; reputation feed |
| Token theft/replay | SimpleJWT rotation+blacklist, `pwv`, replay primitive | prior tokens revoked immediately |
| Session hijacking | tenant-bound tokens; password change invalidates all | forced re-auth |

Identities/targets are stored as short salted hashes (cardinality, not
values), in capped windowed sets — bounded memory, no PII at rest.

---

## 5. Errors, logging, audit

* **Standard envelope** — lockout → `429` (`auth_locked`, dynamic
  `Retry-After`), CAPTCHA → `403` (`captcha_required` / `captcha_failed`),
  limits → `429` (`rate_limited` / `tenant_rate_limited`). All rendered
  through the platform `StandardJSONRenderer`; no internals leaked; login
  failures stay generic (no user/hostel enumeration).
* **Security events** — new `SecurityEvent` types (`auth_failure`,
  `auth_lockout`, `captcha_required`, `captcha_failed`, `api_role_limited`,
  `replay_blocked`) via the Prompt-07 pipeline (structured JSON log +
  immutable rows, async, flood-deduped).
* **Audit** — the existing `record_event` login/logout/password/OTP audit
  trail is untouched and still fires.

---

## 6. Configuration surface

Everything resolves through the Prompt-07 layered chain (defaults → env
overlay → YAML → `SECURITY_*` env → DB `SecuritySetting`, hot reload). Key env
knobs (full list in `.env.example`): `SECURITY_AUTH_ENABLED`,
`SECURITY_LOCKOUT_ENABLED`, `SECURITY_LOCKOUT_TIERS`, `SECURITY_ROLE_LIMITS_ENABLED`,
`SECURITY_CAPTCHA_ENABLED/PROVIDER/SECRET/SITE_KEY`. Per-tenant/plan overrides
use `SecuritySetting` rows and the plan-multiplier table — no redeploy.

---

## 7. Testing

* **Unit/integration (hermetic)** — `apps/security/tests/`: 123 security tests
  incl. Prompt 08 — progressive tiers/scoping/reset, CAPTCHA decision+verify,
  credential-stuffing/enumeration cardinality, replay semantics, auth_guard
  gate, throttle classes (per-IP, per-role, per-plan, per-method, OPTIONS-free),
  and **end-to-end login lockout over the real `/api/auth/login/` endpoint**
  (`test_login_integration.py`). Uses an in-process Redis double
  (`tests/fake_redis.py`) — no external service.
* **Live** — `python manage.py shell < scripts/verify_auth_protection.py`
  (real Redis): 12/12 — lockout escalation, stuffing, replay, throttles.
* **Full suite** — 556 passed, zero regressions.

---

## 8. Final implementation report

**Delivered**: config-driven auth policies (endpoint limits, progressive
lockout tiers, CAPTCHA, role/plan/method budgets); progressive lockout engine;
CAPTCHA trigger+verify (3 providers); credential-stuffing/enumeration/
brute-force detection feeding reputation; replay primitive; 19 concrete
throttle classes; auth-view wiring (login, refresh, signup, OTP, password
reset/change, forgot-hostel, session revoke); global `RoleRateThrottle`;
6 new security-event types (+migration); tests, live verifier, docs.

**Backward compatibility**: the login/OTP flows keep identical success/error
shapes (a `captcha_required` hint is additive); legacy DRF `throttle_scope`
still serves every non-auth view; the whole layer is config-gated and ships
**monitor/relaxed in dev** so local work is never blocked. Verified: bad
login → 400 generic, signup-OTP → 200, CSRF → 200 through the gateway; 556
tests green.

**Key decisions**: progressive lockout complements (not replaces) axes;
CAPTCHA can't lock users out without a secret; WAF/body inspection stays at the
edge; enumeration detection observes behaviour while responses stay uniform;
`RoleRateThrottle` gives blanket per-role/plan coverage instead of editing
dozens of views.

**Known risks / limitations**:
1. Progressive lockout + reputation + stuffing/enumeration state live in Redis;
   a Redis outage degrades them to "off" (axes + per-IP edge limits still
   protect) — by design (fail-open).
2. CAPTCHA is off until a provider secret is configured; wire the SPA widget
   (`NEXT_PUBLIC_CAPTCHA_SITE_KEY`) before enabling in production.
3. Impossible-travel / geo-anomaly detection is delegated to Cloudflare
   (country/ASN) + reputation; no in-app GeoIP yet.
4. Expensive-surface throttles are provided and unit-tested but only attached
   where clearly beneficial; attach per view as those endpoints are hardened.
5. Dev runs the auth layer in monitor/relaxed mode — flip `SECURITY_ENVIRONMENT`
   or a `SecuritySetting` to exercise enforcement locally.

**Recommendations**: enable `role_limits` + CAPTCHA in staging and soak in
monitor before enforce; attach the tenant throttles to exports/analytics/AI as
those ship; feed `reputation.penalize(ip, "auth_failure")` is already wired —
add a Grafana panel over the `auth_*` security events; consider Sentinel/Cluster
Redis before choosing fail-closed for any auth scope.
