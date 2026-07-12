# Deploying the frontend to Vercel

This is an npm-workspace monorepo with **two Next.js apps** that must deploy as
**two separate Vercel projects** (they own different hostnames):

| App              | Path                 | Role                                          |
| ---------------- | -------------------- | --------------------------------------------- |
| `@hostel/client` | `frontend/apps/client` | Marketing site — owns the public root domain. |
| `@hostel/admin`  | `frontend/apps/admin`  | The application — auth, dashboard, PWA.        |

The client app rewrites every non-marketing path (`/login`, `/dashboard`,
`/sw.js`, …) to the admin zone via `next.config.ts` → `ADMIN_ZONE_URL`, so the
whole product is served under one domain in production.

## Per-app config lives in `apps/<app>/vercel.json`

Each app ships a `vercel.json` pinning the framework, install, and build:

```json
{ "$schema": "https://openapi.vercel.sh/vercel.json", "framework": "nextjs",
  "installCommand": "cd ../.. && npm ci", "buildCommand": "npm run build" }
```

- `installCommand: "cd ../.. && npm ci"` — from the Root Directory (`apps/<app>`)
  step up to the workspace root and do a **clean, complete** install from the
  lockfile. This is REQUIRED: Vercel's default install produced only a partial
  set ("added 86 packages") which made webpack fail to resolve app source under
  `@/features/*` (e.g. `@/features/accounting/components/primitives`) even though
  the files were in the checkout. A clean `npm ci` (what Docker CI and every
  green build do) resolves everything.
- `buildCommand: "npm run build"` runs that app's own script (`next build
  --webpack`) — explicit so a future Turbopack default doesn't change the output
  this app was validated against.

> **`vercel.json` cannot set the Root Directory.** That is a project-level
> dashboard setting and is the single most important part of this setup — see
> below. Without it, Vercel never reads these files.

## Dashboard settings (do this once per project)

Create **two** projects from this repo. For each, in **Settings → Build & Deployment**:

| Setting            | client project             | admin project             |
| ------------------ | -------------------------- | ------------------------- |
| **Root Directory** | `frontend/apps/client`     | `frontend/apps/admin`     |
| Framework Preset   | Next.js (auto)             | Next.js (auto)            |
| Build / Install    | leave default — `vercel.json` + workspace auto-install take over |

With Root Directory set to a workspace member, Vercel detects the workspace root
(`frontend/`, via its `package-lock.json` + `workspaces`) and installs there
automatically. If install ever fails to resolve `@hostel/*`, add to the app's
`vercel.json`: `"installCommand": "cd ../.. && npm ci"`.

Do **not** set `NEXT_OUTPUT_STANDALONE` on Vercel — that flag is Docker-only
(it triggers the standalone copy step the Dockerfiles need and Vercel does not).

## Environment variables

Build-time `NEXT_PUBLIC_*` values are inlined into the browser bundle, so set
them in **Settings → Environment Variables** (Production + Preview) before
building.

**Both projects:**

| Variable                         | Example                              | Notes                                     |
| -------------------------------- | ------------------------------------ | ----------------------------------------- |
| `NEXT_PUBLIC_API_BASE_URL`       | `https://api.yourhost.com/api`       | The Render backend URL the browser calls. |
| `NEXT_PUBLIC_TENANT_BASE_DOMAIN` | `yourhost.com`                       | Wildcard base for workspace subdomains.   |

**admin project also:**

| Variable                       | Notes                                            |
| ------------------------------ | ------------------------------------------------ |
| `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | Web-Push public key (PWA push UI hides if unset). |

**client project also:**

| Variable         | Value                              | Notes                                                     |
| ---------------- | ---------------------------------- | --------------------------------------------------------- |
| `ADMIN_ZONE_URL` | the admin project's production URL | Where the client rewrites app routes (must be the admin deployment, e.g. `https://admin.yourhost.com`). |

See `../docs/PRODUCTION.md` and the deploy topology notes for the full picture.
