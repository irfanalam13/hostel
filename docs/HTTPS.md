# HTTPS / TLS architecture & operations

How the Hostel SaaS serves everything over HTTPS — in local development and in
production — plus the theory, the cert options, the header model, a testing
checklist, and a troubleshooting guide.

> **TL;DR for operators**
> - **Dev:** `pwsh scripts/setup-dev-https.ps1` → `docker compose -f docker-compose.yml -f deploy/dev/docker-compose.https.yml up --build` → open `https://localhost`.
> - **Prod:** put `DOMAIN`/`CERTBOT_EMAIL` in `deploy/.env` → `cd deploy && ./certbot/init-letsencrypt.sh` → add `renew.sh` to cron.
> - TLS is terminated by **nginx**; the apps (Django + Next.js) speak plain HTTP behind it and learn the real scheme from `X-Forwarded-Proto`.

---

## 1. Architecture

TLS is terminated at a single **nginx reverse proxy** that fronts both the
Django backend (Gunicorn + WhiteNoise, `web:8000`) and the Next.js frontend
(`frontend:3000`). The browser only ever speaks HTTPS to nginx; the
proxy→app hop is plain HTTP on a private Docker network.

```
                          ┌────────────────────── Docker network (private) ──────────────────────┐
                          │                                                                       │
  Browser ──HTTPS/443──▶ nginx ──HTTP──▶  web:8000  (Django/Gunicorn: /api /admin /health /static /media)
   (TLS)   ──HTTP/80──▶  (TLS term)  ─┐                                                            │
            301 → https              └─HTTP──▶ frontend:3000  (Next.js: everything else)           │
                          │                                                                       │
                          └───────────────────────────────────────────────────────────────────────┘

  X-Forwarded-Proto: https   ──▶  Django SECURE_PROXY_SSL_HEADER  ──▶  request.is_secure() == True
```

Why terminate at the edge (and not in Django/Next directly)?

- **One place to manage certs, ciphers, OCSP, HSTS** — the apps stay
  scheme-agnostic and portable (the same images run on Render, which terminates
  TLS at *its* edge).
- **Performance** — HTTP/2, gzip, keep-alive to upstreams, TLS session reuse all
  live in nginx.
- **Security** — rate limiting and a hardened TLS profile are enforced before a
  request ever reaches application code.

| | **Development** | **Production / staging** |
|---|---|---|
| Proxy | `nginx_dev` (`deploy/dev/`) | `nginx` (`deploy/docker-compose.prod.yml`) |
| Cert | mkcert local CA | Let's Encrypt (`deploy/certbot/`) |
| Origin | `https://localhost` | `https://${DOMAIN}` |
| Config | `deploy/dev/nginx/dev.conf` | `deploy/nginx/templates/app.conf.template` + `snippets/` |
| Renewal | n/a (regenerate) | cron → `deploy/certbot/renew.sh` |

The dev vhost is a deliberate near-copy of the prod vhost, so a mixed-content /
cookie / CSP bug that would bite in prod also bites in dev.

---

## 2. HTTP vs HTTPS, TLS, and the certificate chain

**HTTP** is plaintext: anyone on the path (café Wi‑Fi, ISP, a compromised
router) can read or modify it. **HTTPS** is HTTP carried inside a **TLS** tunnel
that provides three guarantees:

1. **Confidentiality** — traffic is encrypted.
2. **Integrity** — tampering is detected.
3. **Authenticity** — you're really talking to `app.yourdomain.com`, not a
   man-in-the-middle.

> *SSL* is the obsolete predecessor of *TLS*. Everyone says "SSL cert" but every
> modern connection is **TLS** (we allow only TLS 1.2 and 1.3).

### The TLS 1.3 handshake (simplified)

