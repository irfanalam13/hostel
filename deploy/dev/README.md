# Local development over HTTPS (`https://localhost`)

The default `docker compose up` serves the app over **plain HTTP** on
`:3000` / `:8000`, which is fine for most work. Use this overlay when you need
to exercise behaviour that only matches production over **real TLS on a single
origin**:

- Service Worker registration + update flow, Web Push, offline cache
- `Secure` cookies, `SameSite` enforcement, CSRF over HTTPS
- Strict CSP, Trusted Types, COOP/COEP cross-origin isolation
- Catching mixed-content / hard-coded `http://` bugs **before** they ship

It runs an nginx reverse proxy in front of the existing `web` + `frontend`
containers and terminates TLS with a **locally-trusted mkcert certificate**, so
there are no browser warnings.

```
deploy/dev/
  docker-compose.https.yml   overlay: adds the `nginx_dev` proxy on :443
  nginx/dev.conf             localhost TLS vhost (mirror of the prod vhost)
  certs/                     mkcert-issued localhost.pem + localhost-key.pem (git-ignored)
```

## One-time setup

```bash
# Windows (PowerShell)
pwsh scripts/setup-dev-https.ps1

# macOS / Linux / WSL
bash scripts/setup-dev-https.sh
```

This installs the mkcert local CA into your OS/browser trust store and writes
`localhost.pem` + `localhost-key.pem` into `deploy/dev/certs/`.

## Run

In `.env` (so the browser bundle and CSRF agree on the secure origin):

```dotenv
NEXT_PUBLIC_API_BASE_URL=https://localhost/api
CSRF_TRUSTED_ORIGINS=https://localhost,http://localhost:3000
```

Then:

```bash
docker compose -f docker-compose.yml -f deploy/dev/docker-compose.https.yml up --build
```

Open **https://localhost** (not `:3000`/`:8000`). The plain HTTP redirect is on
`:8443` (host `:80` is frequently occupied on dev machines).

## How it mirrors production

| Concern            | Dev (`deploy/dev`)            | Prod (`deploy/`)                          |
| ------------------ | ----------------------------- | ----------------------------------------- |
| TLS terminator     | `nginx_dev`                   | `nginx`                                   |
| Certificate        | mkcert (local CA)             | Let's Encrypt (see `deploy/certbot`)      |
| Origin             | `https://localhost`           | `https://${DOMAIN}`                       |
| `X-Forwarded-Proto`| set → Django sees `https`     | set → Django sees `https`                 |
| Routing            | `/api /admin /static /media` → backend, `/` → Next.js | identical |

Because the dev vhost is intentionally a near-copy of
`deploy/nginx/templates/app.conf.template`, anything that works here works in
prod — and anything that breaks here (CSP, mixed content, cookie scope) would
have broken in prod too.

## Troubleshooting

See [`docs/HTTPS.md`](../../docs/HTTPS.md) → *Troubleshooting*. The usual ones:

- **`NET::ERR_CERT_AUTHORITY_INVALID`** — re-run the setup script (`mkcert
  -install`), then fully restart the browser. In Firefox, mkcert needs `nss`
  (`certutil`) installed.
- **CSRF 403 on POST** — `https://localhost` must be in `CSRF_TRUSTED_ORIGINS`.
- **API calls still hit `http://localhost:8000`** — rebuild the frontend
  (`--build`); `NEXT_PUBLIC_API_BASE_URL` is inlined at build time.
