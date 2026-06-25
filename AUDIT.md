# Hostel Management System — Production Audit Report

**Date:** 2026-06-14
**Stack:** Django + DRF (backend, 20 apps) · Next.js 16 / React 19 / Tailwind 4 (frontend) · SQLite (dev) / Postgres (prod) · Celery + Redis
**Method:** Full read of backend models/views/serializers/settings/middleware/permissions and frontend routes/api-client, followed by manual verification of every Critical claim against source.

> **Note on severity.** Several findings surfaced by automated scanning were **overstated**. Where I verified the actual code and found the real risk to be lower (or already mitigated), the item is marked **[verified — downgraded]** with the reason. The audit is deliberately honest rather than alarmist.

---

## 0. Verification corrections (read first)

| Claimed | Verified reality | Verdict |
|---|---|---|
| Critical: `X-HOSTEL-ID`/`X-HOSTEL-CODE` header lets users read other tenants' data | `HasHostelContext.has_permission` calls `user_is_hostel_member()` for authenticated users (`common/permissions.py:39-40`); middleware resolution is backstopped at the permission layer | **Downgraded → Medium** (verify every viewset actually uses `HasHostelContext`; harden middleware as defence-in-depth) |
| Critical: bed double-booking via race condition | DB has `unique_active_assignment_per_bed` + `unique_active_assignment_per_student` partial unique constraints (`rooms/models.py:64-75`) — corruption is impossible; concurrent approval yields a 500 instead of a clean 409 | **Downgraded → High** (robustness/UX, not integrity) |
| Critical: duplicate `Room`/`Bed` models | **Confirmed real.** Two parallel domains exist (see §1). Needs a product decision, not a blind delete. | **Confirmed → Critical (decision required)** |

---

## 1. ARCHITECTURE — the central issue: two parallel domains

The codebase contains **two overlapping implementations** of the same concept, wired to different tables:

| Concern | Track A ("residents") | Track B ("students") |
|---|---|---|
| Person | `residents.Resident` | `students.Student` |
| Rooms/Beds | `hostel.Room` / `hostel.Bed` (label/number, `TimeStampedModel`) | `rooms.Block→Floor→Room→Bed` (`HostelScopedModel`, status, rent, capacity) |
| Assignment | `residents.Stay`, `residents.BedAssignmentHistory` | `rooms.BedAssignment` (with unique constraints) |
| Billing | `billing.MonthlyDue` / `billing.Payment` / `billing.Invoice` | `fees.FeePlan→FeeLedger` + `payments.Payment→PaymentAllocation→Receipt` |
| Intake | (manual create) | `admissions.AdmissionRequest` (+ public form) |

Track B is materially more complete (admissions → student → constrained bed assignment → fee ledger → allocation → receipt, all `HostelScopedModel`). Track A looks like an earlier iteration. **They share no tables**, so the same hostel's data can diverge depending on which screens are used.

- **Issue:** Two sources of truth for rooms/beds/people/payments.
- **Impact:** Data fragmentation, double bookkeeping, confused reporting, `residents/models.py:5` couples a "current" subsystem to a "legacy" one.
- **Recommended solution:** Pick **one canonical track** (recommend **Track B**), migrate any needed data, then retire the other (remove from `INSTALLED_APPS`, drop routes, archive migrations). **Do not delete before the product owner confirms which track is live.**
- **Priority:** Critical · **Complexity:** L

---

## 2. CRITICAL findings

| # | Issue | Impact | Solution | Cx |
|---|---|---|---|---|
| C1 | **Duplicate domain models (§1)** | Data fragmentation / double truth | Choose canonical track, migrate, retire other | L |
| C2 | **No `LOGGING` config in `settings.py`** | Production errors invisible; no audit/debug trail | Add `LOGGING` dict (console+rotating file, per-app levels); add Sentry hook point | M |
| C3 | **Public layout doesn't redirect authenticated users; legacy token checks remain** (`frontend/src/app/(public)/layout.tsx`, `tenants/subscriptions`, `dashboard/layout.tsx` read `localStorage access_token`) | Broken auth UX; dead/contradictory guards | Redirect authed users to `/dashboard`; remove all legacy `access_token`/`role` localStorage reads, rely on cookie session + `/auth/me` | S |
| C4 | **Negative/zero payment amounts accepted** (`payments/models.py:6`, `billing/models.py:34`, no serializer `min_value`) | Ledger manipulation via reverse "payments" | `MinValueValidator(0.01)` on model + `min_value` on serializer | S |
| C5 | **Backup restore: no size/schema bound** (`backups/views.py:48-66`) | Disk exhaustion / untrusted blob storage | Enforce max size, validate against a schema, separate throttle scope | M |