```
  Client                                                 Server (nginx)
    │  ClientHello  (TLS versions, cipher suites,            │
    │               supported curves, key share) ──────────▶│
    │                                                        │  picks TLS1.3 + a cipher,
    │                                                        │  generates its key share
    │◀───── ServerHello (key share) + Certificate +          │
    │        CertificateVerify (signs the handshake) +       │
    │        Finished                                        │
    │                                                        │
    │  [both derive the same session keys via ECDHE]         │
    │                                                        │
    │──────────────── Finished ─────────────────────────────▶│
    │                                                        │
    │════════════ encrypted application data ════════════════│
```

**ECDHE** key exchange gives **Perfect Forward Secrecy (PFS)**: the session key
is ephemeral, so even if the server's private key leaks later, *past* recorded
traffic stays unreadable. Our cipher list (`deploy/nginx/snippets/ssl.conf`) is
ECDHE-only for exactly this reason.

### Certificate chain & browser verification

A server doesn't present one certificate — it presents a **chain** the browser
walks up to a trust anchor it already has:

```
  ┌─────────────────────┐   issued/signed by   ┌──────────────────────┐   signed by   ┌──────────────┐
  │  Leaf cert          │ ───────────────────▶ │ Intermediate CA      │ ────────────▶ │  Root CA     │
  │  CN=app.domain.com  │                       │ (e.g. Let's Encrypt  │               │ (in OS/browser
  │  (your server)      │                       │  R11 / E5)           │               │  trust store)│
  └─────────────────────┘                       └──────────────────────┘               └──────────────┘
        fullchain.pem  =  leaf  +  intermediate(s)            privkey.pem = the leaf's private key
```

The browser verifies, top-down: signatures chain validly up to a **trusted
root**, the leaf's name matches the host, the cert is in its validity window and
not revoked (**OCSP** — we *staple* the response so the client needn't ask the
CA itself), and the server proves it holds the matching private key
(`CertificateVerify`). Any failure → the `NET::ERR_CERT_*` warning page.

- **`fullchain.pem`** — leaf + intermediates, in order. This is what nginx
  serves (`ssl_certificate`).
- **`privkey.pem`** — the leaf's private key (`ssl_certificate_key`). Secret;
  `0600`, never committed.
- **mkcert** makes your machine trust a *local* root CA, so its leaf certs are
  trusted only on your machine — perfect for dev, useless for the public.

---

## 3. Certificate options

| Option | Best for | Trusted by browsers? | Cost | Renewal | Notes |
|---|---|---|---|---|---|
| **mkcert** | Local dev | Only on machines with its local CA | Free | Re-run script | Zero-warning `https://localhost`. Never use in prod. |
| **OpenSSL self-signed** | Throwaway/CI | No (warns) | Free | Manual | We use it only to *bootstrap* nginx before LE issues (`init-letsencrypt.sh`). |
| **Let's Encrypt** | Most production | Yes | Free | **Auto, 90-day** | What `deploy/certbot/` automates. Rate-limited — test with `STAGING=1`. |
| **Cloudflare Origin CA** | Behind Cloudflare proxy | Only by Cloudflare (not public) | Free | 15-year | Use with CF SSL mode **Full (strict)**. CF↔origin only; public sees CF's edge cert. |
| **Commercial (DigiCert, …)** | EV/OV, compliance | Yes | $$ | Manual/1yr | Buys OV/EV badging + support/warranty; technically no stronger than LE DV. |

This repo implements **mkcert** (dev) and **Let's Encrypt** (prod). To swap in a
Cloudflare Origin or commercial cert, just drop `fullchain.pem` + `privkey.pem`
into `deploy/nginx/certs/` and reload nginx — nothing else changes.

---

## 4. Security headers — who owns which

Headers are split by concern so no response ever carries a duplicate or
conflicting header. **This is deliberate — do not re-add app headers at nginx.**

