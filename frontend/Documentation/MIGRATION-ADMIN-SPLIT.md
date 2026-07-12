# Migration Report — Admin Panel / Client Application Separation

Date: 2026-07-10 · Branch: `feature/dockerize-dev-stack` (working tree)

The single Next.js app under `frontend/` was restructured into an npm-workspaces
monorepo: `apps/client` (public marketing zone), `apps/admin` (authenticated
workspace + PWA), and nine shared `packages/*`. **No URL changed, no backend
endpoint changed, no user-visible behavior changed** (beyond new RBAC gating
described below). See `frontend/ARCHITECTURE.md` for the target architecture.

## 1. What the analysis found (drove the design)

- **No end-user portal exists.** Every `(protected)` route is staff/owner
  back-office; login requires a staff account + Hostel ID; signup provisions a
  hostel owner. "Students/Residents" are records staff manage. Therefore the
  correct split is *marketing site* vs *admin workspace* (the `www` vs
  `dashboard` pattern), not *user app* vs *admin app*.
- **RBAC did not exist** — `role` from `/auth/me/` was only a Topbar label;
  navigation was static; the only gate was authenticated-or-redirect.
- **The PWA is root-scoped** (`/sw.js`, scope `/`), e2e suites, backend
  password-reset links and installed users' URLs all assume current paths —
  so the split preserves every URL via multi-zone fallback rewrites instead of
  moving admin under a `/admin` basePath (an `/admin → /dashboard` redirect
  provides the friendly entry point).

## 2. Route mapping

| Route(s) | Before | After |
|---|---|---|
| `/`, `/about`, `/privacy`, `/terms`, `/security`, `robots.txt`, `sitemap.xml` | single app | **apps/client** (served directly) |
| `/login`, `/signup`, `/verify-otp`, `/forgot-*`, `/reset-password`, `/select-hostel` | single app | **apps/admin** `(public)` — reached through client-zone rewrite, same URLs |
| `/dashboard` … `/visitors` (all 27 protected routes), `/offline`, `/sw.js`, `/manifest.webmanifest`, `/icons/*`, `/api/security/csp-report` | single app | **apps/admin** — same URLs via rewrite |
| `/admin` | 404 | redirect → `/dashboard` |

## 3. Code migration map

| Old (`frontend/src/…`) | New |
|---|---|
| `shared/ui/*` (13 primitives), `shared/ui/toast/*`, `shared/providers/ThemeContext` | `packages/ui` (`@hostel/ui`) |
| `shared/ui/{Sidebar,Topbar,MobileBottomNav,CommandPalette}`, `shared/providers/SidebarContext` | `apps/admin/src/components/shell/` (admin chrome, not shared) |
| `shared/api/{apiClient,offlineWrite}` | `packages/api` |
| `shared/auth/*`, `shared/lib/auth.ts` (token shim) | `packages/auth` |
| `shared/pwa/*`, `shared/providers/PwaProvider` | `packages/pwa` |
| `shared/lib/{dates,finance,storage,exporters,monitoring,hostel}` | `packages/utils` |
| `shared/hooks/useApi` | `packages/hooks` |
| `shared/types/common` | `packages/types` |
| `shared/security/trustedTypes`, `src/proxy.ts` header logic | `packages/config` (`createSecurityProxy`) |
| `features/landing`, `app/(marketing)`, `app/page.tsx`, `robots.ts`, `sitemap.ts` | `apps/client/src` |
| all other `features/*`, `app/(public)`, `app/(protected)`, `app/offline`, `manifest.ts` | `apps/admin/src` |
| — (new) | `packages/permissions` (RBAC) |

Import style: `@/shared/**` → package barrels (`@hostel/ui`, …). Per-app code
keeps the `@/*` alias. 355 imports across 128 files were rewritten; zero
`@/shared` references remain.

## 4. Duplication removed / dead code deleted

- `shared/api/endpoints.ts` (empty), `shared/constants/` (empty dir),
  `features/owner/` (two 0-byte files) — deleted.
- `shared/lib/finance.ts` no longer imports `features/hostels/types`
  (layering violation): it now declares minimal structural types.
