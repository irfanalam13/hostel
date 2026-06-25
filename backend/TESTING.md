# Testing & Coverage (Phase 10)

The backend has a pytest-based regression suite that guards the **canonical
Track A** business flows (auth → RBAC → admission → billing → checkout). CI
fails the build if coverage of those apps drops below **80%**.

## Running

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt
pytest                       # full suite + coverage gate (>=80%)
pytest apps/billing -q       # one app
pytest -m integration        # only end-to-end flows
pytest -m concurrency        # only race-condition guards
pytest --no-cov -q           # skip the coverage gate (faster local loop)
```

`pytest.ini` pins `DJANGO_SETTINGS_MODULE=config.settings_test`, which uses an
isolated in-memory SQLite DB, a fast password hasher, locmem email, eager
Celery, and disables django-axes / DRF throttling by default (the brute-force
and rate-limit tests re-enable them locally with `override_settings`).

## Coverage scope

Coverage (see `.coveragerc`) is measured **only** over the canonical apps —
`common`, `tenants`, `accounts`, `hostel`, `residents`, `billing` — plus the
shared auth/permission layer. Track B (`admissions`, `students`, `rooms`,
`fees`, `payments`) is legacy per the product decision and is deliberately out
of the gate. Migrations, tests, `admin.py`, and `apps.py` are omitted.

Current: **~85%** of canonical apps, 151 tests.

## Layout

```
apps/accounts/tests/   login, signup, password reset, brute-force lockout
apps/common/tests/     RBAC, tenant isolation, middleware, health, integration, renderers
apps/residents/tests/  CRUD + bed history, full lifecycle, negative, performance
apps/billing/tests/    dues integrity, payment→due recalc, dashboard, concurrency, services
apps/hostel/tests/     room/bed uniqueness + tenant scoping
apps/tenants/tests/    hostel code generation + membership scoping
```

## Fixtures / factories

Shared Factory Boy factories and fixtures live in the top-level `conftest.py`:
`hostel`, `other_hostel`, role fixtures (`owner`/`manager`/`accountant`/
`warden`/`resident_user`/`superuser`), `make_user`, and `auth_client(user,
hostel)` — which authenticates with a **real JWT Bearer token** so requests
traverse the full authentication + tenant-resolution + permission stack.

## Notes on concurrency tests

SQLite makes `select_for_update` a no-op and can't share an in-memory DB across
threads, so the `concurrency`-marked tests assert the **correctness
invariants** the locks/constraints protect (no duplicate dues, idempotent
recalc, sum-derived `paid_amount`) rather than spawning real parallel
transactions. On the production Postgres target the row lock in
`billing.services.recalc_due_paid_amount` enforces true parallel safety.

## Bugs caught while writing the suite

* `Resident.join_date` / `VacateRequest.requested_date` defaulted to
  `timezone.now` (a *datetime*) on a `DateField`, 500-ing serialization of any
  resident created without an explicit date. Fixed to `timezone.localdate`.
* Resident list endpoint had an N+1 over nested `bed_history`; added
  `prefetch_related("bed_history")` and a query-budget test to lock it in.