| Header | Set by | Where | Purpose |
|---|---|---|---|
| `Strict-Transport-Security` (HSTS) | **nginx (edge)** | `deploy/nginx/snippets/security-headers.conf` | Force HTTPS for 2y incl. subdomains + preload. Edge owns it because Next.js *documents* don't set it. Set `SECURE_HSTS_SECONDS=0` so Django doesn't double it. |
| `Content-Security-Policy` (nonce + `strict-dynamic`) | **Next.js** | `frontend/packages/config/src/securityProxy.ts (each app: frontend/apps/*/src/proxy.ts)` | Per-request nonce CSP; blocks inline/XSS script. Also Report-Only with Trusted Types. |
| `Content-Security-Policy` (API/admin) | **Django** | `apps.common.middleware.SecurityHeadersMiddleware` | CSP for non-Next responses. |
| `Trusted-Types` / `require-trusted-types-for` | Next.js | `middleware.ts` | DOM-XSS sink guard (Report-Only → enforce via `CSP_TT_ENFORCE=1`). |
| `X-Frame-Options: DENY` | Next.js + Django | `middleware.ts`, settings `X_FRAME_OPTIONS` | Clickjacking. (CSP `frame-ancestors 'none'` is the modern equivalent.) |
| `X-Content-Type-Options: nosniff` | Next.js + Django + asset routes | `middleware.ts`, `next.config.ts`, settings | Stop MIME sniffing. |
| `Referrer-Policy` | Next.js + Django | `middleware.ts`, settings | Limit referrer leakage. |
| `Permissions-Policy` | Next.js | `middleware.ts` | Deny every powerful feature the app doesn't use. |
| `Cross-Origin-Opener/Embedder/Resource-Policy` | Next.js | `middleware.ts`, `next.config.ts` | Cross-origin isolation. |
| `upgrade-insecure-requests` | Next.js (prod) | `middleware.ts` | Auto-upgrade any stray `http://` subresource → `https://` (mixed-content backstop). |

**The HSTS rule of thumb:** it's a *transport* header (about the connection), so
it belongs at the TLS terminator. CSP/XFO/etc. are *content* headers tied to a
specific response body, so the app that generates the body owns them.

### Cookies & auth

Auth is httpOnly-cookie JWT (`apps/accounts`, see `config/settings.py`):

- `JWT_COOKIE_SECURE` = `not DEBUG` → `Secure` flag in prod (cookie only sent
  over HTTPS). Over `https://localhost` in dev it's also fine.
