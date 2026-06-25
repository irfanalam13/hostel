from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import HostelScopedModel


class Notice(HostelScopedModel):
    TARGET_CHOICES = [
        ("ALL", "All"),
        ("BLOCK", "Block"),
        ("FLOOR", "Floor"),
        ("ROOM", "Room"),
        ("ROLE", "Role"),
    ]

    title = models.CharField(max_length=160)
    body = models.TextField()
    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES, default="ALL")
    target_value = models.CharField(max_length=120, blank=True, default="")
    is_pinned = models.BooleanField(default=False)
    published_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notices",
    )

    class Meta:
        ordering = ["-is_pinned", "-published_at"]
        indexes = [
            models.Index(fields=["hostel", "target_type", "is_pinned"]),
            models.Index(fields=["hostel", "published_at"]),
        ]

    def __str__(self):
        return self.title
