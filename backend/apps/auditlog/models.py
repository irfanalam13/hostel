from django.db import models
from apps.common.models import TimeStampedModel
from apps.tenants.models import Hostel
from django.conf import settings

class AuditLog(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE, null=True, blank=True)
    user_id = models.CharField(max_length=64, blank=True)
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=255)
    ip = models.CharField(max_length=64, blank=True)

    def __str__(self):
        return f"{self.method} {self.path}"
    
    


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

    id = models.BigAutoField(primary_key=True)

    # Multi-hostel context (optional but useful)
    hostel_id = models.UUIDField(null=True, blank=True, db_index=True)
    branch_id = models.UUIDField(null=True, blank=True, db_index=True)

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_events",
    )

    action = models.CharField(max_length=32, choices=Action.choices, db_index=True)
    entity_type = models.CharField(max_length=64, blank=True, default="", db_index=True)
    entity_id = models.CharField(max_length=64, blank=True, default="", db_index=True)

    message = models.CharField(max_length=255, blank=True, default="")
    meta = models.JSONField(default=dict, blank=True)

    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.created_at} {self.action} {self.entity_type}:{self.entity_id}"