- `SESSION_COOKIE_HTTPONLY=True`, `JWT_AUTH_COOKIE` httpOnly → not readable by JS
  (XSS can't exfiltrate the token).
- `CSRF_COOKIE_HTTPONLY=False` *by design* — the SPA must read it to echo
  `X-CSRFToken`.
- `SameSite=Lax` default; refresh-token rotation + blacklist
  (`ROTATE_REFRESH_TOKENS`, `BLACKLIST_AFTER_ROTATION`).
- Brute force: `django-axes` (5 failures → 15-min lockout) **and** nginx
  `limit_req zone=auth` (see §6).

---

## 5. Rate limiting (defence in depth)

Two independent layers:

1. **nginx** (`app.conf.template`) — per-IP, before app code runs:
   - `zone=auth` `5r/m` (burst 10) on `^/api/auth/(login|token|signup|password)`
     — credential-stuffing guard.
   - `zone=api` `20r/s` (burst 40) on `^/(api|admin)/`.
   - `health`, `static`, `media` are unthrottled.
2. **DRF** (`REST_FRAMEWORK.DEFAULT_THROTTLE_RATES`) — per-user/scope:
   `anon 60/min`, `user 1000/h`, `auth 5/min`, plus scoped buckets (`signup`,
   `password_reset`, `payment`, …).

nginx catches volumetric abuse cheaply; DRF enforces business-aware limits.

---

## 6. WebSockets / `wss://` (future — not currently used)

**There are no WebSockets in the codebase today** — no `channels`/Daphne, no
`new WebSocket()` in the frontend. Gunicorn (WSGI) serves everything. Real-time
push is done with **Web Push (VAPID)**, not sockets. So there is nothing to
convert to `wss://` right now.

When you *do* add Django Channels, HTTPS-readiness is already 90% there. The
checklist:

1. **Backend**: add `channels` + `channels-redis`, define `config/asgi.py` with a
   `ProtocolTypeRouter`, run **Daphne/Uvicorn** (ASGI) instead of (or alongside)
   Gunicorn, and point the channel layer at the existing Redis.
2. **nginx**: add a location that upgrades the connection (this is exactly the
   shape of the HMR block already in `deploy/dev/nginx/dev.conf`):

   ```nginx
   upstream ws_backend { server web:8001; }   # Daphne

   location /ws/ {
       proxy_pass http://ws_backend;
       proxy_http_version 1.1;
       proxy_set_header Upgrade    $http_upgrade;     # ← the WebSocket upgrade
       proxy_set_header Connection "upgrade";
       proxy_set_header Host       $host;
       proxy_set_header X-Forwarded-Proto $scheme;
       proxy_read_timeout 3600s;                      # long-lived sockets
   }
   ```

   Because the page is served over TLS, the browser **must** use `wss://`
   (`ws://` from an HTTPS page is mixed content and blocked). The CSP already
   permits it in dev (`connect-src … ws: wss:`); for prod add your `wss://${DOMAIN}`
   origin to `connect-src` in `frontend/packages/config/src/securityProxy.ts (each app: frontend/apps/*/src/proxy.ts)`.
3. **Frontend**: derive the socket URL from the page origin so it's automatically
   `wss` in prod / `ws` in dev:
   `const url = location.origin.replace(/^http/, "ws") + "/ws/..."`.

No code is shipped for this — it's documented so the wiring is ready.

## 7. OAuth / social login (future — not currently used)

There is **no OAuth/Google/Microsoft login** in the codebase (auth is
username/password → httpOnly-cookie JWT). When added, the only HTTPS-specific
requirements are: register **HTTPS-only** redirect URIs
(`https://${DOMAIN}/api/auth/callback/...`), keep client secrets server-side
(never in the Next.js bundle), and ensure the OAuth state cookie is
`Secure` + `SameSite=Lax`. No proxy changes needed.

---

## 8. Testing checklist

Run after any TLS/proxy/header change.

**TLS / certificate**
- [ ] `curl -sI https://$DOMAIN` returns `200` and a `strict-transport-security` header.
- [ ] `curl -sI http://$DOMAIN` returns `301` to `https://`.
- [ ] `echo | openssl s_client -connect $DOMAIN:443 -servername $DOMAIN` shows the full chain + `Verify return code: 0 (ok)`.
- [ ] TLS 1.0/1.1 refused: `openssl s_client -tls1_1 -connect $DOMAIN:443` fails.
- [ ] OCSP stapled: `openssl s_client -connect $DOMAIN:443 -status | grep -A2 "OCSP Response"`.
- [ ] [SSL Labs](https://www.ssllabs.com/ssltest/) grade **A/A+** (or `testssl.sh $DOMAIN`).

**HTTP/2 & redirect**
- [ ] `curl -sI --http2 https://$DOMAIN | grep -i "HTTP/2"`.
- [ ] Redirect is `301` (permanent), not `302`.

**Headers**
- [ ] Exactly **one** `Content-Security-Policy` per response (no duplicates).
- [ ] Exactly **one** `Strict-Transport-Security` (set `SECURE_HSTS_SECONDS=0` if you see two).
- [ ] `securityheaders.com` grade A.

**App / mixed content**
- [ ] DevTools Console shows **no** "Mixed Content" warnings on any page.
- [ ] Login sets `Secure; HttpOnly` cookies (DevTools → Application → Cookies).
- [ ] Media/PDF/image uploads load over `https://`.
- [ ] PWA installs; service worker registers; offline mode works (SW requires a secure context).
- [ ] `/admin/` reachable only over HTTPS.

**Rate limiting**
- [ ] 30 rapid `POST /api/auth/login/` → some `429`s.

The existing E2E/security CI (`.github/workflows/e2e.yml`, `security.yml`, ZAP)
covers much of the app-layer checks — see `TESTING.md`.

---

## 9. Monitoring

- **Cert expiry**: the blackbox exporter (`monitoring/blackbox/`) probes the
  public URL; alert on `probe_ssl_earliest_cert_expiry - time() < 14*24*3600`
  (14 days). Add to `monitoring/prometheus/alerts.yml`.
- **Renewal**: `renew.sh` logs to `/var/log/certbot-renew.log`; alert if the file
  is stale (cron didn't run) or contains `error`.
- **Handshake health**: blackbox `http_2xx` module with `tls: true` flags
  expired/misconfigured certs as probe failures.
- **Quick manual check**:
  ```bash
  echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null \
    | openssl x509 -noout -enddate
  ```

---

## 10. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `NET::ERR_CERT_AUTHORITY_INVALID` (dev) | mkcert CA not trusted / not installed | Re-run `setup-dev-https.*` (`mkcert -install`), restart browser. Firefox needs `nss`/`certutil`. |
| `NET::ERR_CERT_AUTHORITY_INVALID` (prod) | Using LE **staging** cert, or chain missing | Re-issue without `STAGING=1`; ensure nginx serves **`fullchain.pem`** (not just the leaf). |
| **Mixed Content** blocked | A hard-coded `http://` URL or absolute asset | Use relative URLs / `NEXT_PUBLIC_API_BASE_URL=https://…`; `upgrade-insecure-requests` is a backstop, not a cure. |
| `ERR_TOO_MANY_REDIRECTS` | Redirect loop: nginx → https, but app also redirects, or `X-Forwarded-Proto` not seen | Confirm `proxy.conf` sets `X-Forwarded-Proto $scheme` and Django has `SECURE_PROXY_SSL_HEADER`. Don't set `SECURE_SSL_REDIRECT` *and* terminate elsewhere without the forwarded header. |
| `SSL_ERROR_NO_CYPHER_OVERLAP` / handshake failed | Client too old for TLS1.2+ / curve mismatch | Expected for ancient clients. Verify `ssl_protocols`/`ssl_ciphers` in `snippets/ssl.conf`. |
| Cert expired | Renewal cron not running | Check `/var/log/certbot-renew.log`; run `./certbot/renew.sh` manually; verify cron + ports 80/443 open. |
| **502 Bad Gateway** | `web`/`frontend` upstream down/unhealthy | `docker compose ps`; check app healthchecks/logs. nginx `upstream` names must match service names. |
| **504 Gateway Timeout** | Slow upstream > `proxy_read_timeout` | Inspect the slow endpoint; raise the timeout in `proxy.conf` only if legitimately needed. |
| WebSocket fails to connect | (Future) missing upgrade headers or `ws://` from HTTPS | Use `wss://`; add the upgrade `location` from §6; allow `wss:` in CSP `connect-src`. |
| **CORS** error in browser | Frontend origin not allow-listed | Add the origin to `CORS_ALLOWED_ORIGINS`. With the single-origin proxy, API calls are same-origin and need no CORS. |
| Cookies not sent / CSRF 403 | `Secure` cookie over HTTP, or origin not in `CSRF_TRUSTED_ORIGINS` | Use HTTPS; add the exact scheme+host (e.g. `https://localhost`) to `CSRF_TRUSTED_ORIGINS`. |
| HSTS "stuck" on HTTP after switching | Browser cached HSTS; or testing on a preloaded domain | Clear HSTS at `chrome://net-internals/#hsts`; never enable `preload` until you're committed to HTTPS-forever. |
| OCSP stapling not working | No resolver / cert has no OCSP URL | Confirm `resolver` in `ssl.conf`; private CAs have no OCSP — harmless. |
| nginx won't start: "cannot load certificate" | Cert files missing at `/etc/nginx/certs` | Dev: run the mkcert script. Prod: run `init-letsencrypt.sh` (it bootstraps a temp cert first). |

---

## 11. Prompt coverage map

The original "convert HTTP→HTTPS" brief had 30+ parts. Status against this repo:

| Area | Status | Where |
|---|---|---|
| HTTPS architecture / TLS / chain | ✅ Documented | §1–2 |
| Folder structure | ✅ | `deploy/{nginx,dev,certbot}/` |
| Cert options (mkcert/LE/CF/commercial) | ✅ | §3 |
| Dev HTTPS (mkcert, Win/Mac/Linux) | ✅ **Added** | `scripts/setup-dev-https.*`, `deploy/dev/` |
| Local certs explained | ✅ | §2, `deploy/dev/README.md` |
| Docker config (volumes, certs, ports, healthchecks) | ✅ | compose files |
| Nginx (HTTP/2, TLS1.2/1.3, PFS, OCSP, sessions, gzip, proxy) | ✅ **Hardened** | `deploy/nginx/` |
| HTTP→HTTPS 301 redirect | ✅ | `app.conf.template`, `dev.conf` |
| Security headers | ✅ | §4 |
| Django SSL/HSTS/cookies/CORS/CSRF | ✅ Pre-existing | `config/settings.py` |
| Next.js env / config | ✅ | `next.config.ts`, `.env*` |
| Env vars (.env / prod / local) | ✅ | `.env.example`, `deploy/.env.prod.example` |
| API over HTTPS (axios/fetch/SSR) | ✅ | single-origin via `NEXT_PUBLIC_API_BASE_URL` |
| WebSocket / `wss://` | ⚠️ **N/A today** — documented for future | §6 |
| Auth (JWT/cookies/refresh) | ✅ | §4, `apps/accounts` |
| OAuth / social login | ⚠️ **N/A today** — documented for future | §7 |
| CORS / CSRF / trusted origins | ✅ | `config/settings.py`, §10 |
| PWA / SW / push over HTTPS | ✅ Pre-existing | secure context required (see `TESTING.md`) |
| Mixed-content scan/fix | ✅ | `upgrade-insecure-requests` + dev mirror catches it; §8 |
| Uploads (media/PDF/img) over HTTPS | ✅ | nginx `^/media/` route |
| Admin panel HTTPS-only | ✅ | `^/admin/` behind TLS + redirect |
| Cookies (Secure/HttpOnly/SameSite/rotation) | ✅ | §4 |
| Rate limiting (nginx + Django) | ✅ **Added (nginx)** | §5 |
| Hardening (clickjack/MITM/XSS/CSRF/smuggling/TLS) | ✅ | §4–5, `SECURITY.md` |
| Performance (HTTP/2, gzip, keep-alive, TLS reuse, caching) | ✅ | `app.conf.template`, `ssl.conf` |
| Let's Encrypt (certbot, auto-renew, cron, zero-downtime) | ✅ **Added** | `deploy/certbot/` |
| Cloudflare (optional) | ✅ Documented | §3 |
| CI/CD (deploy, cert validation, HTTPS verify) | ✅ Pre-existing | `.github/workflows/`, `deploy/deploy.sh` |
| Testing checklist | ✅ | §8 |
| Monitoring (expiry, alerting, Prometheus/Grafana) | ✅ | §9, `monitoring/` |
| Troubleshooting guide | ✅ | §10 |

See also: [`deploy/README.md`](../deploy/README.md),
[`deploy/dev/README.md`](../deploy/dev/README.md),
[`deploy/certbot/README.md`](../deploy/certbot/README.md),
[`SECURITY.md`](../SECURITY.md).