- `globals.css` design tokens extracted once to
  `packages/ui/src/styles/tokens.css`; both apps import it (theme divergence
  per app is now possible without duplication).
- `tailwind.config.ts` deleted (vestigial v3 config; Tailwind v4 is CSS-first).
- Unused dependencies `axios` and `jwt-decode` dropped.
- Known remaining duplication (deliberately deferred, functional as-is):
  `VacateStudentButton` exists in both `features/students` and
  `features/payments`; two API call conventions (`api.*` wrapper vs raw
  `apiFetch`) coexist across feature modules. Consolidating them is a
  behavior-risk refactor best done per-feature with its own tests.

## 5. RBAC (new)

`@hostel/permissions` introduces roles (SUPER_ADMIN…GUEST), module
permissions, and a route→permission policy consumed by the protected layout
(403 `AccessDenied`), Sidebar, MobileBottomNav and CommandPalette.
**Backward compatibility rule:** a missing/unknown backend role normalizes to
OWNER (full access) because the backend does not issue differentiated roles
yet — no existing account loses anything. If the backend ever returns e.g.
`WARDEN`, that account now gets the warden grant set (no finance/settings/
tenants/backup) — the first real behavior change RBAC is meant to introduce.

## 6. State management

No global stores were shared between marketing and admin concerns, so stores
split naturally: hostel/feature stores live in admin features; auth/session
state (`@hostel/auth`) and PWA state (`@hostel/pwa`) are packages used by both
apps; `SidebarContext` is admin-only shell state.

## 7. Security improvements

- Admin code can no longer appear in the marketing bundle (separate apps).
- Both zones share one `createSecurityProxy()` so CSP/Trusted-Types/COOP/COEP
  never drift; the client proxy runs ONLY on marketing routes to avoid
  double-nonce CSP on proxied admin documents.
- Route-, nav- and component-level permission gating (see §5).

## 8. Performance

- Marketing pages no longer ship any admin dependency (recharts etc. absent
  from the client app entirely).
- `optimizePackageImports` retained per app; admin zone gets a dedicated asset
  namespace (`/admin-static`) in production.
- Sidebar prefetch behavior, React Compiler, and console-stripping preserved.

## 9. Build / CI / deploy changes

- `frontend/` is the workspace root — lockfile path, CI `working-directory`,
  and Docker build context are unchanged.
- Two Dockerfiles (`apps/*/Dockerfile`, workspace-aware, standalone output
  nested per app). Compose: `frontend` (client) + `admin` services;
  `ADMIN_PORT=3001` added to `.env`; CSRF trusted origins include `:3001` for
  direct-admin dev access. nginx templates unchanged (single upstream — the
  client zone routes internally).
- Workflows updated: build/scan/deploy matrices produce `hostel-client` +
  `hostel-admin`; `deploy.sh`/`rollback.sh` handle both images; e2e/DAST/LHCI
  start both zones via `scripts/start-zones.mjs`.
- Vitest runs as three projects (admin / client / packages); Playwright
  webServer builds both apps and starts both zones.

## 10. Manual steps required (out-of-repo)

1. **Vercel**: split into two projects (see ARCHITECTURE.md §Deployment) —
   Root Directories `frontend/apps/client` and `frontend/apps/admin`; set
   `ADMIN_ZONE_URL` on the client project; move the public domain to the
   client project. Until this is done, the existing single Vercel project
   will fail to build (its root points at `frontend/`, which is no longer a
   Next app).
2. **Render backend env**: no change needed (single public origin preserved).
3. Local dev: `docker compose up -d --build` rebuilds both zone containers;
   or run natively with `npm run dev:admin` + `npm run dev:client`.

## 11. Verification performed

- `tsc --noEmit` clean for both apps (packages type-check transitively).
- `next build` succeeds for both apps (all 40+ routes present).
- `vitest run`: 23/23 tests green across 7 files (admin + packages projects).
- `eslint`: 0 errors (18 pre-existing warnings).
- Playwright smoke suite (`e2e/smoke.spec.ts`, chromium): **19/19 passed**
  against the real two-zone topology (client :3100 proxying admin :3101) —
  login flow and every protected route render through the zone rewrite.
- `docker compose config` parses; workflows YAML-validated.
