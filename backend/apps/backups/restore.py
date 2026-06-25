"""Restore engine — the heart of disaster recovery.

Restore flow (per the Phase-4 spec):
    1. Validate backup file
    2. Check schema_version compatibility
    3. Create snapshot of current DB (pre-restore)
    4. Switch to maintenance mode (stop writes)
    5. Restore database (atomic: delete canonical rows, re-insert from backup)
    6. Run integrity checks (counts; FK integrity enforced by the DB)
    7. Re-enable the system

Safety rules enforced here:
    * Destructive restore requires ``force=True`` (the API additionally requires
      an explicit confirmation token).
    * A pre-restore snapshot is ALWAYS created before any deletion.
    * Integrity is checked *inside* the transaction, so a mismatch rolls the
      whole restore back to the original data.
    * ``dry_run=True`` validates and reports a plan without writing anything.
"""

import json
import logging
import traceback

from django.db import transaction
from django.utils.timezone import now

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event

from .alerts import dr_alert
from .dr import maintenance_window
from .dump import (
    CANONICAL_SECTIONS,
    canonical_counts,
    get_section_model,
    section_queryset,
)
from .models import BackupPeriod, RestoreRun
from .storage import create_snapshot, load_backup_data
from .validation import validate_backup

logger = logging.getLogger("apps.backups")


class RestoreError(Exception):
    """Base class for restore failures."""


class RestoreSafetyError(RestoreError):
    """Raised when safety preconditions (force/confirmation) are not met."""


class RestoreValidationError(RestoreError):
    """Raised when the backup fails validation and force is not set."""


class RestoreIntegrityError(RestoreError):
    """Raised when post-restore integrity checks fail (rolls back)."""


def _load_and_validate(source_snapshot, data):
    if source_snapshot is not None:
        report = validate_backup(source_snapshot, persist=True)
        data = load_backup_data(source_snapshot)
    else:
        if not isinstance(data, dict):
            raise RestoreValidationError("No backup data provided.")
        raw = json.dumps(data, default=str).encode("utf-8")
        report = validate_backup(raw_bytes=raw)
    return data, report


def _backup_counts(data: dict) -> dict:
    return {
        s.key: (len(data[s.key]) if isinstance(data.get(s.key), list) else 0)
        for s in CANONICAL_SECTIONS
    }


def _apply_rows(hostel, data: dict) -> dict:
    """Delete canonical rows for the hostel and re-insert them from ``data``.

    Must run inside an atomic block. Returns inserted counts per section.
    """
    # Delete children-first (reverse FK order) to avoid protected deletes.
    for section in reversed(CANONICAL_SECTIONS):
        section_queryset(section, hostel).delete()

    inserted = {}
    # Insert parents-first.
    for section in CANONICAL_SECTIONS:
        model = get_section_model(section)
        rows = data.get(section.key, []) or []
        objs = []
        for raw in rows:
            row = dict(raw)
            # Pin hostel-scoped rows to the target hostel (supports staging
            # restores into a different hostel without rewriting children).
            if section.scope == "hostel":
                row["hostel_id"] = hostel.id
            objs.append(model(**row))
        if objs:
            model.objects.bulk_create(objs, batch_size=500)
        inserted[section.key] = len(objs)
    return inserted


def _integrity_check(hostel, expected: dict) -> dict:
    """Compare live counts to expected (backup) counts. Returns a report."""
    live = canonical_counts(hostel)
    mismatches = {
        key: {"expected": expected.get(key, 0), "actual": live.get(key, 0)}
        for key in expected
        if expected.get(key, 0) != live.get(key, 0)
    }
    return {"ok": not mismatches, "live_counts": live, "mismatches": mismatches}


def ensure_hostel_from_dump(data: dict, *, create: bool = True):
    """Resolve (or recreate) the target hostel from a backup's hostel section.

    Enables recovery from a backup FILE alone after total DB loss: if the hostel
    row is gone, it is recreated with its original id/code so child FKs match.
    """
    from apps.tenants.models import Hostel

    meta = (data or {}).get("hostel") or {}
    hid = meta.get("id")
    code = meta.get("code")

    hostel = None
    if hid:
        hostel = Hostel.objects.filter(id=hid).first()
    if hostel is None and code:
        hostel = Hostel.objects.filter(code=code).first()
    if hostel is None and create:
        hostel = Hostel(
            id=hid,
            name=meta.get("name", "") or "Recovered hostel",
            code=code or "",
            address=meta.get("address", "") or "",
            phone=meta.get("phone", "") or "",
            owner_name=meta.get("owner_name", "") or "",
            plan_name=meta.get("plan_name", "basic") or "basic",
        )
        hostel.save(force_insert=True)
        logger.warning("Recreated hostel %s (%s) from backup during recovery", hostel.id, hostel.code)
    return hostel


