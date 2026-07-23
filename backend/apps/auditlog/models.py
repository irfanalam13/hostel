from django.conf import settings
from django.db import models, transaction
from django.utils import timezone

from apps.common.models import TimeStampedModel
from apps.tenants.models import Hostel

from .hashing import GENESIS_HASH, instance_hash


class AuditImmutableError(Exception):
    """Raised when something attempts to mutate or delete an audit record.

    Audit events are append-only. The only sanctioned way to remove rows is the
    retention/archiving path (:mod:`apps.auditlog.retention`), which exports
    them first and advances the chain checkpoint.
    """


class AuditLog(TimeStampedModel):
    """DEPRECATED legacy per-request logger. Kept only so historical rows and
    the (currently unwired) ``apps.common.audit`` middleware don't break. New
    code must use :class:`AuditEvent` via ``apps.auditlog.services.record_event``.
    """

    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, null=True, blank=True)
    user_id = models.CharField(max_length=64, blank=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=255)
    ip = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"{self.method} {self.path}"


class AuditChainState(models.Model):
    """Singleton head of the audit hash chain (always ``pk=1``).

    Holds the tip so an insert is O(1): lock this one row, read the last hash
    and sequence, append, write back. ``checkpoint_*`` records the point up to
    which old rows have been archived-and-pruned so verification can still run
    against the truncated tail.
    """

    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    sequence = models.BigIntegerField(default=0)
    last_hash = models.CharField(max_length=64, default=GENESIS_HASH)
    # Everything up to and including this sequence has been archived off and
    # deleted; the oldest surviving row's prev_hash must equal checkpoint_hash.
    checkpoint_sequence = models.BigIntegerField(default=0)
    checkpoint_hash = models.CharField(max_length=64, default=GENESIS_HASH)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Audit chain state"

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class AuditEventQuerySet(models.QuerySet):
    def delete(self):
        raise AuditImmutableError(
            "Audit events are append-only; use the retention/archiving path."
        )

    def _archive_delete(self):
        """Retention-only bypass. Callers MUST have archived the rows first."""
        return super().delete()


class AuditEventManager(models.Manager.from_queryset(AuditEventQuerySet)):
    @transaction.atomic
    def create_chained(self, **fields):
        """Insert one event, linking it into the tamper-evident hash chain.

        Serializes on the singleton chain head so concurrent writers (Celery
        workers + synchronous fallback) produce a strictly ordered, gap-free
        sequence. This is the ONLY sanctioned way to create an AuditEvent.
        """
        head = AuditChainState.objects.select_for_update().get_or_create(pk=1)[0]

        # Async payloads carry created_at as an ISO string (JSON transport).
        created_at = fields.get("created_at")
        if isinstance(created_at, str):
            from django.utils.dateparse import parse_datetime

            fields["created_at"] = parse_datetime(created_at) or timezone.now()
        fields.setdefault("created_at", timezone.now())
        # Never trust a caller-supplied hash/sequence.
        for reserved in ("sequence", "prev_hash", "content_hash"):
            fields.pop(reserved, None)

        sequence = head.sequence + 1
        prev_hash = head.last_hash or GENESIS_HASH

        # Build the instance first so Django applies field defaults ("" for
        # blank CharFields, {} for meta, etc.); the hash MUST cover the values
        # as they will be persisted, which is what the verifier re-reads.
        event = self.model(sequence=sequence, prev_hash=prev_hash, **fields)
        event.content_hash = instance_hash(event, prev_hash)
        event.save(force_insert=True)

        head.sequence = sequence
        head.last_hash = event.content_hash
        head.save(update_fields=["sequence", "last_hash", "updated_at"])
        return event


class AuditEvent(models.Model):
    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        PAYMENT = "payment", "Payment"
        VACATE = "vacate", "Vacate"
        EXPORT = "export", "Export"
        BACKUP = "backup", "Backup"
        RESTORE = "restore", "Restore"
        # --- Disaster recovery (Phase 4) ---
        BACKUP_FAILED = "backup_failed", "Backup failed"
        SNAPSHOT = "snapshot", "Snapshot created"
        RESTORE_STARTED = "restore_started", "Restore started"
        RESTORE_COMPLETED = "restore_completed", "Restore completed"
        RESTORE_FAILED = "restore_failed", "Restore failed"
        RETENTION = "retention", "Retention deletion"
        RETENTION_FAILED = "retention_failed", "Retention deletion failed"
        MAINTENANCE = "maintenance", "Maintenance mode change"
        # --- Security (Phase 10) ---
        ACCESS_DENIED = "access_denied", "Access denied"
        AUTH_FAILED = "auth_failed", "Authentication failed"
        # --- Operations governance (Phase 11) ---
        INCIDENT = "incident", "Incident lifecycle"
        ANNOUNCEMENT = "announcement", "System announcement"
        FEATURE_FLAG = "feature_flag", "Feature flag change"

    class Result(models.TextChoices):
        SUCCESS = "success", "Success"
        FAILURE = "failure", "Failure"
        DENIED = "denied", "Denied"

    id = models.BigAutoField(primary_key=True)

    # --- tamper-evident chain (Phase 7) ---
    sequence = models.BigIntegerField(null=True, blank=True, unique=True, db_index=True)
    prev_hash = models.CharField(max_length=64, blank=True, default="")
    content_hash = models.CharField(max_length=64, blank=True, default="", db_index=True)

    # Multi-hostel context (optional but useful) — the "where"
    hostel_id = models.UUIDField(null=True, blank=True, db_index=True)
    branch_id = models.UUIDField(null=True, blank=True, db_index=True)

    # --- who ---
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )

    # --- what ---
    action = models.CharField(max_length=32, choices=Action.choices, db_index=True)
    entity_type = models.CharField(max_length=64, blank=True, default="", db_index=True)
    entity_id = models.CharField(max_length=64, blank=True, default="", db_index=True)

    message = models.CharField(max_length=255, blank=True, default="")
    # --- why ---
    reason = models.CharField(max_length=255, blank=True, default="")
    # --- old value / new value ---  {"old": {...}, "new": {...}}
    changes = models.JSONField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)

    # --- request metadata / correlation ---
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    request_id = models.CharField(max_length=64, blank=True, default="", db_index=True)

    # --- result / status / timing ---
    result = models.CharField(
        max_length=16, choices=Result.choices, default=Result.SUCCESS, db_index=True
    )
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    # --- when --- (explicit default, NOT auto_now_add, so it is part of the hash)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    objects = AuditEventManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action", "-created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
        ]

    def __str__(self):
        return f"{self.created_at} {self.action} {self.entity_type}:{self.entity_id}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AuditImmutableError("Audit events are append-only and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditImmutableError("Audit events are append-only and cannot be deleted.")
