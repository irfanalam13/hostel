"""Push-notification data model.

Four tables:

* ``PushSubscription``     – a Web Push endpoint for one user/device (VAPID).
* ``Notification``         – one logical notification (content + targeting +
                             schedule + status + denormalised delivery counts).
* ``NotificationRecipient``– per-user fan-out row: the user's inbox + read state.
* ``NotificationDelivery`` – per-subscription push attempt: retries + tracking.

Tenant isolation: ``Notification`` is hostel-scoped and recipients are always
resolved from active ``UserHostel`` memberships, so a notification can never
reach a user outside its hostel. ``PushSubscription`` is per-user (a device
belongs to a person, not a tenant) but records the hostel it was created under.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import HostelScopedModel, TimeStampedModel


class NotificationCategory(models.TextChoices):
    GENERAL = "GENERAL", "General"
    ADMISSION_APPROVED = "ADMISSION_APPROVED", "Admission approved"
    FEE_DUE = "FEE_DUE", "Fee due reminder"
    RENT_OVERDUE = "RENT_OVERDUE", "Rent overdue"
    VISITOR_APPROVAL = "VISITOR_APPROVAL", "Visitor approval"
    ROOM_CHANGED = "ROOM_CHANGED", "Room changed"
    MAINTENANCE_COMPLETED = "MAINTENANCE_COMPLETED", "Maintenance completed"
    COMPLAINT_RESOLVED = "COMPLAINT_RESOLVED", "Complaint resolved"
    EMERGENCY = "EMERGENCY", "Emergency announcement"
    STAFF_NOTICE = "STAFF_NOTICE", "Staff notice"
    INVENTORY_ALERT = "INVENTORY_ALERT", "Inventory alert"


class NotificationPriority(models.TextChoices):
    NORMAL = "NORMAL", "Normal"
    HIGH = "HIGH", "High"
    URGENT = "URGENT", "Urgent"


class AudienceType(models.TextChoices):
    ALL = "ALL", "All hostel members"
    ROLE = "ROLE", "Specific roles"
    USER = "USER", "Specific users"


class NotificationStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    SCHEDULED = "SCHEDULED", "Scheduled"
    SENDING = "SENDING", "Sending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    CANCELED = "CANCELED", "Canceled"


class DeliveryStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"
    EXPIRED = "EXPIRED", "Expired"  # subscription gone (404/410) — pruned


class PushSubscription(TimeStampedModel):
    """A browser Web Push subscription (one per device/user)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="push_subscriptions"
    )
    # Hostel the subscription was created under (context only; a device receives
    # whatever notifications target its user across hostels).
    hostel = models.ForeignKey(
        "tenants.Hostel", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="push_subscriptions",
    )
    endpoint = models.TextField(unique=True)
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    user_agent = models.CharField(max_length=300, blank=True, default="")
    is_active = models.BooleanField(default=True)
    failure_count = models.PositiveIntegerField(default=0)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"PushSubscription(user={self.user_id}, …{self.endpoint[-12:]})"

    def as_subscription_info(self) -> dict:
        """Shape required by pywebpush."""
        return {"endpoint": self.endpoint, "keys": {"p256dh": self.p256dh, "auth": self.auth}}


class Notification(HostelScopedModel):
    """A logical notification, fanned out to recipients on dispatch."""

    category = models.CharField(
        max_length=32, choices=NotificationCategory.choices, default=NotificationCategory.GENERAL
    )
    priority = models.CharField(
        max_length=10, choices=NotificationPriority.choices, default=NotificationPriority.NORMAL
    )
    title = models.CharField(max_length=160)
    body = models.TextField(blank=True, default="")
    url = models.CharField(max_length=300, blank=True, default="/dashboard")
    icon = models.CharField(max_length=300, blank=True, default="")
    tag = models.CharField(max_length=80, blank=True, default="")
    data = models.JSONField(default=dict, blank=True)

    # Targeting
    audience = models.CharField(
        max_length=10, choices=AudienceType.choices, default=AudienceType.ALL
    )
    target_roles = models.JSONField(default=list, blank=True)  # used when audience=ROLE

    # Lifecycle
    status = models.CharField(
        max_length=12, choices=NotificationStatus.choices, default=NotificationStatus.DRAFT
    )
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    # Denormalised tracking counters (kept current by services.recompute_counts)
    recipients_count = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    read_count = models.PositiveIntegerField(default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="notifications_created",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hostel", "status", "scheduled_at"]),
            models.Index(fields=["hostel", "category"]),
        ]

    def __str__(self):
        return f"{self.get_category_display()}: {self.title}"

    @property
    def require_interaction(self) -> bool:
        return self.priority in (NotificationPriority.HIGH, NotificationPriority.URGENT)

    def to_push_payload(self) -> dict:
        """The JSON delivered to the service worker's ``push`` handler."""
        return {
            "title": self.title,
            "body": self.body,
            "url": self.url or "/dashboard",
            "icon": self.icon or "/icons/icon-192.png",
            "tag": self.tag or str(self.id),
            "requireInteraction": self.require_interaction,
            "data": {"category": self.category, "notificationId": str(self.id), **(self.data or {})},
        }


class NotificationRecipient(TimeStampedModel):
    """Per-user fan-out: the recipient's inbox entry + read/unread state."""

    notification = models.ForeignKey(
        Notification, on_delete=models.CASCADE, related_name="recipients"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications_received"
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    # True once at least one of the user's subscriptions accepted the push.
    delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("notification", "user")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "is_read"]),
        ]

    def __str__(self):
        return f"{self.user_id} ← {self.notification_id}"

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at", "updated_at"])


class NotificationDelivery(TimeStampedModel):
    """One push attempt to one subscription — the unit of retry + tracking."""

    recipient = models.ForeignKey(
        NotificationRecipient, on_delete=models.CASCADE, related_name="deliveries"
    )
    subscription = models.ForeignKey(
        PushSubscription, on_delete=models.SET_NULL, null=True, related_name="deliveries"
    )
    status = models.CharField(
        max_length=10, choices=DeliveryStatus.choices, default=DeliveryStatus.PENDING
    )
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True, default="")
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "next_retry_at"]),
        ]

    def __str__(self):
        return f"Delivery({self.status}, attempts={self.attempts})"
