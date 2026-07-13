# Enterprise Authentication Flow — Audit & Refactor Report

_Phases 1–2 of the Authentication Flow Refactor. This is the internal audit of
the **existing** MyHostel Cloud Platform auth system, followed by the refactor
decisions. The system was analyzed in full before any code changed; the
guiding rule throughout is **refactor, never rewrite — preserve every working
feature and API contract.**_

---

## 1. Current architecture (as-built)

### Backend (Django + DRF + SimpleJWT)

| Concern | Where | Notes |
| --- | --- | --- |
| User model | `apps/accounts/models.py:19` `User(AbstractUser)` | single global `role` (choices: OWNER/ADMIN/MANAGER/RECEPTIONIST/ACCOUNTANT/WARDEN/STAFF/STUDENT/PARENT/RESIDENT/READ_ONLY), `mfa_enabled`, `password_version` (pwv) |
| Tenant model | `apps/tenants/models.py:191` `Hostel` | `slug` = permanent workspace username / subdomain; `status` lifecycle; `owner` FK |
| Membership | `apps/accounts/models.py:34` `UserHostel` | `(user, hostel)` unique; **role is on the User, not the membership** |
| RBAC | `apps/common/rbac.py` | roles + portals + `module.action` permissions; per-workspace overrides in `Hostel.settings`; custom per-tenant roles unioned in from `apps/staff` |
| JWT | `apps/accounts/tokens.py`, `authentication.py` | httpOnly cookies; claims `hostel_id/hostel_code/workspace/role/pwv/portal`; rotation + blacklist; remember-me extends refresh only |
| Tenant resolution | `apps/tenants/middleware.py:107` | subdomain > `X-Workspace` > `X-Hostel-Code` > `X-Hostel-Id`; status gate before auth |
| Auth enforcement | `apps/accounts/authentication.py:22` `CookieJWTAuthentication` | pwv check → hostel resolve → cross-tenant token binding → membership (cached) → CSRF on cookie writes |
| Authorization | `apps/common/permissions.py`, `apps/common/rbac.py` | `HasHostelContext`/`IsHostelResolved` (membership), `RequirePermission`/`ActionPermissions` (RBAC), `IsSuperUser`/`IsPlatformAdmin` (platform) |
| Subscription / features | `apps/subscriptions/` | DB-driven plans/features/limits; entitlement snapshot cached; `RequiresFeature`, `enforce_limit` |
| Provisioning | `apps/tenants/services.py:114` `provision_workspace()` | one transaction: hostel + slug + owner membership + default settings + trial + audit |

The backend is **enterprise-grade and already implements the intended
pipeline** (tenant → membership → role → permission → subscription → feature).
It needs only surgical fixes, not restructuring.

### Frontend (Next.js monorepo — client + admin zones)

| Concern | Where | Notes |
| --- | --- | --- |
| Zone split | `apps/client` (marketing, owns public origin) + `apps/admin` (whole app) | client fallback-rewrites all non-marketing paths to admin |
| Session | `packages/auth/AuthProvider.tsx` | cookie-native; loads `/auth/me`; single-flight refresh in `packages/api/apiClient.ts` |
| Tenant context | `packages/utils/workspace.ts` | derived statelessly from hostname; no React TenantProvider |
| RBAC (client) | `packages/permissions/` | static `ROLE_GRANTS` map + `routePolicy` table gating layout/sidebar/nav/palette |
| Login UI | `apps/admin/.../WorkspaceLoginForm.tsx` | one component behind five portal pages |

---

## 2. Findings

### Critical / security

1. **Cross-tenant audit-log leak.** `apps/auditlog/views.py` `AuditEventViewSet`
   used `queryset = AuditEvent.objects.all()` with role-only
   `[IsAuthenticated, IsOwnerOrManager]` — **no hostel scoping and no
   membership check**. An owner/manager of one workspace could read every
   tenant's audit events. → **FIXED** (see §3).

2. **Frontend role fail-open to OWNER.** `packages/permissions/roles.ts`
   `normalizeRole()` mapped any unknown/missing role to **OWNER** (full
   tenant-admin). The premise ("backend doesn't issue real roles yet") is
   obsolete — the backend issues a real `role` on every token and `/auth/me`.
   → **FIXED**: least-privilege fallback + alias mapping (see §3). (Backend
   remains authoritative regardless; this is defense-in-depth for the UI.)

3. **Entitlements enforcement is off by default.** `ENTITLEMENTS_ENFORCED`
   defaults to `False` (`config/settings.py`), making every `RequiresFeature`
   and `enforce_limit` a no-op. → Documented; enabling it is an ops/config
   decision (flipping it without seeded plans would break existing tenants), so
   it is **called out** rather than flipped blindly.

### Duplication / multiple entry points

