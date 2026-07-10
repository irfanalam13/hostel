# Website Builder — Hostel Public Website CMS

Prompt 03 — built on the workspace architecture (`MULTI_TENANCY.md`) and
tenant auth (`AUTHENTICATION.md`). Every hostel automatically receives a
professional, fully editable public website at its workspace URL:

```
https://everest.myhostel.com/        ← public website (this document)
https://everest.myhostel.com/login   ← authenticated system (unchanged)
```

---

## Architecture

| Concern | Where it lives |
| --- | --- |
| Section registry (types, schemas, defaults) | `backend/apps/website/sections.py` |
| Models (draft, sections, versions, inquiries, media) | `backend/apps/website/models.py` |
| Scaffold / publish / rollback / overview | `backend/apps/website/services.py` |
| Admin + public API | `backend/apps/website/views.py` → `/api/website/…` |
| Public renderer (server components) | `frontend/apps/client/src/features/hostel-site/` |
| Host-aware root page | `frontend/apps/client/src/app/page.tsx` |
| Builder UI (Settings → Website Builder) | `frontend/apps/admin/src/features/website/` (`/settings/website`) |

### Draft → Publish → Version model

Editing always happens on the **draft** (`Website` + `WebsiteSection` rows).
**Publish** snapshots the entire draft into an immutable `WebsiteVersion`
(v1, v2, …) and stamps it live; the public endpoint serves **only** the
published snapshot, so half-edited drafts can never leak. **Restore** copies
any version back into the draft for review — publishing again makes it live.
**Unpublish** takes the site offline (draft + history intact).

Every hostel is scaffolded on first access (admin or public): the standard
section set with the hostel's name/phone/address woven in, published as v1 —
the public URL works from day one.

### Section registry

A website is an ordered list of typed sections. Each type in
`SECTION_TYPES` declares a label, a **field schema** (text / textarea / url /
number / boolean / image / list-of-objects), default content, and whether
it's "recommended" (missing ones surface on the overview). Available types:
hero, about, stats, facilities, rooms (with pricing/availability), gallery,
dining, amenities, staff, testimonials, faq, notices, events, downloads,
policies, contact (with map + inquiry form), custom.

**Adding a section type = one registry entry + one renderer component.** The
builder's editor is schema-driven (`SectionForm.tsx` renders inputs straight
from the registry), so new types are instantly editable with zero builder-UI
changes.

### XSS story

Content is plain text stored as JSON, rendered by React (auto-escaped). No
HTML is ever accepted or emitted. Multi-line text renders with
`whitespace-pre-line`. JSON blob sizes and list lengths are capped
server-side; the public payload is bounded.

## Builder UI (Settings → Website Builder)

* **Publish bar** — live/offline state, current version, "unpublished
  changes" indicator, Preview link (workspace URL), Publish / Unpublish.
* **Overview** — status, last published, section counts, missing recommended
  sections, SEO checklist + score, inquiry counts, version count.
* **Sections** — add (type picker), reorder (↑/↓ persisted via
  `sections/reorder/`), hide/show, duplicate, delete, and inline editing via
  the schema-driven form (image fields include validated upload).
* **Theme** — primary/secondary/accent colors (pickers), border radius,
  header style, with a live preview swatch.
* **SEO & Social** — meta title/description/keywords, OG image, canonical,
  robots; branding (logo/favicon/cover); social links (shown only when set).
* **Inquiries** — inbox with new-badge, mark-read, archive.
* **Versions** — history with author/note/date + restore-to-draft.

RBAC: `website.view` (MANAGER+ by default, READ_ONLY read-only),
`website.edit`, `website.publish` — per-workspace overridable like every
other permission.

## Public rendering

The client zone's root page branches on the `x-workspace` request header
(stamped by the edge proxy from the Host header, client-tamper-proof):

* Workspace host → server-side fetch of `/api/website/public/` (ISR,
  `revalidate: 60`) → themed site render. Theme = CSS variables on the root
  wrapper; sections render in owner order; nav/footer/socials from settings.
