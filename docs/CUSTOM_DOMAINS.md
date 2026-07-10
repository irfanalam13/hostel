# Custom Domains, White-Label & Enterprise Branding

Prompt 05 — built on Prompts 01–04 (`MULTI_TENANCY.md`, `AUTHENTICATION.md`,
`WEBSITE_BUILDER.md`, `WORKSPACE_MANAGEMENT.md`). An eligible workspace can
replace its default URL with its own branded domain:

```
https://everest.myhostel.com   →   https://hostel.everest.com
```

while the internal tenant identity (slug, Hostel ID, tokens, data) is
unchanged — same accounts, same sessions, no duplicates.

---

## Architecture

| Concern | Where it lives |
| --- | --- |
| Domain model + verification records | `backend/apps/domains/models.py` (`CustomDomain`) |
| Syntax/platform/wildcard validation | `apps/domains/validators.py` |
| Verification, SSL, activation, plan limits | `apps/domains/services.py` (pluggable `dns_lookup` / `ssl_probe`) |
| Periodic DNS re-validation + cert monitoring | `apps/domains/tasks.py` (Celery beat, daily) |
| Host → tenant resolution | `apps/tenants/middleware.py` + `cache.get_tenant_by_custom_domain` |
| White-label + email/PDF branding | `apps/tenants/workspace_settings.py` (`white_label`) + `apps/tenants/branding.py` |
| Console UI | `frontend/apps/admin/src/features/domains/` → Settings → Custom Domains |

### Domain lifecycle

```
pending ── verify (TXT or CNAME) ──► verified ── activate ──► active (⭑ primary)
   │                                                             │
   └── failed (retryable; auto-retried daily) ◄──────────────────┴── disabled
```

* **Add** — syntax-validated (no protocols/paths/wildcards/IPs; the platform's
  own domain family is rejected), globally unique (one tenant per hostname,
  ever), and **plan-gated**: `CUSTOM_DOMAIN_LIMITS` maps `plan_name → count`
  (default `free:0, basic:1, professional:1, enterprise:3`), fully
  configurable via env.
* **Verify** — the owner adds *either* record, then clicks "Verify now"
  (throttled: `THROTTLE_DOMAIN_VERIFY`, default 20/hour):
  * `TXT  _hostel-verify.<domain>` = `hostel-verify-<random32>`
  * `CNAME <domain>` → `<slug>.<base-domain>`

  Un-propagated DNS produces a friendly retry message; the daily beat task
  also retries automatically. DNS health (`txt`/`cname` booleans + timestamp)
  is stored and shown in the console.
* **Activate** — verified domains start routing (cached lookup, negative
  caching, invalidated on every state change) and become the **primary**
  domain by default. Primary is switchable; at most one per workspace
  (DB constraint). Disable/remove stop routing immediately.

### Routing (same structure as the default workspace)

The tenant middleware resolution order is now: platform subdomain →
**request host as active custom domain** → `X-Workspace` header →
**`X-Tenant-Host` header** (split-topology bridge: the SPA on
`hostel.everest.com` forwards the host it serves to the API on another
origin; the frontend derives it strictly from `window.location`, never
stored state) → legacy headers. `/`, `/login`, `/student`, `/parent`,
`/admin` therefore behave identically on both hosts, and tokens issued on
either host are the same workspace-bound tokens from Prompt 02 — cross-tenant
reuse stays impossible, and cookies are naturally per-origin (no sharing
across unrelated domains).

### Redirects & SEO

`public_url_for(hostel)` returns the primary custom domain when active, else
the workspace URL. It drives:

* **canonical / og:url** on the public site (`generateMetadata`),
* the public payload's `workspace.public_url`,
* email/PDF footers and invite links,
* a **permanent redirect** (Next `permanentRedirect`, HTTP 308 — same
  SEO semantics as 301) from the default host's public homepage to the
  primary domain. Login/portal routes deliberately stay reachable on both
  hosts (the spec requires auth to work from both URLs); search engines
  index only the primary domain via the redirect + canonicals.

### SSL