4. **Five login pages, one component.** `/login` (staff), `/staff-login`
   (exact duplicate of `/login`), `/admin`, `/student`, `/parent` — all render
   `WorkspaceLoginForm` differing only by a `portal` prop. → **Collapsed** to
   one unified tenant login; the four extra routes now redirect to `/login`
   (URLs preserved).

5. **Duplicate login route (backend).** `/api/auth/login/` and `/api/auth/token/`
   map to the same view. → **Kept** (documented alias) — removing either would
   break existing clients; harmless.

6. **Duplicate `AuthUser` type** (`AuthProvider.tsx` and `auth.api.ts`) and
   `Plan` defined 3×. → Noted; low-risk drift, left as-is to avoid churn.

### Inconsistent redirects

7. Post-auth redirects diverged across surfaces: the login form was role-aware
   (uses backend `redirect`), but the public layout, `logout()`, the admin
   root page, and the marketing Navbar all hardcoded `/dashboard`, misrouting
   STUDENT/PARENT sessions into an `AccessDenied`. → **Standardized** on
   `postAuthHome()` (see §3).

### Non-issues (verified, no change needed)

- `UserViewSet` / `UserHostelViewSet` **are** hostel-scoped via
  `_hostel_ids_for` — no cross-tenant user leak.
- Login already admits **all roles when `portal` is empty** and routes by
  `default_route_for_role` — the backend needs no change for a unified login.
- Tenant isolation, JWT/pwv, refresh rotation, remember-me, workspace-scoped
  password reset, django-axes + progressive lockout, async audit — all sound.

---

## 3. Refactor decisions (what changed)

**Principle:** the backend architecture is correct; the incoherence lived in
the frontend (five portal login pages, fail-open role, scattered redirects)
plus two backend security gaps. Changes are additive and backward-compatible.

| Change | Files | Phase |
| --- | --- | --- |
| Scope audit events to the caller's workspace(s); require membership | `apps/auditlog/views.py` | 2, 9, 12 |
| Unified tenant login (all roles, no portal gate); portal pages → redirects | `apps/admin/.../login`, `/staff-login`, `/admin`, `/student`, `/parent`, `WorkspaceLoginForm` | 7 |
| Single `postAuthHome()` redirect helper adopted everywhere | `packages/permissions`, admin layouts/root, `AuthProvider`, client Navbar | 8, 10, 11 |
| Least-privilege `normalizeRole` fallback + aliases | `packages/permissions/roles.ts` | 9, 10 |
| Owner workspace selector for multi-org owners | `apps/admin/.../select-workspace` | 6 |

Preserved unchanged: every `/api/auth/*` and `/api/tenants/*` contract, JWT
cookies, RBAC semantics, subscription/feature gating, tenant isolation, and the
existing test suites (extended, not rewritten).

---

## 4. Phase completion (5, 6, 9)

A follow-up pass closed the three phases that the first cut left partial. All
additive, all reusing existing services, no contract changes.

| Phase | Gap | Fix | Files |
| --- | --- | --- | --- |
| 5 — Signup | Provisioning created the tenant + owner + trial but **no `Subscription` row and no default departments**. | `provision_workspace()` now seeds a default subscription via the existing `subscriptions.lifecycle.assign_plan` service (real `Subscription` row + immutable `SubscriptionEvent` + entitlement-cache refresh; trial status bounded by the trial end date) and a default department set. Both are savepoint-isolated best-effort so a fresh install with no seeded plans (or a staff-app hiccup) still provisions cleanly; `plan_name` remains the entitlement fallback. | `apps/tenants/services.py` |
| 6 — Owner login | The `/select-workspace` selector existed but was **not auto-triggered after login** for multi-org owners. | The login form now routes a root-domain OWNER/ADMIN through `/select-workspace`, which loads their organizations and auto-forwards when there is exactly one (picker only when several). A workspace-host login stays bound to its single workspace. | `WorkspaceLoginForm.tsx` |
| 9 — Authorization sweep | Only the audit-log endpoint was reviewed. A full DRF view sweep found two more platform-surface leaks in disaster recovery. | `DRModeView` (global DR mode switch) and `DRStatusView` (cross-tenant restore history) are now **super-admin only** (`IsSuperUser`) — a tenant `ADMIN` could previously flip the platform-wide DR mode and read every tenant's restore runs. Per-hostel restore/validate keep the `IsDRAdmin` + `_can_touch_hostel` membership gate. Every other tenant-facing viewset was verified either hostel-scoped or correctly platform-gated. | `apps/backups/admin_api.py` |

Tests added: `apps/tenants/tests/test_workspace_service.py` (subscription +
departments seeding, and no-plans fallback), `apps/backups/test_dr_authz.py`
(tenant admin forbidden / super admin allowed on the global DR surfaces), and a
`login.test.tsx` case for the owner → selector route.
