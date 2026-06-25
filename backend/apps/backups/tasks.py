"""Celery tasks for disaster recovery: scheduled backups, retention, monitoring.

Scheduling lives in ``CELERY_BEAT_SCHEDULE`` (settings). All tasks retry on
failure and raise DR alerts so a problem is never silent.
"""

import logging
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils.timezone import now

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.tenants.models import Hostel

from .alerts import dr_alert
from .dump import BACKUP_SCHEMA_VERSION, build_hostel_dump  # noqa: F401 (re-export)
from .models import BackupPeriod, BackupSnapshot
from .retention import apply_retention as _apply_retention
from .storage import create_snapshot
from .validation import validate_backup

logger = logging.getLogger("apps.backups")

# --- Backward-compatible alias (older imports expect tasks._dump_hostel) ---
_dump_hostel = build_hostel_dump


def _do_backup(hostel: Hostel, period: str, *, kind: str, note: str) -> BackupSnapshot:
    """Create + validate a backup for one hostel. Raises if validation fails."""
    snap = create_snapshot(hostel, period=period, kind=kind, note=note)
    report = validate_backup(snap, persist=True)
    if not report["ok"]:
        # A freshly written backup that fails validation is a serious problem.
        raise RuntimeError(f"backup {snap.id} failed validation: {report['errors']}")
    record_event(
        action=AuditEvent.Action.BACKUP, hostel=hostel,
        entity_type="backup.snapshot", entity_id=str(snap.id),
        message=f"{period} backup created for {hostel.code}",
        meta={"period": period, "size_bytes": snap.size_bytes, "checksum": snap.checksum},
    )
    logger.info("Backup %s (%s) created for hostel %s", snap.id, period, hostel.id)
    return snap


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def backup_hostel(self, hostel_id, period: str = BackupPeriod.DAILY):
    """Create one backup for one hostel (retried up to 3 times)."""
    try:
        hostel = Hostel.objects.get(id=hostel_id)
    except Hostel.DoesNotExist:
        logger.error("Backup skipped: hostel %s not found.", hostel_id)
        return None
    try:
        snap = _do_backup(hostel, period, kind="scheduled", note=f"Auto {period} backup")
        return str(snap.id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Backup failed for hostel %s (%s).", hostel_id, period)
        if self.request.retries >= self.max_retries:
            dr_alert(
                "backup_failed",
                f"{period} backup failed for hostel {hostel_id} after {self.max_retries} retries: {exc}",
                hostel=hostel,
                meta={"hostel_id": str(hostel_id), "period": period},
                audit_action=AuditEvent.Action.BACKUP_FAILED,
            )
        raise self.retry(exc=exc)


@shared_task
def run_scheduled_backups(period: str = BackupPeriod.DAILY):
    """Fan out a backup task per active hostel for the given bucket."""
    hostel_ids = list(Hostel.objects.filter(is_active=True).values_list("id", flat=True))
    for hid in hostel_ids:
        backup_hostel.delay(str(hid), period)
    logger.info("Scheduled %s backups for %d hostels.", period, len(hostel_ids))
    return {"period": period, "hostels": len(hostel_ids)}


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def apply_retention(self):
    """Enforce the retention policy across all hostels."""
    try:
        return _apply_retention()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Retention task failed.")
        if self.request.retries >= self.max_retries:
            dr_alert(
                "retention_failed",
                f"Retention task failed after retries: {exc}",
                audit_action=AuditEvent.Action.RETENTION_FAILED,
            )
        raise self.retry(exc=exc)


@shared_task
def check_missed_backups():
    """Alert if any active hostel has no recent successful backup (RPO guard)."""
    max_age = timedelta(hours=getattr(settings, "BACKUP_MAX_AGE_HOURS", 26))
    cutoff = now() - max_age
    stale = []
    for hostel in Hostel.objects.filter(is_active=True):
        last = (
            BackupSnapshot.objects.filter(hostel=hostel)
            .exclude(period=BackupPeriod.PRE_RESTORE)
            .order_by("-created_at")
            .first()
        )
        if last is None or last.created_at < cutoff:
            stale.append(hostel.code)
            dr_alert(
                "missing_scheduled_backup",
                f"No backup for {hostel.code} within {max_age}.",
                hostel=hostel,
                meta={"last_backup": str(last.created_at) if last else None},
                audit_action=AuditEvent.Action.BACKUP_FAILED,
            )
    return {"stale_hostels": stale, "checked_at": now().isoformat()}


# --- Backward-compatible task name (older code/UI expects this) ---
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def scheduled_backup_for_hostel(self, hostel_id):
    """Immediate manual backup for one hostel (owner-triggered 'schedule now')."""
    try:
        hostel = Hostel.objects.get(id=hostel_id)
    except Hostel.DoesNotExist:
        logger.error("Scheduled backup skipped: hostel %s not found.", hostel_id)
        return None
    try:
        snap = _do_backup(hostel, BackupPeriod.MANUAL, kind="scheduled", note="Auto backup")
        return str(snap.id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Scheduled backup failed for hostel %s.", hostel_id)
        if self.request.retries >= self.max_retries:
            dr_alert(
                "backup_failed",
                f"Manual backup failed for hostel {hostel_id}: {exc}",
                hostel=hostel,
                meta={"hostel_id": str(hostel_id)},
                audit_action=AuditEvent.Action.BACKUP_FAILED,
            )
        raise self.retry(exc=exc)