> C2 fix is the single highest-leverage production change. C3/C4 are small and safe. C5 is contained (owner-only endpoint).

---

## 3. HIGH findings

| # | Issue | Impact | Solution | Cx |
|---|---|---|---|---|
| H1 | **Bed allocation race → 500 not 409** (`admissions/serializers.py:55`, `students/views.py` transfer, `rooms/views.py` perform_create) | Ugly errors under concurrency; bed status write outside txn | `select_for_update()` on bed inside `transaction.atomic()`, catch `IntegrityError`→409 | M |
| H2 | **`FeeLedger.net_due` never recalculated** after discount/fine change (`fees/models.py:22-25`, `fees/services.py:27-38`) | Wrong dues; allocation validation drifts | `save()` override / `recalculate_net_due()` = `amount - discount + fine`; recompute on allocation delete | S |
| H3 | **No outstanding-dues check before checkout/vacate** (`students/views.py:68`, `residents/views.py:54`) | Residents leave owing money | Block checkout when `FeeLedger` in `DUE/PARTIAL` (configurable override) | S |
| H4 | **No toast/confirm system; 12+ `alert()` calls** (beds, payments, expenses, vacate) | Blocking, unprofessional UX; accidental destructive actions | Add Toast + ConfirmDialog primitives; replace `alert()`/`confirm()` | M |
| H5 | **Form buttons lack loading/disabled state** across ~20 forms | Double-submits, no in-flight feedback | Add `loading`/`disabled` to shared `Button`; thread submit state | M |
| H6 | **Missing indexes on hot FK/filter fields** (attendance, billing dues/payments, complaints assigned_to, operations logs, payments allocations) | Full scans as data grows | `db_index=True` + composite `Meta.indexes` per §8 list | M |
| H7 | **Missing prefetch/select_related** (`residents` bed_history, `students` documents, `rooms` bed→room) | N+1 on list endpoints | Add `select_related`/`prefetch_related` to those `get_queryset` | M |
| H8 | **Production config can silently break/foot-gun**: `ALLOWED_HOSTS=[]` when `DEBUG=False`; CORS hardcoded; no guard against `*` | 400-for-everything or over-permissive CORS in prod | Fail-fast validation when `DEBUG=False`; document required env | S |
| H9 | **Reports return HTML, never PDF** though `weasyprint` is installed (`reports/views.py:18`) | "PDF support" advertised but absent | Wire `HTML(...).write_pdf()`; add report list per §6 | M |
| H10 | **No tests on critical flows** (auth, admissions, room allocation, RBAC, billing) — most `tests.py` empty | Regressions ship silently | Add targeted tests for the 6 critical flows + `conftest.py` fixtures | L |
| H11 | **Password reset token in URL query** (`accounts/views.py:217`) | Token leak via referrer/forwarded mail | Single-use signed token, server-validated; shorten TTL | M |
| H12 | **Celery backup task has no error handling; Redis URL hardcoded localhost** | Silent task failure; prod broker breakage | try/except + logging; env-driven broker URL | S |

---

## 4. MEDIUM findings

