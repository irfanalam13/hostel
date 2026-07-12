# Workspace Management, Branding & Tenant Administration

Prompt 04 — the owner's console for everything workspace-level. Built on
Prompts 01–03 (`MULTI_TENANCY.md`, `AUTHENTICATION.md`, `WEBSITE_BUILDER.md`).

---

## Architecture

| Concern | Where it lives |
| --- | --- |
| Namespaced settings (schemas + validation) | `backend/apps/tenants/workspace_settings.py` |
| Rename + aliases | `apps/tenants/services.rename_workspace_username`, `models.WorkspaceAlias`, middleware `_alias_redirect`, `cache.get_alias_hostel` |
| Management API | `backend/apps/tenants/manage_views.py` → `/api/tenants/manage/…` |
| Console UI | `frontend/apps/admin/src/features/workspace/` (Settings sections) |

### Settings architecture

All owner configuration lives under `Hostel.settings["workspace"][<namespace>]`
— one JSON document per concern with a schema of defaults in
`WORKSPACE_SETTING_NAMESPACES`:

| Namespace | Contents |
| --- | --- |
| `profile` | legal name, registration, type, established year, description, motto, contacts, social links |
| `business` | business/owner name, PAN/VAT, address (country → postal code), future multiple addresses |
| `regional` | timezone, currency, date/time/number formats, language, first day of week |
| `notifications` | channels (email live; sms/push/whatsapp future-ready) + per-module toggles |
| `security` | password policy, expiry, session/idle timeouts, lockout, login alerts, MFA flag (stored policy; per-knob enforcement lands with its feature) |
| `preferences` | public website, maintenance mode, portals, inquiry, blog/gallery/events/notices toggles |
| `branding` | logo, dark/square logo, favicon, cover, login background, dashboard banner, icon |

Reads overlay stored values on defaults (new keys need no migration); writes
are validated key-by-key (unknown keys rejected, types enforced, nested dicts
merged so partial updates don't wipe siblings, strings capped at 500 chars).
Every update is audit-logged with the changed field list. The frontend
`NamespaceForm` renders inputs straight from the returned defaults — new
backend keys appear in the UI automatically.

**Hostel name vs username**: editing any profile field (including the display
name via the existing workspace API) never touches the workspace username or
URL — permanence is enforced in `Hostel.save()`.

### Branding propagation

`GET /api/tenants/workspaces/public/` (the login-page branding endpoint) now
merges `branding` (logo → dark_logo → login_background) over the raw logo
file, so branding set in the console automatically reaches login pages and
portals. The *public website's* branding stays in the Website Builder
(deliberately separate — a hostel may brand its site differently).

## Workspace rename & redirect strategy

The workspace username stays the permanent tenant identifier; renaming is the
**managed exception** (owner-only, password-confirmed, transactional):

1. Validate + availability-check the new username — aliases count as taken,
   so a retired name can never be claimed by another tenant.
2. Keep the old username as a `WorkspaceAlias` row.
3. Write the new slug via a queryset update (bypassing the permanence guard
   in `save()` — the only code path allowed to).
4. Invalidate tenant + alias cache entries for both names.
5. Audit with old/new.

Requests to the old URL (subdomain or `X-Workspace`) get **HTTP 301** to the
same path on the new workspace URL plus an `X-Workspace-Moved-To` header for
API/SSR clients. Renaming back to one of your own retired names reclaims it
(the alias flips). Alias lookups are Redis-cached with negative caching, so
unknown-subdomain probes stay DB-free.

## Management API

All under `/api/tenants/manage/`, operating on the session's workspace
(isolation inherited from workspace-bound tokens):

| Endpoint | Permission | Purpose |
| --- | --- | --- |
| `GET overview/` | `workspace.view` | identity, status, owner, member/staff/student/parent/resident counts, active users (30d), last login, storage bytes, subscription + trial days, inquiry count |
| `GET/PATCH settings/<namespace>/` | view / `workspace.manage` | namespaced settings (returns `defaults` for schema-driven UIs) |
| `POST rename/` | OWNER + password | username change with 301 aliases |
| `GET activity/?q=&action=&limit=` | `workspace.view` | workspace-scoped audit trail (actor, IP, device, action, result) |
| `GET/POST team/` · `PATCH/DELETE team/<user_id>/` | `accounts.invite` | list/invite members (temp password returned once + emailed best-effort), change roles, remove membership. Guards: no OWNER invites, no self-edit/removal, owner untouchable |
| `POST danger/<action>/` | OWNER + password | `reset_branding`, `reset_theme`, `disable_website`, `archive`, `request_deletion` (soft delete — data always preserved) |
| `GET/POST export/` | OWNER (+ password on import) | export/import all settings namespaces as JSON |

Lifecycle endpoints (activate/suspend/archive/restore/soft-delete) remain on
the Prompt-01 workspace API.

## Preference integration with the public website

`preferences` toggles are enforced server-side in the website public API:

* `enable_public_website: false` → public site 404s (renderer shows the
  offline page) without touching the draft or publish state.
* `enable_online_inquiry: false` → inquiry endpoint 403s **and** the
  published payload flips `show_inquiry_form` off.
* `enable_gallery/events/public_notices: false` → those section types are
  filtered out of the public payload.

## Console UI (Settings)

New/upgraded sections, all registered in the settings registry (nav, search,
breadcrumbs follow automatically): **Workspace Overview** (identity, counts,
storage, subscription, quick actions incl. copy-URL / open website / builder),
**Workspace Profile** (profile + business + regional forms), **Branding**,
**Workspace URL** (current username/URL + owner rename flow reusing the
live availability checker from Prompt 01), **Preferences**, **Team
Management**, **Notifications** and **Security** (upgraded from placeholders),
**Activity Logs** (search), **Danger Zone** (password-gated actions +
settings export). Subscription details surface on the Overview; payment
processing is deliberately out of scope (architecture-ready via the existing
Plan/Subscription models).

## Testing

`apps/tenants/tests/test_workspace_management.py` (21 tests): overview
counts/subscription, settings roundtrip + nested merge + validation +
permission gates + isolation, profile-edit-never-renames, rename (URL change,
301 + moved-to header, password/owner requirements, squatting prevention,
reclaim-own-alias), team invite/role/remove + guards + isolation, activity
scoping + filtering, danger zone password gate + disable-website, settings
export/import roundtrip, preference enforcement (website off, inquiry off,
gallery hidden), branding propagation to the login endpoint.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| Old workspace URL 404s instead of redirecting | alias row missing (rename pre-dates Prompt 04) or alias cache stale — renames invalidate it; TTL bounds staleness |
| "This workspace username is already taken" for an unused name | it's a retired alias of another workspace — permanently reserved |
| Settings PATCH 400 "Unknown settings" | key isn't in the namespace schema — check `GET …/settings/<ns>/` `defaults` |
| Public site suddenly 404 | `preferences.enable_public_website` toggled off (or unpublished via the danger zone) |
| Team invite 403 | caller lacks `accounts.invite` (OWNER/ADMIN/MANAGER by default) |
