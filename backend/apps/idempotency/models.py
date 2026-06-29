from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class IdempotencyRecord(TimeStampedModel):
    """One processed (or in-progress) offline-sync request, keyed by the client's
    Idempotency-Key. Lets a replayed request return the original result instead of
    creating a duplicate. ``status_code == 0`` marks an in-progress reservation.
    """

    key = models.CharField(max_length=200, unique=True, db_index=True)
    hostel_id = models.UUIDField(null=True, blank=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="idempotency_records",
    )
    method = models.CharField(max_length=10)
    path = models.CharField(max_length=300)
    # sha256 of the raw request body — used to reject Idempotency-Key reuse with a
    # different payload and to verify client-sent X-Payload-Checksum integrity.
    request_hash = models.CharField(max_length=64, blank=True, default="")
    status_code = models.PositiveIntegerField(default=0)
    response_body = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hostel_id", "created_at"]),
        ]

    def __str__(self):
        return f"{self.key} {self.method} {self.path} -> {self.status_code}"
