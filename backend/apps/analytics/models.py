"""PWA analytics event store.

A single append-only ``AnalyticsEvent`` table records discrete telemetry from the
installed/in-browser app. High-frequency signals (cache hits/misses, sync
batches) arrive pre-aggregated as periodic summary events with a numeric
``value``, so we never write one row per network request.

Device type and browser are derived server-side from the User-Agent (reliable)
in services.parse_user_agent. Everything is tenant-scoped via ``hostel``.
"""
import uuid

from django.conf import settings
from django.db import models


class EventType(models.TextChoices):
    # Install funnel
    INSTALL_PROMPT = "INSTALL_PROMPT", "Install prompt shown"
    INSTALL_ACCEPTED = "INSTALL_ACCEPTED", "Install accepted"
    INSTALL_DISMISSED = "INSTALL_DISMISSED", "Install dismissed"
    INSTALLED = "INSTALLED", "Installed"
    # Updates
    UPDATE_AVAILABLE = "UPDATE_AVAILABLE", "Update available"
    UPDATE_APPLIED = "UPDATE_APPLIED", "Update applied"
    # Connectivity
    OFFLINE_SESSION = "OFFLINE_SESSION", "Offline session"  # value = seconds
    # Engagement
    FEATURE_USED = "FEATURE_USED", "Feature used"  # name = feature
    # Push
    PUSH_RECEIVED = "PUSH_RECEIVED", "Push received"
    PUSH_OPEN = "PUSH_OPEN", "Push opened"
    # Cache (value = count in batch)
    CACHE_HIT = "CACHE_HIT", "Cache hit"
    CACHE_MISS = "CACHE_MISS", "Cache miss"
    # Background sync (value = count in batch)
    SYNC_SUCCESS = "SYNC_SUCCESS", "Sync success"
    SYNC_FAILURE = "SYNC_FAILURE", "Sync failure"
    # Errors
    ERROR = "ERROR", "Client error"


class DeviceType(models.TextChoices):
    MOBILE = "MOBILE", "Mobile"
    TABLET = "TABLET", "Tablet"
    DESKTOP = "DESKTOP", "Desktop"
    UNKNOWN = "UNKNOWN", "Unknown"


class Browser(models.TextChoices):
    CHROME = "CHROME", "Chrome"
    SAFARI = "SAFARI", "Safari"
    FIREFOX = "FIREFOX", "Firefox"
    EDGE = "EDGE", "Edge"
    SAMSUNG = "SAMSUNG", "Samsung Internet"
    OPERA = "OPERA", "Opera"
    OTHER = "OTHER", "Other"


class AnalyticsEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    hostel = models.ForeignKey(
        "tenants.Hostel", on_delete=models.CASCADE, null=True, blank=True,
        related_name="analytics_events",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="analytics_events",
    )
    event_type = models.CharField(max_length=24, choices=EventType.choices)
    name = models.CharField(max_length=200, blank=True, default="")
    value = models.FloatField(default=0)

    device_type = models.CharField(max_length=10, choices=DeviceType.choices, default=DeviceType.UNKNOWN)
    browser = models.CharField(max_length=10, choices=Browser.choices, default=Browser.OTHER)
    platform = models.CharField(max_length=40, blank=True, default="")
    app_version = models.CharField(max_length=40, blank=True, default="")
    sw_version = models.CharField(max_length=40, blank=True, default="")

    occurred_at = models.DateTimeField(null=True, blank=True)  # client clock
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hostel", "event_type", "created_at"]),
            models.Index(fields=["hostel", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} ({self.created_at:%Y-%m-%d})"