| # | Issue | Solution | Cx |
|---|---|---|---|
| M1 | Tenant isolation relies on per-view permission correctness (middleware accepts `X-HOSTEL-ID` w/o membership). Verify **every** viewset uses `HasHostelContext`/`IsHostelResolved`; add membership check in middleware as defence-in-depth | Audit viewsets + harden middleware | M |
| M2 | Inconsistent custom-action response shapes vs the `StandardJSONRenderer` envelope | Standardize `{detail, data}` for actions | M |
| M3 | Complaint status allows illegal transitions (CLOSED→OPEN) (`complaints/views.py:37`) | State-machine `VALID_TRANSITIONS` guard | S |
| M4 | `generate_month` not lock-guarded under concurrency (`fees/services.py:17`) | Wrap in txn; rely on `unique_together(student,month)` + log skips | M |
| M5 | Public admission serializer exposes too much; per-hostel rate limit + spam protection missing (`admissions/views.py:58`) | Dedicated public serializer (whitelist fields) + throttle scope | M |
| M6 | File uploads unvalidated (type/size) — residents photos, student docs, complaint attachments | `FileExtensionValidator` + size validator; serve via auth'd endpoint | M |
| M7 | No request dedupe/caching/cancellation on frontend (no React Query/SWR); duplicate fetches, race conditions | Introduce a small fetch layer or React Query; `AbortController` | L |
| M8 | Dashboard does multiple separate count queries; no caching (`dashboard/views.py`, `billing/views.py` in-memory sum) | Combine via `aggregate()`; cache 60s | M |
| M9 | `fields="__all__"` across many serializers | Explicit `fields`/`read_only_fields` | M |
| M10 | No API versioning (`/api/v1`) | Add URL versioning namespace | M |
| M11 | Money fields `max_digits=10` | Bump to 12–14 for large institutions | S |
| M12 | No dark mode, partial responsiveness, accessibility gaps (labels/ARIA), missing empty states on several tables | Theme tokens + dark variants; `htmlFor`; empty-state component | M |
| M13 | Session cookie hardening only in prod; `SECURE_CONTENT_TYPE_NOSNIFF` gated on DEBUG | Always-on nosniff; explicit session flags | S |
| M14 | Audit endpoints/serializers unpaginated + `__all__` | Explicit pagination + field whitelist | S |

---

## 5. LOW findings

| # | Issue | Solution |
|---|---|---|
| L1 | Unused `axios` dep (app uses `fetch`) | Remove from `package.json` |
| L2 | Hardcoded currency `Rs./NPR` in several places | Centralize `formatCurrency` + config |
| L3 | Topbar shows all 21 routes regardless of role | Role-filtered nav |
| L4 | `db.sqlite3.bak-premigrate` committed | Remove + gitignore |
| L5 | Duplicate route registrations (rooms vs hostel, payments vs billing) | Resolve once canonical track chosen (§1) |
| L6 | `month` CharField lacks format validation (`fees`) | `RegexValidator(YYYY-MM)` |
| L7 | `BedAssignment.end_date` not enforced ≥ `start_date` | `clean()` / check constraint |
| L8 | No request timeout / offline handling on frontend | `AbortSignal` timeout; offline banner |
| L9 | No Docker/compose, no CI pipeline, no Procfile | Add when deployment target is chosen |

---

## 6. Reporting module — present vs needed

CSV exports exist for residents/occupancy/due-payments/complaints/attendance/visitors (`apps/exports/views.py`). **Missing:** real PDF (H9), revenue report with method breakdown, aging analysis (30/60/90), complaint SLA/resolution-time, occupancy trend. Filtering/date-range present unevenly.

## 7. Payments correctness summary

Track B (`payments/services.allocate_payment`) is sound: locks the ledger, recomputes status, validates positivity — but **after** record creation (C4) and without recalculating `net_due` (H2). Allocation-on-delete doesn't recompute (L-ish). Track A billing sums without locking (overpayment hidden by `remaining` clamp).

## 8. Index targets (H6)

`attendance(resident,date)`, `billing.MonthlyDue(hostel,resident)`, `billing.Payment(hostel,resident,due)`, `complaints.Complaint(assigned_to,created_by,status)`, `operations.*(resident,student,recorded_by)`, `payments.PaymentAllocation(payment,ledger)`, `residents.BedAssignmentHistory(resident,bed)`, `students.StudentDocument(student)`.

---

## 9. Recommended implementation order

1. **Decision gate:** confirm canonical domain (§1).
2. **Critical, no-decision:** C2 logging, C3 auth-guard cleanup, C4 payment validators. (C5 backup bound.)
3. **High, safe:** H2 net_due, H3 dues-on-checkout, H8 prod-config guards, H1 bed-allocation locking, H6/H7 indexes+prefetch, H12 celery/redis.
4. **High, UX:** H4 toast/confirm, H5 button loading, H9 PDF reports.
5. **Tests (H10)** alongside each backend change.
6. **Medium → Low** as scoped.

Items requiring product input before code: **§1 canonical track**, scope of infra (Docker/CI/S3), and whether to adopt React Query (M7).
