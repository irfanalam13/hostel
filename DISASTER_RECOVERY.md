# Disaster Recovery (DR) — Hostel SaaS

This document is the operational runbook for backing up and restoring the
hostel management platform. It is written so that **a new engineer can lose the
entire database and bring the system back from backups alone, within 30
minutes, without guessing.**

> **Canonical domain:** DR operates on **Track A** (residents, billing,
> payments, attendance, rooms/beds). Legacy **Track B** data is still written
> into backup files so nothing is lost mid-migration, but it is intentionally
> excluded from restore/validation/integrity logic.

---

## 1. Backup system overview

* **What a backup is** — a per-hostel JSON export of canonical data
  (`apps/backups/dump.py`), gzip-compressed, with a recorded **sha256
  checksum**, **size**, and **schema version**.
* **Where backups live** — on `MEDIA_ROOT/backups/`, organised by retention
  bucket:

  ```
  backups/daily/     backups/weekly/     backups/monthly/
  backups/manual/    backups/pre_restore/
  ```

  Naming convention: `<hostelcode>_<UTCtimestamp>_v<schema>.json.gz`
  (e.g. `H-25EB54_20260614T103551_v2.json.gz`).
* **How backups run** — automatically via **Celery Beat** (see §3), or manually
  via the API / CLI.
* **Metadata** — each backup is a `BackupSnapshot` row carrying
  `checksum`, `size_bytes`, `schema_version`, `period`, `is_valid`,
  `validated_at`.

### Backup schema versioning
`BACKUP_SCHEMA_VERSION = 2` (`apps/backups/dump.py`). Restores reject any file
whose `schema_version` is not in `SUPPORTED_SCHEMA_VERSIONS`. Bump the version
(and add a migration path) whenever the canonical dump shape changes.

---

## 2. RTO / RPO

| Objective | Target | How it is met |
|-----------|--------|---------------|
| **RTO** (Recovery Time Objective) | **< 30 minutes** | Logical JSON restore of one hostel runs in seconds–minutes; the documented procedure (§4/§5) is a handful of commands. |
| **RPO** (Recovery Point Objective) | **≤ 24 hours** | Daily automated backups (01:00) + a missed-backup monitor that alerts if any hostel has no backup within `BACKUP_MAX_AGE_HOURS` (default 26h). |

---

## 3. Scheduled backups (Celery Beat)

Defined in `CELERY_BEAT_SCHEDULE` (settings), in the project timezone
(`Asia/Kathmandu`, `CELERY_ENABLE_UTC = False`):

| Schedule | When | Task |
|----------|------|------|
| Daily | every day 01:00 | `run_scheduled_backups("daily")` |
| Weekly | Sunday 02:00 | `run_scheduled_backups("weekly")` |
| Monthly | 1st of month 03:00 | `run_scheduled_backups("monthly")` |
| Retention | daily 04:00 | `apply_retention` |
| Missed-backup monitor | every 6h | `check_missed_backups` |

Each per-hostel backup (`backup_hostel`) **retries up to 3 times** and raises a
DR alert if it ultimately fails. Run the worker + scheduler:

```bash
docker compose up -d celery_worker celery_beat   # production
# or locally:
celery -A config worker -l info
celery -A config beat   -l info
```

---

## 4. Backup retention policy

Per hostel, per bucket (configurable via `BACKUP_RETENTION` / env):

| Bucket | Keep | Env override |
|--------|------|--------------|
| Daily | 7 | `BACKUP_RETENTION_DAILY` |
| Weekly | 4 | `BACKUP_RETENTION_WEEKLY` |
| Monthly | 12 | `BACKUP_RETENTION_MONTHLY` |

* **Manual** and **pre-restore** snapshots are **never** auto-deleted.
* Every deletion is written to the audit log; deletion failures raise an alert.
* Storage usage (count + bytes per bucket) is reported by `storage_usage()`
  and by `manage.py dr_retention`.

```bash
manage.py dr_retention --dry-run     # show what would be deleted
manage.py dr_retention               # enforce
```

---

## 5. Restore procedure (step by step)

The engine (`apps/backups/restore.py`) always performs:

1. **Validate** the backup file (checksum, schema, required tables, readability,
   size).
2. **Check schema-version** compatibility.
3. **Create a pre-restore snapshot** of current data (so a restore is itself
   reversible).
4. **Switch to maintenance mode** (writes blocked system-wide).
5. **Restore** inside a single DB transaction (delete canonical rows → re-insert
   from backup, parents-first).
6. **Integrity check** inside the transaction (row counts; FK integrity enforced
   by the DB). On mismatch the whole restore **rolls back** to the original data.
7. **Re-enable** the system (back to normal mode).

### Safety rules (enforced in code)
* A destructive restore requires **`force=true`**.
* The Admin API additionally requires a **confirmation token** equal to the
  hostel code being overwritten.
* A **pre-restore snapshot is always created** before any deletion.
* **Dry-run** (`dry_run=true`) validates and reports a plan, changing nothing.

### Option A — Admin API
```http
POST /api/admin/restore/        (admin only)
# dry run:
{ "backup_id": "<uuid>", "dry_run": true }
# real restore:
{ "backup_id": "<uuid>", "force": true, "confirm": "<HOSTEL_CODE>" }
```

