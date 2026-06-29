from django.conf import settings
from django.db import models


class UserPresence(models.Model):
    """Lightweight per-user/hostel presence for the system-status dashboard.

    Updated by the client heartbeat (POST /api/dashboard/heartbeat/). "Online"
    is derived from ``last_seen`` being within a short window, so no background
    job is needed. DB-backed (not cache) so counts are correct across multiple
    Gunicorn/worker processes.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="presence"
    )
    hostel = models.ForeignKey(
        "tenants.Hostel", on_delete=models.CASCADE, related_name="user_presence"
    )
    last_seen = models.DateTimeField(auto_now=True)
    is_installed = models.BooleanField(default=False)  # running as an installed PWA
    sw_version = models.CharField(max_length=40, blank=True, default="")
    app_version = models.CharField(max_length=40, blank=True, default="")
    user_agent = models.CharField(max_length=300, blank=True, default="")

    class Meta:
        unique_together = ("user", "hostel")
        indexes = [
            models.Index(fields=["hostel", "last_seen"]),
        ]

    def __str__(self):
        return f"Presence(user={self.user_id}, hostel={self.hostel_id})"