* Root domain → the platform marketing page, byte-for-byte unchanged.

SEO per tenant: `generateMetadata` emits title/description/keywords/OG/
Twitter/canonical/robots from the published snapshot, plus a
`LodgingBusiness` JSON-LD block. Unavailable sites are `noindex`.
Performance: server-rendered HTML, ISR caching, `loading="lazy"` images,
no client JS except the inquiry form.

## Inquiries

Public `POST /api/website/public/inquiries/`: name + message required, email
or phone required, throttled per-IP (`THROTTLE_WEBSITE_INQUIRY`, default
5/hour), **honeypot** field (`website`) silently drops bots with the same
201 response (no oracle), IP recorded, audited. Stored tenant-scoped; the
admin inbox lives in the builder's Inquiries tab.

## Media

`POST /api/website/media/` (multipart): images (jpg/png/webp/gif — must
fully parse via Pillow, so renamed scripts/polyglots are rejected) and PDFs
(`%PDF-` header check), size-capped by `MAX_UPLOAD_SIZE_MB`. Stored under a
tenant-prefixed path (`website/<hostel_id>/…`).

## API summary

| Endpoint | Auth | Purpose |
| --- | --- | --- |
| `GET /api/website/public/` | public (workspace-resolved) | published snapshot |
| `POST /api/website/public/inquiries/` | public, throttled | inquiry form |
| `GET/PATCH /api/website/settings/` | `website.view` / `.edit` | draft + theme/seo/branding/nav/footer/social + section registry |
| `GET /api/website/overview/` | `website.view` | dashboard numbers |
| `…/sections/` CRUD + `reorder/` + `{id}/duplicate/` | `website.edit` | section management |
| `POST /api/website/publish/` · `unpublish/` | `website.publish` | go live / offline |
| `GET /api/website/versions/` · `POST …/{n}/restore/` | view / publish | history + rollback |
| `GET/PATCH /api/website/inquiries/` | `website.view` | admin inbox |
| `GET/POST/DELETE /api/website/media/` | `website.edit` | asset uploads |

## Tenant isolation

Sections/versions/inquiries/media all FK to the tenant; admin queries filter
on `request.hostel` (workspace-bound tokens from Prompt 02 make cross-tenant
requests 401 outright); public payloads are built from the resolved
workspace only; media paths are tenant-prefixed. Covered by dedicated
isolation tests.

## Deployment notes

* **Docker/dev**: SSR fetches use `API_INTERNAL_URL=http://web:8000/api`
  (service-internal) — the browser-facing `NEXT_PUBLIC_API_BASE_URL` points
  at the wrong container from inside the compose network.
* **Vercel + Render**: no `API_INTERNAL_URL` needed (the public API URL is
  reachable server-side). Wildcard domain setup per `MULTI_TENANCY.md`.
* Publishes appear on the public site within the ISR window (60s).

## Testing

`backend/apps/website/tests/test_website.py` (20 tests): auto-scaffold,
draft-never-leaks, publish/unpublish, version history + rollback, section
add/hide/duplicate/reorder/delete + validation, hidden-section exclusion,
theme/SEO flow, tenant isolation (admin + public), RBAC (staff blocked,
manager allowed), inquiry storage/honeypot/validation/isolation, media
validation (fake image, fake PDF, unknown types), overview.

## Troubleshooting

| Symptom | Cause |
| --- | --- |
| Public site shows "Temporarily unavailable" in Docker | frontend container can't reach the API — check `API_INTERNAL_URL` |
| Edits not visible on the public site | they're on the draft — Publish; then allow up to 60s ISR |
| "Missing sections" on overview | a recommended type isn't on the page — add it from the Sections tab |
| Image upload rejected | not a real image/PDF or over `MAX_UPLOAD_SIZE_MB` |
| Inquiry form 429 | per-IP throttle (`THROTTLE_WEBSITE_INQUIRY`, default 5/hour) |