### Option B — CLI (preferred during a real incident)
```bash
# From a stored backup (DB still has the BackupSnapshot row):
manage.py dr_restore --backup-id <uuid> --dry-run
manage.py dr_restore --backup-id <uuid> --force --confirm <HOSTEL_CODE>

# From a file alone, after TOTAL database loss (recreates the hostel):
manage.py dr_restore --file backups/daily/H-ABC_..._v2.json.gz \
    --force --confirm <HOSTEL_CODE>
```

---

## 6. Emergency recovery — "the database is gone"

Goal: rebuild a working system from backup files only. Target < 30 min.

```bash
# 1. Stand up infrastructure + apply schema
docker compose up -d postgres redis
docker compose run --rm web python manage.py migrate

# 2. (optional) lock the system while recovering
docker compose exec web python manage.py dr_mode --set emergency --reason "DB loss recovery"

# 3. Restore each hostel from its newest backup FILE (recreates hostels too)
#    Backups live under MEDIA_ROOT/backups/<bucket>/.
docker compose exec web python manage.py dr_restore \
    --file backups/daily/<hostelcode>_<latest>.json.gz \
    --force --confirm <HOSTEL_CODE>
#    Repeat per hostel. Verify each with --dry-run first if unsure.

# 4. Verify integrity of all restored backups
docker compose exec web python manage.py dr_verify --all

# 5. Return to normal
docker compose exec web python manage.py dr_mode --set normal

# 6. Bring the app + workers back
docker compose up -d web celery_worker celery_beat frontend
```

> Media files (resident photos / ID docs) are stored separately from the JSON
> backup; restore them from the media volume / object-store backup. The DB
> restore re-links their paths.

---

## 7. Disaster-recovery modes

System-wide singleton (`DRState`), enforced by `DRModeMiddleware`:

| Mode | Behaviour |
|------|-----------|
| **normal** | Full operation. |
| **maintenance** | Read-only: GET/HEAD/OPTIONS pass; writes get `503`. Used automatically during a restore. |
| **emergency** | Full lock: everything returns `503` except health checks, auth, and the admin DR API (admin-only). |

```bash
manage.py dr_mode                          # show current mode
manage.py dr_mode --set maintenance --reason "..."
manage.py dr_mode --set normal
# or via API: POST /api/admin/dr/mode/  { "mode": "maintenance", "reason": "..." }
```

Health endpoints (`/health/...`) and the admin DR API are always exempt so
operators can drive recovery even under a full lock.

---

## 8. Backup validation

A backup is only trusted if it passes every check (`apps/backups/validation.py`):

* **file readability** — gzip-decodes + JSON-parses
* **file integrity** — sha256 matches the stored checksum
* **schema compatibility** — `schema_version` is supported
* **required tables present** — residents, billing (monthly_dues), payments
  (billing_payments), attendance, rooms (hostel_rooms), beds (hostel_beds)
* **size sanity** — within `[BACKUP_MIN_BYTES, BACKUP_MAX_BYTES]`

Invalid backups are rejected automatically: a freshly-created backup that fails
validation raises an alert, and a restore from an invalid backup is refused
unless `force` is set.

```bash
manage.py dr_verify --backup-id <uuid>
manage.py dr_verify --hostel <code>
manage.py dr_verify --all
```

---

## 9. DR audit logging

Every DR event is recorded as an `AuditEvent` with timestamp, actor, action,
status, and backup/run id. Actions:

`backup`, `backup_failed`, `snapshot`, `restore_started`, `restore_completed`,
`restore_failed`, `retention`, `retention_failed`, `maintenance`.

`RestoreRun` rows additionally capture the full lifecycle of each restore
(status, dry-run flag, before/after counts, validation report, integrity result,
pre-restore snapshot, error).

---

## 10. Monitoring & alerting

`dr_alert()` funnels every DR failure to: ERROR logs, **Sentry** (if
`SENTRY_DSN` set), **email** (`DR_ALERT_EMAILS`, if SMTP configured), and the
audit log. Alerts fire on:

* backup failure (after retries)
* restore failure
* missing scheduled backup (RPO breach)
* retention deletion failure
* corrupt backup detected

---

## 11. Recovery testing

Restores are testable without touching production:

* **Dry-run** (`--dry-run` / `dry_run=true`) validates + plans, mutating nothing.
* **Staging restore** — restore a backup into a *different* hostel (the engine
  re-pins hostel-scoped rows to the target), or into a throwaway database.
* **Automated tests** (`apps/backups/tests_dr.py`, 23 tests) cover:
  backup→restore→consistency, corrupted-backup rejection, dry-run no-op,
  atomic rollback on failure, retention enforcement, maintenance-mode gating,
  schema-version rejection, and admin-API protection.

```bash
python manage.py test apps.backups.tests_dr apps.backups.tests
```

---

## 12. Contact / escalation flow

1. **On-call engineer** — runs `dr_verify`, attempts restore per §5/§6.
2. **Backend lead** — if restore fails integrity or backups are corrupt.
3. **Platform/DB owner** — if infrastructure (Postgres/Redis/volumes) is lost.
4. **Product owner** — informed of any data-loss window (RPO impact).

Record every incident: which backup was restored, the `RestoreRun` id, the
pre-restore snapshot id, and the data-loss window.
