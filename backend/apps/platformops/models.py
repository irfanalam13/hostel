"""Phase 11 — Operations governance.

Platform-global (not tenant-scoped) operational surfaces owned by platform
operators (``is_superuser``):

* :class:`Announcement` — system-wide banners/notices shown to users.
* :class:`MaintenanceWindow` — pre-announced scheduled maintenance; can flip the
  existing DR read-only mode automatically when it starts.
* :class:`Incident` / :class:`IncidentUpdate` — incident tracking with a public
  status timeline.
* :class:`FeatureFlag` / :class:`FeatureFlagOverride` — a real feature-flag
  engine: master switch, percentage rollout, tenant/role targeting, per-target
  overrides with expiry, and a per-flag kill switch.
"""
from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.common.models import TimeStampedModel


class Level(models.TextChoices):
    INFO = "info", "Info"
    WARNING = "warning", "Warning"
    CRITICAL = "critical", "Critical"


class Audience(models.TextChoices):
    ALL = "all", "Everyone"
    STAFF = "staff", "Staff & admins"
    ADMINS = "admins", "Admins only"


class Announcement(TimeStampedModel):
    """A system-wide banner/announcement surfaced to users."""

    title = models.CharField(max_length=200)
    body = models.TextField(blank=True, default="")
    level = models.CharField(max_length=16, choices=Level.choices, default=Level.INFO)
    audience = models.CharField(max_length=16, choices=Audience.choices, default=Audience.ALL)

    is_active = models.BooleanField(default=True)
    dismissible = models.BooleanField(default=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    @property
    def live(self) -> bool:
        now = timezone.now()
        if not self.is_active:
            return False
        if self.starts_at and self.starts_at > now:
            return False
        if self.ends_at and self.ends_at < now:
            return False
        return True


class MaintenanceWindow(TimeStampedModel):
    """A pre-announced maintenance window."""

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Scheduled"
        IN_PROGRESS = "in_progress", "In progress"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.SCHEDULED)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    # When it starts, drive the existing DR read-only mode (apps.backups.dr).
    enforce_read_only = models.BooleanField(default=False)
    # Free-form list of affected services/components.
    components = models.JSONField(default=list, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        ordering = ["-scheduled_start"]

    def __str__(self):
        return f"{self.title} ({self.status})"

    @property
    def is_current(self) -> bool:
        return self.status == self.Status.IN_PROGRESS


class Incident(TimeStampedModel):
    """An operational incident with a status timeline."""

    class Severity(models.TextChoices):
        SEV1 = "sev1", "SEV1 — Critical"
        SEV2 = "sev2", "SEV2 — Major"
        SEV3 = "sev3", "SEV3 — Minor"
        SEV4 = "sev4", "SEV4 — Low"

    class Status(models.TextChoices):
        INVESTIGATING = "investigating", "Investigating"
        IDENTIFIED = "identified", "Identified"
        MONITORING = "monitoring", "Monitoring"
        RESOLVED = "resolved", "Resolved"

    title = models.CharField(max_length=200)
    summary = models.TextField(blank=True, default="")
    severity = models.CharField(max_length=8, choices=Severity.choices, default=Severity.SEV3)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.INVESTIGATING, db_index=True
    )
    components = models.JSONField(default=list, blank=True)
    is_public = models.BooleanField(default=False, help_text="Visible on the public status feed.")

    started_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"[{self.severity}] {self.title}"

    @property
    def is_open(self) -> bool:
        return self.status != self.Status.RESOLVED


class IncidentUpdate(TimeStampedModel):
    """One entry on an incident's timeline (append-only in practice)."""

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name="updates")
    status = models.CharField(max_length=16, choices=Incident.Status.choices)
    message = models.TextField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.incident_id} @ {self.created_at}"


class FeatureFlag(TimeStampedModel):
    """A global feature flag with rollout + targeting + kill switch."""

    key = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=200, blank=True, default="")
    description = models.TextField(blank=True, default="")

    # Master switch. When False the flag is off for everyone (unless a specific
    # override says otherwise) — evaluated after the kill switch.
    is_active = models.BooleanField(default=False)
    # Emergency per-flag kill: forces OFF for everyone, overrides everything.
    kill = models.BooleanField(default=False)
    # 0-100 deterministic percentage rollout (by tenant, else user, else global).
    rollout_percentage = models.PositiveSmallIntegerField(default=0)

    # Targeting (lists of hostel UUIDs as strings / role codes). Empty = no filter.
    allowed_hostels = models.JSONField(default=list, blank=True)
    blocked_hostels = models.JSONField(default=list, blank=True)
    allowed_roles = models.JSONField(default=list, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return self.key


class FeatureFlagOverride(TimeStampedModel):
    """Explicit per-tenant or per-user override, optionally time-boxed."""

    flag = models.ForeignKey(FeatureFlag, on_delete=models.CASCADE, related_name="overrides")
    hostel_id = models.UUIDField(null=True, blank=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.CASCADE, related_name="feature_overrides",
    )
    # Whether the override grants (True) or denies (False) the feature.
    enabled = models.BooleanField(default=True)
    reason = models.CharField(max_length=255, blank=True, default="")

    # Scheduling window: the override only applies while active AND within
    # [starts_at, expires_at) (either bound may be null = open-ended).
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    # Revocation: a revoked override is kept for the audit trail but never
    # applied. Revoke sets this False (distinct from deleting the row).
    is_active = models.BooleanField(default=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                # An override targets a tenant, a user, or (rarely) both — but
                # not neither.
                condition=models.Q(hostel_id__isnull=False) | models.Q(user__isnull=False),
                name="featureflagoverride_has_target",
            ),
        ]

    def __str__(self):
        target = self.user_id or self.hostel_id or "?"
        return f"{self.flag_id}:{target}={self.enabled}"

    @property
    def is_live(self) -> bool:
        """True when this override should be applied right now."""
        if not self.is_active:
            return False
        now = timezone.now()
        if self.starts_at is not None and self.starts_at > now:
            return False
        if self.expires_at is not None and self.expires_at <= now:
            return False
        return True

    @property
    def schedule_state(self) -> str:
        """Human-readable lifecycle state for the UI."""
        if not self.is_active:
            return "revoked"
        now = timezone.now()
        if self.starts_at is not None and self.starts_at > now:
            return "scheduled"
        if self.expires_at is not None and self.expires_at <= now:
            return "expired"
        return "active"
