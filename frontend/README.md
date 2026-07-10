# Hostel SaaS — Frontend Monorepo

Two Next.js applications composed as multi-zones on one origin, plus shared
workspace packages. Full details: [ARCHITECTURE.md](./ARCHITECTURE.md) ·
migration report: [Documentation/MIGRATION-ADMIN-SPLIT.md](./Documentation/MIGRATION-ADMIN-SPLIT.md).

```
apps/client      public marketing site   → http://localhost:3000
apps/admin       admin workspace + PWA   → http://localhost:3001
packages/*       @hostel/ui · api · auth · pwa · permissions · hooks · utils · types · config
```

The client zone proxies every non-marketing path to the admin zone, so
`localhost:3000` serves the entire product; `localhost:3001` gives direct
(full-HMR) access to the admin app while developing it.

## Commands (run from this directory)

```bash
npm install            # one install for the whole workspace
npm run dev:admin      # admin app dev server (:3001)
npm run dev:client     # client app dev server (:3000, proxies admin)
npm run build          # production build of both apps
npm run typecheck      # tsc for both apps (packages checked transitively)
npm run lint           # eslint across the workspace
npm test               # vitest (admin / client / packages projects)
npm run e2e            # Playwright — builds & starts both zones itself
npm run lhci           # Lighthouse CI (expects apps already built)
npm run cy:ci          # Cypress against both zones (expects built apps)
```

Docker development (from the repo root): `docker compose up -d --build` —
services `frontend` (client zone) and `admin`.
