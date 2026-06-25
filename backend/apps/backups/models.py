from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel
from apps.tenants.models import Hostel


class BackupPeriod(models.TextChoices):
    MANUAL = "manual", "Manual"
    DAILY = "daily", "Daily"
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    PRE_RESTORE = "pre_restore", "Pre-restore snapshot"


def backup_upload_path(instance, filename):
    """Organise backups on disk by retention bucket: backups/<period>/<file>."""
    period = getattr(instance, "period", None) or BackupPeriod.MANUAL
    return f"backups/{period}/{filename}"


class BackupSnapshot(TimeStampedModel):
    """A single point-in-time export of one hostel's canonical (Track A) data.

    Phase 4 adds the metadata needed to treat a snapshot as a verifiable,
    retention-managed disaster-recovery artifact rather than a plain file.
    """

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="backups")
    file = models.FileField(upload_to=backup_upload_path)
    # Legacy free-form classification (kept for backward compatibility).
    kind = models.CharField(max_length=20, default="manual")  # manual/scheduled
    note = models.CharField(max_length=255, blank=True)

    # --- Disaster-recovery metadata (Phase 4) ---
    period = models.CharField(
        max_length=20, choices=BackupPeriod.choices, default=BackupPeriod.MANUAL, db_index=True
    )
    schema_version = models.PositiveIntegerField(default=0)
    checksum = models.CharField(max_length=64, blank=True, default="")  # sha256 hex
    size_bytes = models.BigIntegerField(default=0)
    compressed = models.BooleanField(default=False)
    # None = not yet validated; True/False = last validation result.
    is_valid = models.BooleanField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["hostel", "created_at"]),
            models.Index(fields=["hostel", "period", "created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.hostel.code} {self.period} backup {self.created_at:%Y-%m-%d %H:%M}"


class RestoreRun(TimeStampedModel):
    """Audit + control record for a single restore (or dry-run) operation."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        DRY_RUN = "dry_run", "Dry run"

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, related_name="restore_runs")
    backup = models.ForeignKey(
        BackupSnapshot, on_delete=models.SET_NULL, null=True, blank=True, related_name="restores"
    )
    # Snapshot taken of the live data immediately before a destructive restore.
    pre_restore_snapshot = models.ForeignKey(
        BackupSnapshot, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    dry_run = models.BooleanField(default=False)
    force = models.BooleanField(default=False)

    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    schema_version = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # before/after row counts, validation report, integrity results
    stats = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["hostel", "created_at"])]

    def __str__(self):
        return f"Restore[{self.status}] {self.hostel_id} @ {self.created_at:%Y-%m-%d %H:%M}"


class DRMode(models.TextChoices):
    NORMAL = "normal", "Normal"
    MAINTENANCE = "maintenance", "Maintenance (read-only)"
    EMERGENCY = "emergency", "Emergency restore (admin-only)"


class DRState(models.Model):
    """Singleton holding the system-wide disaster-recovery mode.

    Always row id=1. Use :meth:`get_solo` / :meth:`set_mode` rather than
    creating rows directly.
    """

    singleton_id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    mode = models.CharField(max_length=20, choices=DRMode.choices, default=DRMode.NORMAL)
    reason = models.CharField(max_length=255, blank=True, default="")
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    changed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Disaster-recovery state"

    def __str__(self):
        return f"DR mode: {self.mode}"

    @classmethod
    def get_solo(cls) -> "DRState":
        obj, _ = cls.objects.get_or_create(singleton_id=1)
        return obj

    @classmethod
    def set_mode(cls, mode: str, *, reason: str = "", user=None) -> "DRState":
        obj = cls.get_solo()
        obj.mode = mode
        obj.reason = (reason or "")[:255]
        obj.changed_by = user if (user is not None and getattr(user, "pk", None)) else None
        obj.save()
        return obj
