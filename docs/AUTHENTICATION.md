# Tenant Authentication, Routing & Workspace Access

Prompt 02 — built on the workspace architecture in `MULTI_TENANCY.md`.
Every authentication request belongs to exactly one workspace; nothing
authenticates globally.

---

## Request lifecycle (auth)

```
Request to everest.myhostel.com/login (or X-Workspace: everest)
  │
  ├─ TenantResolutionMiddleware      resolve + validate workspace BEFORE auth
  │     unknown → 404 · suspended/expired/pending → 403 (professional error pages)
  │
  ├─ Login page loads that workspace's branding (public endpoint below)
  │
  ├─ POST /api/auth/login/  {username, password, portal, remember}
  │     user search is scoped to the resolved workspace's members only
  │     portal gate: the role must be admitted by that portal
  │     axes brute-force lockout · throttled (THROTTLE_AUTH) · audited
  │
  ├─ Tokens issued — bound to the workspace (see JWT claims)
  │     httpOnly + Secure + SameSite cookies; rotation + blacklist on refresh
  │
  └─ Response: {user, role, redirect, workspace, mfa_required}
        client navigates to the role's dashboard (redirect)
```

Every subsequent API request re-verifies: tenant (middleware) → token
validity + pwv → workspace binding → membership (cached) → role/permission.

## Workspace routing (frontend, admin zone)

**One unified tenant login authenticates every role** (Authentication Flow
Refactor). Authentication establishes identity; authorization (role +
permissions) decides access and where the session lands.

| Route | Purpose |
| --- | --- |
| `/login` | the single tenant login — all roles (owner, admin, staff, receptionist, accountant, warden, parent, student, security, laundry, maintenance …) |
| `/admin`, `/staff-login`, `/student`, `/parent` | **legacy redirects → `/login`** (kept so old bookmarks/links keep working; no role-specific login UI remains) |
| `/select-workspace` | owner workspace picker for accounts that belong to more than one hostel |

`/login` renders `WorkspaceLoginForm` (`features/auth/components/`): on a
workspace host it shows the tenant's logo/name/workspace-username (from the
public branding endpoint), asks for no Hostel ID, and renders
`WorkspaceErrorScreen` for unknown/suspended/expired workspaces. On the root
domain the legacy Hostel-ID flow is unchanged. It sends **no `portal`**, so the
backend admits every role and returns each role's `redirect`.

The backend `portal` gate (`PORTALS` in `apps/common/rbac.py`) still exists and
is honored when a caller supplies a `portal` — the API stays backward
compatible — but the UI no longer sends one. Post-auth destinations are
centralized in `postAuthHome()` (`@hostel/permissions`), used by the login
form, the public/protected layouts, logout and the marketing navbar so a
session never lands somewhere its role can't open.

Successful login follows the backend's `redirect`:
OWNER/ADMIN/staff roles → `/dashboard`, STUDENT/RESIDENT →
`/student/dashboard`, PARENT → `/parent/dashboard`. Portal dashboards are
role-gated stubs until their prompts ship.

## JWT model

Access token ~15 min; refresh 3 days (or `REMEMBER_ME_REFRESH_DAYS`, default
30, with `remember: true`). httpOnly/Secure/SameSite cookies, rotation with
blacklist-after-rotation, CSRF enforced on cookie-borne writes.

Claims on every token (issued via `apps/accounts/tokens.py`):

| Claim | Purpose |
| --- | --- |
| `hostel_id` / `hostel_code` | tenant binding (legacy names, used everywhere) |
| `workspace` | tenant's permanent workspace username |
| `role` | role at login (authorization always re-reads the DB role) |
| `pwv` | password-version fingerprint — password change kills every earlier token |
| `portal` | which login surface issued the session |

Enforcement in `CookieJWTAuthentication` on **every request**:
1. `pwv` must match the user's current password hash (password-change
   detection / forced logout; `POST /auth/password/change/` re-issues this
   device's cookies so only *other* devices are signed out).
2. If the request resolved a workspace, the token must belong to **that**
   workspace — a token minted on `everest.*` is a 401 on `himalayan.*`, even
   for a user who is a member of both. Cross-tenant token reuse is impossible.
3. Active membership of the token's workspace (Redis-cached, ~<20ms total).

## RBAC / permission system

`apps/common/rbac.py`:

* **Roles**: OWNER, ADMIN, MANAGER, RECEPTIONIST, ACCOUNTANT, WARDEN, STAFF,
  STUDENT, PARENT, RESIDENT (legacy), READ_ONLY. Platform staff =
  `is_superuser` (bypasses checks).
