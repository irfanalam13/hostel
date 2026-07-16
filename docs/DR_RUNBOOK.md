# Disaster Recovery Runbook

**Phase 5, §6.** Targets, procedures, and drills that make recovery *proven*, not
hoped-for. Built on the `apps/backups` DR engine (backup, verify, restore,
retention, DR modes) — this doc is the operational layer on top.

## Targets

| Objective | Target | Notes |
| --- | --- | --- |
| **RPO** (max data loss) | ≤ 24h | Daily scheduled backups per hostel. Tighten with more frequent backups. |
| **RTO** (max time to recover one hostel) | ≤ 15 min | Logical per-hostel restore; measured by drills/game-days. |
| **Backup retention** | 7 daily · 4 weekly · 12 monthly | Enforced by `dr_retention`. |
| **Backup location** | Off-host object storage (S3/R2) | Enforced by `dr_offsite_check`. |

## Architecture facts

- Backups are **per-hostel logical dumps** (canonical Track A data) — gzip JSON
  with sha256 checksum + schema version (`apps/backups/dump.py`, `storage.py`).
- Restore is **atomic** with integrity checked *inside* the transaction, always
  preceded by an automatic pre-restore snapshot (`apps/backups/restore.py`).
- DR modes (`dr_mode`): `normal` → `maintenance` (read-only) → `emergency`.

## Everyday commands

```bash
python manage.py dr_backup --all                 # back up every active hostel
python manage.py dr_verify --all                 # checksum + loadability
python manage.py dr_retention                     # prune expired backups
python manage.py dr_offsite_check --max-age-hours 26   # off-host + fresh (prod)
python manage.py dr_mode --set maintenance --reason "restore in progress"
```

## Restore procedure (real recovery)

1. `dr_mode --set maintenance --reason "..."` — stop writes.
2. Identify the backup: `dr_verify --hostel <CODE>` (confirm a valid, recent one).
3. Dry-run: `dr_restore --hostel <CODE> --dry-run` — review the plan/counts.
4. Restore: `dr_restore --hostel <CODE> --force --confirm <CODE>`
   (a pre-restore snapshot is taken automatically; integrity is enforced).
5. `dr_verify --hostel <CODE>` — confirm post-restore integrity.
6. `dr_mode --set normal`.

Total-loss (backup file only): `dr_restore --file <path>` recreates the hostel
from the dump (`ensure_hostel_from_dump`).

## Drills & game-days (this is what makes it "proven")

- **Automated restore drill** — `dr_drill` restores a snapshot end-to-end into an
  isolated DB and grades **integrity + RTO + RPO**. The verified engine test
  (`apps/backups/tests_drill.py`) runs in the `test-backend` CI job on Postgres,
  and on a **weekly schedule** via `.github/workflows/dr-drill.yml` (catches
  restore-breaking drift even with no relevant PRs).
    ```bash
    python manage.py dr_drill --hostel <CODE> --max-rto 900 --max-rpo 93600 --confirm
    ```
- **Quarterly game-day** — `deploy/scripts/dr_gameday.sh` runs a full
  simulate-loss-and-recover exercise on **staging** and records the real RTO:
    ```bash
    DR_GAMEDAY_ENV=staging bash deploy/scripts/dr_gameday.sh <CODE> --confirm <CODE>
    ```
  Record each game-day's measured RTO/RPO below.

## Off-site & cross-region

- Set `STORAGE_BACKEND=s3` (+ `S3_*`) so backups leave the app/DB host
  (DEVOPS_AUDIT P1). `dr_offsite_check` fails in production if storage is local.
- **Cross-region:** enable object-store replication (S3 CRR / R2) to a second
  region so a regional outage can't take both the DB and its backups. This is an
  infra setting on the bucket (out of app scope) — track it in Terraform.
- `BACKUP_ENCRYPTION_KEY` — keep an escrow copy; without it offsite backups are
  undecryptable.

## Drill log

| Date | Type | Hostel | RTO | RPO | Result | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| _(record each drill/game-day here)_ | | | | | | |
