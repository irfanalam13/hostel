"""Restore-drill: prove a backup is actually restorable, and measure RTO/RPO.

A backup you have never restored is a hope, not a recovery plan (DEVOPS_AUDIT
P1). This exercises the *real* restore engine end-to-end against a chosen
snapshot and reports:

  * **RTO** (Recovery Time Objective) — wall-clock seconds the restore took.
  * **RPO** (Recovery Point Objective) — age of the backup at drill time, i.e.
    how much data a recovery from it would lose.
  * **integrity** — the engine's own post-restore row-count check.

It drives ``restore.restore_hostel`` (which takes a pre-restore snapshot, enters
a maintenance window, and restores atomically with integrity enforced inside the
transaction). Because it triggers a brief maintenance window and rewrites the
target hostel's canonical rows, run it in an **isolated / staging database**
(the scheduled workflow uses an ephemeral Postgres) — never casually on prod.
"""
from __future__ import annotations

import logging
import time

from django.utils.timezone import now

from .models import BackupSnapshot
from .restore import restore_hostel

logger = logging.getLogger("apps.backups")


def latest_snapshot(hostel=None) -> BackupSnapshot | None:
    qs = BackupSnapshot.objects.all()
    if hostel is not None:
        qs = qs.filter(hostel=hostel)
    return qs.order_by("-created_at").first()


def run_drill(
    source_snapshot: BackupSnapshot,
    *,
    max_rto_seconds: float | None = None,
    max_rpo_seconds: float | None = None,
    cleanup: bool = True,
) -> dict:
    """Restore ``source_snapshot`` into its hostel and grade RTO/RPO/integrity.

    Returns a result dict (never raises for a *failed* drill — inspect ``ok``);
    only genuine engine errors propagate.
    """
    rpo_seconds = (now() - source_snapshot.created_at).total_seconds()

    started = time.monotonic()
    run = restore_hostel(source_snapshot.hostel, source_snapshot=source_snapshot, force=True)
    rto_seconds = time.monotonic() - started

    integrity = (run.stats or {}).get("integrity", {})
    integrity_ok = bool(integrity.get("ok"))

    reasons = []
    if not integrity_ok:
        reasons.append(f"integrity mismatch: {integrity.get('mismatches')}")
    if max_rto_seconds is not None and rto_seconds > max_rto_seconds:
        reasons.append(f"RTO {rto_seconds:.1f}s > target {max_rto_seconds}s")
    if max_rpo_seconds is not None and rpo_seconds > max_rpo_seconds:
        reasons.append(f"RPO {rpo_seconds:.0f}s > target {max_rpo_seconds}s")

    result = {
        "ok": not reasons,
        "reasons": reasons,
        "snapshot_id": str(source_snapshot.id),
        "hostel": source_snapshot.hostel.code,
        "rto_seconds": round(rto_seconds, 3),
        "rpo_seconds": round(rpo_seconds, 1),
        "restore_status": run.status,
        "restored_counts": (run.stats or {}).get("inserted", {}),
        "integrity_ok": integrity_ok,
        "restore_run_id": str(run.id),
    }

    # Housekeeping: the engine created a pre-restore safety snapshot; a routine
    # drill shouldn't accumulate them.
    if cleanup and run.pre_restore_snapshot_id:
        pre = run.pre_restore_snapshot
        try:
            pre.file.delete(save=False)
        except Exception:  # file backend may already be gone
            logger.debug("could not delete pre-restore file for %s", pre.id, exc_info=True)
        pre.delete()

    logger.info("DR drill result: %s", result)
    return result
