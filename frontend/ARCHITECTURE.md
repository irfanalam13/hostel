# Frontend Architecture — Monorepo (Client + Admin Zones)

The frontend is an npm-workspaces monorepo with two independent Next.js
applications composed as **multi-zones on a single public origin**, plus a set
of shared TypeScript-source packages.

```
frontend/                      ← workspace root (lockfile, tooling, e2e)
├── apps/
│   ├── client/                ← CLIENT zone: public marketing site
│   │   └── src/
│   │       ├── app/           (/, /about, /privacy, /terms, /security,
│   │       │                   robots.txt, sitemap.xml)
│   │       ├── features/landing/
│   │       └── proxy.ts       (security headers — marketing routes only)
│   └── admin/                 ← ADMIN zone: authenticated workspace + PWA
│       └── src/
│           ├── app/           ((public) auth, (protected) workspace, offline,
│           │                   manifest, /api/security/csp-report)
│           ├── components/shell/  (Sidebar, Topbar, MobileBottomNav,
│           │                       CommandPalette, SidebarContext)
│           ├── features/      (admissions, attendance, billing, residents,
│           │                   students, fees, payments, tenants, settings,
│           │                   account, backups, … — 26 domain modules)
│           └── proxy.ts       (security headers — all admin routes)
├── packages/
│   ├── ui/           @hostel/ui           design system (Button, Card, Table,
│   │                                      Modal, toast, ThemeProvider, tokens.css)
│   ├── api/          @hostel/api          fetch client (CSRF, refresh, envelope
│   │                                      unwrap, offline queue), offlineWrite
│   ├── auth/         @hostel/auth         AuthProvider, session store, auth events
│   ├── pwa/          @hostel/pwa          SW registration, IndexedDB outbox,
│   │                                      push, background tasks, PWA components
│   ├── permissions/  @hostel/permissions  RBAC: roles, permissions, route policy,
│   │                                      usePermissions/Guard/AccessDenied
│   ├── hooks/        @hostel/hooks        useApi (declarative fetching)
│   ├── utils/        @hostel/utils        dates, finance, storage, monitoring,
│   │                                      exporters, hostel context
│   ├── types/        @hostel/types        shared base types
│   └── config/       @hostel/config       createSecurityProxy (shared CSP/
│                                          Trusted-Types/isolation headers),
│                                          trusted-types bootstrap
├── e2e/                       Playwright suites (run against both zones)
├── cypress/                   Cypress e2e + component tests
├── scripts/start-zones.mjs    starts both prod servers for tests/lighthouse
├── playwright.config.ts / cypress.config.ts / lighthouserc.js / vitest.config.ts
└── package.json               workspaces + root scripts
```

## Multi-zone routing (URLs are unchanged)

The **client** app owns the public origin. Its `next.config.ts` declares
*fallback rewrites*: any path it does not serve itself is proxied to the
**admin** zone (`ADMIN_ZONE_URL`). Marketing routes always win because
fallback rewrites only run when no client page matched.

- `/`, `/about`, `/privacy`, `/terms`, `/security`, `robots.txt`, `sitemap.xml`
  → client zone.
- `/login`, `/signup`, `/dashboard`, `/students`, … `/sw.js`,
  `/manifest.webmanifest`, `/icons/*`, `/offline` → admin zone via rewrite.
- `/admin` → redirects to `/dashboard` (friendly entry point).

No existing URL changed; the PWA keeps its root scope; backend
CORS/CSRF/`FRONTEND_URL` are untouched in production (the browser only ever
sees one origin).

In production the admin zone builds with `assetPrefix: /admin-static` so its
build assets never collide with the client's `/_next/*` namespace. The service
worker understands both asset paths.

### Ports

| Context | Client zone | Admin zone |
|---|---|---|
| Local dev (`npm run dev:*`) | 3000 | 3001 |
| Docker compose | `FRONTEND_PORT` (3000) | `ADMIN_PORT` (3001, direct access) |
| Tests (playwright/lhci/cypress) | 3100 | 3101 |

In dev, work on the admin app directly at `localhost:3001` (full HMR); the
client zone at `localhost:3000` still proxies admin paths for integration
checks. In containers the client reaches admin at `http://admin:3000`.

> **Standalone/Docker caveat:** rewrites are baked into the routes manifest at
> **build** time, so the client image accepts `ADMIN_ZONE_URL` as a build arg
> (default `http://admin:3000`). Changing topology means rebuilding the client
> image, not just flipping runtime env.

## Shared packages

Packages ship TypeScript source (no build step); apps compile them via
`transpilePackages`. Dependency graph (no cycles at file level):

```
ui ── utils          api ── {auth/store, auth/events, pwa/outbox, utils}
auth ── {api, utils} pwa ── {api, auth/store, config, ui, utils}
hooks ── {ui, utils} permissions ── auth        config, types ── (leaf)
```

`@hostel/auth` and `@hostel/pwa` expose subpath exports (`/store`, `/events`,
`/outbox`, `/synclog`) so the api package can import concrete modules without
pulling React component barrels into its graph.

## RBAC (@hostel/permissions)

- `roles.ts` — role taxonomy (SUPER_ADMIN…GUEST). `normalizeRole()` maps the
  backend's free-form `role` string; **missing/unknown roles normalize to
  OWNER** so no pre-taxonomy account loses access (the backend does not issue
  differentiated roles yet).
- `permissions.ts` — coarse module permissions (`finance:manage`,
  `tenants:manage`, …) + per-role grants; `can(role, permission)`.
- `routePolicy.ts` — admin route prefix → required permission. This single
  table drives **all four** enforcement surfaces: the protected layout
  (renders `AccessDenied` on violation), the Sidebar, the MobileBottomNav and
  the CommandPalette (entries the role can't open are hidden).
- `react.tsx` — `usePermissions()`, `<Guard permission=…>` for
  buttons/sections, `<AccessDenied />`.

Admin code cannot leak into the client bundle by construction — it lives in a
different application.

## Security

Both zones stamp the same strict security header set (per-request CSP nonce +
`strict-dynamic`, Trusted-Types report-only rollout, COOP/COEP/CORP,
Permissions-Policy) via `createSecurityProxy()` from `@hostel/config`; each
app's `src/proxy.ts` keeps only its matcher. **The client matcher is a
positive list of marketing routes** — it must never run on proxied admin
paths, or the document would carry two CSP nonces and every script would be
rejected.

## Testing

- `npm test` — vitest, one project per app + one for packages.
- `npm run e2e` — Playwright; its webServer builds both apps and runs
  `scripts/start-zones.mjs` (client 3100 → admin 3101).
- `npm run lhci` / `npm run cy:ci` — use the same helper.
- `npm run typecheck` / `npm run lint` — workspace-wide.

## Deployment

- **Docker/VPS**: two images (`apps/client/Dockerfile`, `apps/admin/Dockerfile`),
  both built from the `./frontend` context. Compose services: `frontend`
  (client) + `admin`. nginx keeps its single `frontend:3000` upstream — the
  client zone routes internally.
- **Vercel** (current production): **two projects are required**:
  1. *client* — Root Directory `frontend/apps/client`; env
     `ADMIN_ZONE_URL=https://<admin-project-domain>`,
     `NEXT_PUBLIC_API_BASE_URL`. Attach the public domain here.
  2. *admin* — Root Directory `frontend/apps/admin`; env
     `NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_VAPID_PUBLIC_KEY`.
  Both auto-detect the workspace root via the shared lockfile. These are
  dashboard settings and cannot be committed — see the migration report.