Certificate **provisioning** is infrastructure-level (Vercel provisions
automatically when the customer domain is attached to the frontend project;
Caddy/certbot on a VPS). The platform's job is transparency: `check_ssl`
performs a real TLS handshake and records status
(`active / expiring ≤21d / expired / pending`) + expiry; the daily task
re-checks every active domain and writes **audit warnings** for missing DNS
records or expiring certificates (never auto-deactivates on a DNS blip).

### White-label

New `white_label` workspace-settings namespace: `enabled`, `platform_name`,
`browser_title`, `footer_text`, `email_sender_name`, `loading_screen_text`,
`hide_platform_branding`. Consumed by:

* the public login-branding endpoint (`/api/tenants/workspaces/public/` now
  returns `white_label` + `public_url`) — login pages/portals present the
  hostel's own system name;
* the public website payload (browser title override, footer);
* `apps/tenants/branding.py`:
  * `email_branding(hostel)` — sender display name, tenant logo/footer and
    the **custom-domain** site URL (the From *address* stays the platform's
    authenticated sender for SPF/DKIM; per-tenant SMTP is the future-ready
    swap point) — already applied to team-invite emails;
  * `pdf_branding(hostel)` — logo, theme colors, business info,
    header/footer for WeasyPrint exports (receipts, fee reports, admission
    forms) — the context every export template renders.

## API summary

All authenticated + audited; reads `workspace.view`, mutations
`workspace.manage`:

| Endpoint | Purpose |
| --- | --- |
| `GET/POST /api/domains/` | list (with workspace/public URL + plan limit) / add |
| `POST /api/domains/{id}/verify/` | DNS ownership check (throttled) |
| `POST /api/domains/{id}/activate/` | activate (+`make_primary`, default true) |
| `POST /api/domains/{id}/primary/` | switch primary |
| `POST /api/domains/{id}/disable/` · `DELETE /api/domains/{id}/` | stop routing / remove |
| `POST /api/domains/{id}/ssl/` | refresh certificate snapshot |
| `GET/PATCH /api/tenants/manage/settings/white_label/` | white-label config (Prompt 04 API) |

## Deployment guide

1. **DNS (customer)**: TXT or CNAME per the console instructions.
2. **Routing (platform)**: attach the customer domain to the frontend host —
   on Vercel, add it to the client-zone project (TLS auto-provisions); on a
   VPS, point nginx/Caddy at the client zone with on-demand TLS.
3. **Django**: include customer domains in `ALLOWED_HOSTS` and
   `CSRF_TRUSTED_ORIGINS` (or front the API with a validating proxy). In the
   split topology this is often unnecessary — the API never sees the customer
   host directly; the SPA bridges it via `X-Tenant-Host`.
4. HTTPS enforcement/HSTS ride the existing production config (SecurityMiddleware
   + edge headers).

## Testing

`apps/domains/tests/test_domains.py` (31 tests, DNS/SSL probes mocked):
validation matrix (incl. wildcard/protocol/platform-domain rejections),
duplicate prevention across tenants, configurable plan limits, TXT + CNAME
verification with retry, activation gating, direct-host and `X-Tenant-Host`
routing, identical login from both hosts, inactive/disabled domains not
routing, exactly-one-tenant mapping, primary switching, SSL status
transitions, the revalidation task's warning behavior, full API flow +
permissions + isolation, and white-label propagation to login branding,
public payload, email and PDF helpers. Frontend: host-classification unit
tests (`isPlatformHost`).

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| "Verification records not found yet" | DNS not propagated (up to 48h) — auto-retried daily, or click Verify now |
| Domain "already connected to a workspace" | assigned to some tenant (possibly yours) — hostnames are globally unique |
| Custom domain 404s after activation | infrastructure routing missing (step 2 above) or lookup cache TTL — state changes invalidate it |
| Default URL doesn't redirect | redirect covers the public homepage only (login/portals stay on both hosts); ISR window is 60s |
| SSL shows "pending" | domain not yet attached at the edge / cert not issued — provisioning is infrastructure-level |
