# Security hardening (Phase 10)

This document describes the defence-in-depth controls layered onto the app and
how to operate them. For verification see [`tests/security/`](tests/security/)
and [`TESTING.md`](TESTING.md); for an assessment checklist see
[`tests/security/PENTEST_CHECKLIST.md`](tests/security/PENTEST_CHECKLIST.md).

## Browser-side controls

| Control | Where | Notes |
|---|---|---|
| **Strict CSP** | `frontend/packages/config/src/securityProxy.ts (each app: frontend/apps/*/src/proxy.ts)` | Per-request `nonce` + `'strict-dynamic'`; no effective `unsafe-inline` for scripts. Next applies the nonce to its own bundles. |
| **Trusted Types** | middleware (report-only) + `shared/security/trustedTypes.ts` | `require-trusted-types-for 'script'` ships **report-only** first; a `default` policy blocks cross-origin script URLs. Flip `CSP_TT_ENFORCE=1` to enforce once reports are clean. |
| **SRI** | `frontend/next.config.ts` (`experimental.sri`) | `integrity="sha384-…"` on build `<script>` tags → tampered chunks rejected. |
| **Permissions-Policy** | middleware (frontend) + `apps/common/middleware.py` (API) | Every powerful feature (camera, mic, geo, usb, payment, …) denied. |
| **COOP / COEP / CORP** | middleware (frontend) + backend middleware | `same-origin` opener, `credentialless` embedder, `same-origin` resource policy → cross-origin isolation, blocks XS-Leaks and no-cors embedding. |
| **Secure storage** | `shared/lib/storage.ts` | Tokens live only in httpOnly cookies. `set()` rejects credential-looking keys/values; `clearAll()` wipes web storage on logout. |
| **Service Worker hardening** | `frontend/public/sw.js` | Same-origin GET only; never caches cross-origin API responses; validates `message` sender origin; won't cache `no-store`/`private`/non-basic navigations. |
| **Offline data encryption** | `shared/pwa/crypto.ts` + `sw.js` | Outbox request bodies AES-GCM encrypted at rest in IndexedDB with a **non-extractable** key; the SW decrypts only at replay time. |

## Server-side controls (pre-existing + extended)

- httpOnly + `Secure` + `SameSite` JWT cookies (`CookieJWTAuthentication`).
- Brute-force protection (`django-axes`) + per-scope DRF throttling (auth, signup, password_reset, payment, backup).
- Always-on `nosniff`; prod HSTS preload, SSL redirect, secure cookies.
- Strict API CSP (`default-src 'none'`) outside DEBUG; COOP/CORP/Permissions-Policy/`X-Permitted-Cross-Domain-Policies` on every response.
- Multi-tenant isolation enforced at the permission layer.

## Audit logging

`apps/auditlog` records security-relevant events (`AuditEvent`):

- writes (create/update/delete), logins/logouts, payments, exports, backup/restore, DR mode changes;
- **access-denied** (401/403) on non-auth API paths — probing / broken-access-control attempts (Phase 10);
- each event captures the **real client IP** (X-Forwarded-For first hop), actor, tenant, and user-agent.

## CSP / Trusted-Types reporting

The middleware sets `report-uri`/`report-to` → `frontend/apps/admin/src/app/api/security/csp-report/route.ts`,
which logs a compact line per violation. Watch these during the Trusted-Types
report-only rollout, then set `CSP_TT_ENFORCE=1` once clean.

## Rollout / operations

1. Deploy with Trusted Types in **report-only** (default).
2. Watch `[csp-report]` log lines for a week of real traffic.
3. Fix any legitimate violations (or add the offending lib's policy name to the
   `trusted-types` allowlist in `middleware.ts`).
4. Set `CSP_TT_ENFORCE=1` to enforce.

### Environment flags
| Var | Default | Effect |
|---|---|---|
| `CSP_TT_ENFORCE` | unset | `1` moves Trusted Types from report-only into the enforced CSP. |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api` | Drives the CSP `connect-src` allowlist. |

## Known follow-ups
- Promote Trusted Types to enforce after the report-only soak.
- Consider COEP `require-corp` (stricter than `credentialless`) once all
  subresources are confirmed same-origin/CORP-tagged.