def restore_hostel(
    hostel,
    *,
    source_snapshot=None,
    data=None,
    user=None,
    request=None,
    dry_run=False,
    force=False,
):
    """Restore one hostel's canonical data. Returns a :class:`RestoreRun`.

    Pass either ``source_snapshot`` (a BackupSnapshot) or raw ``data`` (dict).
    """
    run = RestoreRun.objects.create(
        hostel=hostel,
        backup=source_snapshot,
        status=RestoreRun.Status.PENDING,
        dry_run=dry_run,
        force=force,
        performed_by=user if (user is not None and getattr(user, "pk", None)) else None,
        started_at=now(),
    )

    try:
        data, report = _load_and_validate(source_snapshot, data)
        run.schema_version = report.get("schema_version") or 0
        before_counts = canonical_counts(hostel)
        backup_counts = _backup_counts(data)
        run.stats = {
            "validation": report,
            "before_counts": before_counts,
            "backup_counts": backup_counts,
        }

        # Step 1+2: validation / schema compatibility gate.
        if not report["ok"] and not force:
            run.status = RestoreRun.Status.FAILED
            run.error = "Backup failed validation: " + "; ".join(report["errors"])
            run.finished_at = now()
            run.save()
            dr_alert(
                "corrupt_backup_detected",
                run.error,
                hostel=hostel,
                meta={"backup_id": str(getattr(source_snapshot, "id", "")), "report": report},
            )
            raise RestoreValidationError(run.error)

        # --- DRY RUN: report the plan, change nothing. ---
        if dry_run:
            run.status = RestoreRun.Status.DRY_RUN
            run.stats["plan"] = {
                "would_delete": before_counts,
                "would_insert": backup_counts,
                "valid": report["ok"],
            }
            run.finished_at = now()
            run.save()
            record_event(
                request, action=AuditEvent.Action.RESTORE_STARTED, actor=user, hostel=hostel,
                entity_type="backup.restore", entity_id=str(run.id),
                message=f"Dry-run restore for {hostel.code}",
                meta={"dry_run": True, "valid": report["ok"]},
            )
            return run

        # Step 0 (safety): destructive restore needs explicit force.
        if not force:
            run.status = RestoreRun.Status.FAILED
            run.error = "Refusing to overwrite data without force=True."
            run.finished_at = now()
            run.save()
            raise RestoreSafetyError(run.error)

        run.status = RestoreRun.Status.RUNNING
        run.save(update_fields=["status", "schema_version", "stats"])
        record_event(
            request, action=AuditEvent.Action.RESTORE_STARTED, actor=user, hostel=hostel,
            entity_type="backup.restore", entity_id=str(run.id),
            message=f"Restore started for {hostel.code}",
            meta={"backup_id": str(getattr(source_snapshot, "id", "")), "force": True},
        )

        # Step 3: ALWAYS snapshot current state before destruction.
        pre = create_snapshot(
            hostel, period=BackupPeriod.PRE_RESTORE, kind="pre_restore",
            note=f"Auto pre-restore snapshot for run {run.id}",
        )
        run.pre_restore_snapshot = pre
        run.save(update_fields=["pre_restore_snapshot"])
        record_event(
            request, action=AuditEvent.Action.SNAPSHOT, actor=user, hostel=hostel,
            entity_type="backup.snapshot", entity_id=str(pre.id),
            message=f"Pre-restore snapshot {pre.id} created",
        )

        # Steps 4-6: maintenance window + atomic restore + integrity.
        with maintenance_window(reason=f"restore {run.id} for {hostel.code}", user=user):
            with transaction.atomic():
                inserted = _apply_rows(hostel, data)
                integrity = _integrity_check(hostel, backup_counts)
                run.stats["inserted"] = inserted
                run.stats["integrity"] = integrity
                if not integrity["ok"]:
                    # Roll back the whole restore — original data is restored.
                    raise RestoreIntegrityError(
                        f"Integrity check failed: {integrity['mismatches']}"
                    )

        # Step 7: success (maintenance window exits → normal mode).
        run.status = RestoreRun.Status.COMPLETED
        run.finished_at = now()
        run.save()
        record_event(
            request, action=AuditEvent.Action.RESTORE_COMPLETED, actor=user, hostel=hostel,
            entity_type="backup.restore", entity_id=str(run.id),
            message=f"Restore completed for {hostel.code}",
            meta={"inserted": inserted, "pre_restore_snapshot": str(pre.id)},
        )
        logger.info("Restore %s completed for hostel %s", run.id, hostel.id)
        return run

    except (RestoreValidationError, RestoreSafetyError):
        # Already recorded on the run above; just propagate.
        raise
    except Exception as exc:  # noqa: BLE001 — integrity + any failure -> logged DR failure
        run.status = RestoreRun.Status.FAILED
        run.error = f"{exc}\n{traceback.format_exc()}"[:4000]
        run.finished_at = now()
        run.save()
        record_event(
            request, action=AuditEvent.Action.RESTORE_FAILED, actor=user, hostel=hostel,
            entity_type="backup.restore", entity_id=str(run.id),
            message=f"Restore failed for {hostel.code}: {exc}"[:255],
        )
        dr_alert(
            "restore_failed",
            f"Restore {run.id} failed for {hostel.code}: {exc}",
            hostel=hostel,
            meta={"run_id": str(run.id)},
            audit_action=AuditEvent.Action.RESTORE_FAILED,
        )
        raise RestoreError(str(exc)) from exc
