# Local development behind the single-origin Nginx gateway

The default `docker compose up` now fronts the whole multi-zone app with an
**Nginx reverse proxy on one origin** — `http://localhost` — exactly like
production. Open **`http://localhost`**, not `:3000` / `:3001`.

```
                         http://localhost   (ONE browser origin)
                                 │
                              ┌──┴──┐
                              │nginx│  deploy/dev/nginx/gateway.conf
                              └──┬──┘
      ┌───────────────┬─────────┼──────────────┬───────────────────┐
      ▼               ▼         ▼               ▼                   ▼
   /  /about       /login    /_next/       /admin-static/     /api  /admin/
   /privacy        /signup   (client       (admin chunks      /static /media
   /terms          /dashboard chunks, HMR,  + admin HMR)       /health
   /security       …(all else) image opt.)
      │               │         │               │                   │
      ▼               ▼         ▼               ▼                   ▼
   client:3000     admin:3000  client:3000    admin:3000          web:8000
   (marketing)     (workspace)                                    (Django)
```

## Why a gateway

Previously the **client** Next.js dev server reverse-proxied the **admin** dev
server for `/login`, `/signup`, `/dashboard`, … One Next dev server proxying
another mangles the inner app's Turbopack runtime and HMR, so admin pages
rendered but never **hydrated** — forms fell back to native GET submits and the
screen looked stuck / "infinitely refreshing".

With the gateway, every path goes **directly** to the correct dev server on a
single origin. Both zones hydrate on their own, there's no cross-origin
navigation, no CORS (the API is same-origin `/api`), and cookies behave exactly
as they will in production.

## Run it

```bash
docker compose up            # gateway + both zones + Django + Redis
# then open:
http://localhost
```

That's it — the `nginx` service is part of `docker-compose.override.yml`, and the
override points the browser bundle at the same-origin `/api` and trusts the
`http://localhost` origin for CSRF.

- **Port 80 already taken?** Set `GATEWAY_PORT` (e.g. `GATEWAY_PORT=8080`) in
  `.env` and open `http://localhost:8080`.
- **Want a prod-like hostname?** Add `127.0.0.1 hostel.local` to your hosts file
  and open `http://hostel.local` (already CSRF-trusted / in `ALLOWED_HOSTS`).
- **Direct-port debugging** (`http://localhost:3000` / `:3001`) still works for
  inspecting a single zone, but API calls and cross-zone links only work through
  the gateway.

## How it maps to production

| Concern            | Dev gateway (`deploy/dev/nginx/gateway.conf`) | Prod (`deploy/nginx/…app.conf.template`) |
| ------------------ | --------------------------------------------- | ---------------------------------------- |
| Entry point        | `nginx` on `http://localhost`                 | `nginx` on `https://${DOMAIN}`           |
| `/` + marketing    | → client zone                                 | → client zone                            |
| everything else    | → admin zone (direct)                         | → client zone → edge-rewrite → admin     |
| `/api /admin/ /static /media /health` | → Django                     | → Django                                 |
| admin assets       | `/admin-static/*` (assetPrefix)               | `/admin-static/*` (assetPrefix)          |
| API from browser   | same-origin `/api` (no CORS)                  | same-origin `/api` (no CORS)             |

The one intentional dev/prod difference is **TLS**: this gateway is plain HTTP
(so `Secure` cookies, HSTS and `upgrade-insecure-requests` are off, which is
correct for `http://`). When you specifically need to exercise TLS-only
behaviour (Service Worker/push, `Secure` cookies, COOP/COEP), use the HTTPS
overlay in [`README.md`](./README.md) instead.

## The `/_next` collision (why admin has `assetPrefix`)

Two Next.js dev servers can't both own `/_next/*` on one origin. Production
already gives the admin zone `assetPrefix: "/admin-static"`; we now enable that
in **dev too** (`apps/admin/next.config.ts`). So:

- `/_next/*` → **client** (its chunks, its HMR socket, and the image optimizer
  `/_next/image`, which Next does not assetPrefix — served for both zones, as in
  prod).
- `/admin-static/*` → **admin** (its chunks, and its HMR socket at
  `/admin-static/_next/webpack-hmr` — the dev server derives the HMR path from
  `assetPrefix`).

## HMR

Both dev servers' Fast-Refresh websockets pass through the gateway:

- client HMR → `ws://localhost/_next/webpack-hmr` → client
- admin HMR  → `ws://localhost/admin-static/_next/webpack-hmr` → admin

The gateway sets `Upgrade`/`Connection` on every location (via a
`map $http_upgrade`) so websockets and pooled keep-alive HTTP both work.

## Troubleshooting

- **`bind: address already in use` on :80** — set `GATEWAY_PORT`.
- **CSRF 403 on POST** — the origin you opened must be in `CSRF_TRUSTED_ORIGINS`
  (`web` service env in the override already lists localhost / hostel.local).
- **A page renders but is dead / not interactive** — you likely opened a zone on
  its raw port; open `http://localhost` (the gateway) instead.
- **Changed `next.config.ts`** — restart that zone's container; Next does not
  hot-reload its own config (`docker compose restart admin` / `frontend`).
