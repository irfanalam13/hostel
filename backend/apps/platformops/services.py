"""Operations-governance services: maintenance transitions, override reaping."""
import logging

from django.utils import timezone

logger = logging.getLogger("apps.platformops")


def start_maintenance(window, *, user=None, request=None):
    """Mark a window in-progress; optionally flip the system into DR read-only."""
    from .models import MaintenanceWindow

    window.status = MaintenanceWindow.Status.IN_PROGRESS
    window.save(update_fields=["status", "updated_at"])
    if window.enforce_read_only:
        from apps.backups import dr
        from apps.backups.models import DRMode

        dr.set_mode(DRMode.MAINTENANCE, reason=f"maintenance: {window.title}",
                    user=user, request=request)
    logger.warning("maintenance window started: %s", window.title)
    return window


def complete_maintenance(window, *, user=None, request=None):
    """Mark a window complete; return the system to normal if we forced DR."""
    from .models import MaintenanceWindow

    window.status = MaintenanceWindow.Status.COMPLETED
    window.save(update_fields=["status", "updated_at"])
    if window.enforce_read_only:
        from apps.backups import dr
        from apps.backups.models import DRMode

        if dr.get_mode() == DRMode.MAINTENANCE:
            dr.set_mode(DRMode.NORMAL, reason=f"maintenance complete: {window.title}",
                        user=user, request=request)
    logger.warning("maintenance window completed: %s", window.title)
    return window


def auto_transition_windows():
    """Beat task body: auto-start/complete windows that have reached their time.

    Only windows explicitly marked ``enforce_read_only`` are auto-driven for the
    DR side; timing transitions apply to all so the public status stays honest.
    """
    from .models import MaintenanceWindow

    now = timezone.now()
    started = completed = 0

    due = MaintenanceWindow.objects.filter(
        status=MaintenanceWindow.Status.SCHEDULED, scheduled_start__lte=now
    )
    for window in due:
        start_maintenance(window)
        started += 1

    ending = MaintenanceWindow.objects.filter(
        status=MaintenanceWindow.Status.IN_PROGRESS, scheduled_end__lte=now
    )
    for window in ending:
        complete_maintenance(window)
        completed += 1

    return {"started": started, "completed": completed}


def reap_expired_overrides():
    """Delete feature-flag overrides whose expiry has passed."""
    from .models import FeatureFlagOverride

    deleted, _ = FeatureFlagOverride.objects.filter(
        expires_at__isnull=False, expires_at__lte=timezone.now()
    ).delete()
    return {"deleted": deleted}