* **Permissions**: `module.action` strings (17 modules × view/create/edit/
  delete + feature permissions like `billing.collect`, `backups.restore`,
  `workspace.manage`). Wildcards `*` and `module.*` in grant lists.
* **Defaults** per role in `DEFAULT_ROLE_PERMISSIONS`; **per-workspace
  overrides** via `Hostel.settings["permissions"]["roles"][ROLE] = [...]` —
  configurable RBAC with no code change. Cached per (workspace, role) in
  Redis (`PERMISSIONS_CACHE_TTL`, default 300s) and invalidated on workspace
  save; effective lookup is <10ms warm.
* **DRF**: `RequirePermission("residents.create")` class factory and
  `ActionPermissions` (+ per-view `permission_map`) for new endpoints;
  existing endpoints keep their role classes (`STAFF_ROLES` now includes
  RECEPTIONIST).

Frontend mirror in `packages/permissions` (`can`, `permissionForPath`,
`portalHomeForRole`): gates routes (protected layout), sidebar, mobile nav
and command palette. `/student/*` requires `student-portal:view` (held only
by STUDENT/RESIDENT), `/parent/*` requires `parent-portal:view` (PARENT).
The backend remains authoritative — UI gating is UX, not security.

## API endpoints

| Endpoint | Notes |
| --- | --- |
| `POST /api/auth/login/` | tenant-scoped; `portal`, `remember`; returns `redirect`, `workspace`, `mfa_required` |
| `POST /api/auth/token/refresh/` | cookie rotation + blacklist |
| `POST /api/auth/logout/` | blacklists refresh, clears cookies, audited |
| `POST /api/auth/logout-all/` | revokes every outstanding refresh token |
| `GET /api/auth/me/` · `GET /api/auth/session/verify/` | current user / one-call session+workspace+role verification |
| `GET /api/auth/sessions/` · `DELETE /api/auth/sessions/{id}/` | device list (browser·OS label) / per-device logout |
| `GET /api/auth/permissions/` · `GET /api/auth/permissions/check/?permission=x` | effective permissions / point check |
| `POST /api/auth/password/forgot|reset/` | **workspace-scoped** on a workspace host (only that tenant's members; uniform anti-enumeration response); global only on the root domain |
| `GET /api/tenants/workspaces/public/` | unauthenticated login-page branding (name, workspace username, logo, locale) — never owner/plan/settings data |

## Sessions & security

Already in place and unchanged: django-axes lockout (5 fails / 15 min),
scoped throttles, Django password validators, signup email OTP verification,
session/device tracking via OutstandingToken, login history (`/auth/activity/`),
audit events (login, failed login, logout, password reset/change, access
denied, token revocation) with IP/user-agent/workspace. New in this prompt:
`last_login` stamping, password-change detection (pwv), portal-denial
auditing (`ACCESS_DENIED`), remember-me. **MFA prep**: `User.mfa_enabled`
field + `mfa_required` in the login response — enabling a factor later is an
additive verification flow, not a structural change.

## Error responses

Machine-readable and uniform: workspace-level failures use the envelope
`meta.code` (`workspace_not_found|suspended|expired|inactive|pending`);
credentials failures are always the same generic message (no user/tenant
enumeration); portal denials are explicit ("use your own portal's login
page"); expired sessions are 401s the SPA answers with one single-flight
refresh, then forced re-login.

## Testing

`apps/accounts/tests/test_tenant_auth.py` (36 tests): workspace-context and
subdomain login, cross-tenant login + token-reuse rejection, the full
portal×role matrix, remember-me lifetimes, pwv invalidation + current-session
survival, workspace-scoped reset (request & confirm), session verify,
permissions endpoints incl. per-workspace overrides, public branding (incl.
suspended gate). Frontend: `packages/permissions/__tests__/portals.test.ts` +
updated login-flow tests (portal payload, redirect, remember-me).

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| 401 "belongs to a different workspace" | token minted on another workspace host — sign in on this workspace |
| 401 "invalidated by a password change" | pwv rotation after a password change/reset — sign in again |
| "cannot sign in here" on correct password | role not admitted by that portal — use the portal for your role |
| Password reset "works" but no email on a workspace host | the account isn't a member of that workspace (scoped lookup) |
| Permission change not applying | cached per (workspace, role); saving the workspace invalidates, else `PERMISSIONS_CACHE_TTL` |
