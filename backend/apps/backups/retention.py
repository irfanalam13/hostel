"""Backup retention policy.

Keeps the N most-recent backups per hostel per bucket and deletes the rest:

    daily   → keep 7        weekly  → keep 4        monthly → keep 12

Pre-restore snapshots and manual backups are NEVER auto-deleted (manual ones
are an operator's deliberate artifact; pre-restore ones are recovery anchors).
Every deletion is audited; deletion failures raise a DR alert.
"""

import logging

from django.conf import settings

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.tenants.models import Hostel

from .alerts import dr_alert
from .models import BackupPeriod, BackupSnapshot

logger = logging.getLogger("apps.backups")

# Buckets subject to automatic retention (manual / pre_restore are exempt).
MANAGED_PERIODS = (BackupPeriod.DAILY, BackupPeriod.WEEKLY, BackupPeriod.MONTHLY)


def default_policy() -> dict:
    return dict(getattr(settings, "BACKUP_RETENTION", {"daily": 7, "weekly": 4, "monthly": 12}))


def storage_usage() -> dict:
    """Storage tracking: count + total bytes per period across all hostels."""
    usage = {}
    for period, _ in BackupPeriod.choices:
        qs = BackupSnapshot.objects.filter(period=period)
        total = sum(qs.values_list("size_bytes", flat=True))
        usage[period] = {"count": qs.count(), "bytes": total}
    usage["total_bytes"] = sum(v["bytes"] for k, v in usage.items() if isinstance(v, dict))
    return usage


def _delete_snapshot(snap: BackupSnapshot) -> bool:
    """Delete one snapshot's file + row. Returns True on success."""
    try:
        if snap.file:
            snap.file.delete(save=False)
        snap.delete()
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("Retention: failed to delete backup %s", snap.id)
        dr_alert(
            "retention_deletion_failed",
            f"Failed to delete backup {snap.id}: {exc}",
            hostel=getattr(snap, "hostel", None),
            meta={"backup_id": str(snap.id)},
            audit_action=AuditEvent.Action.RETENTION_FAILED,
        )
        return False


def apply_retention(policy: dict | None = None) -> dict:
    """Enforce retention across every hostel. Returns a summary dict."""
    policy = policy or default_policy()
    summary = {"deleted": 0, "failed": 0, "by_period": {}, "errors": []}

    for hostel in Hostel.objects.all():
        for period in MANAGED_PERIODS:
            keep = int(policy.get(period, 0) or 0)
            qs = BackupSnapshot.objects.filter(hostel=hostel, period=period).order_by("-created_at")
            stale = list(qs[keep:]) if keep > 0 else list(qs)
            for snap in stale:
                ok = _delete_snapshot(snap)
                bucket = summary["by_period"].setdefault(period, {"deleted": 0, "failed": 0})
                if ok:
                    summary["deleted"] += 1
                    bucket["deleted"] += 1
                    record_event(
                        action=AuditEvent.Action.RETENTION, hostel=hostel,
                        entity_type="backup.snapshot", entity_id=str(snap.id),
                        message=f"Retention deleted {period} backup {snap.id} for {hostel.code}",
                        meta={"period": period, "keep": keep},
                    )
                else:
                    summary["failed"] += 1
                    bucket["failed"] += 1

    summary["storage"] = storage_usage()
    logger.info("Retention applied: %s deleted, %s failed", summary["deleted"], summary["failed"])
    return summary
