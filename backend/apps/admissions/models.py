from django.conf import settings
from django.db import models
from apps.common.models import HostelScopedModel


class AdmissionRequest(HostelScopedModel):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]
    SOURCE_CHOICES = [
        ("INTERNAL", "Internal"),
        ("PUBLIC", "Public"),
    ]

    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True, default="")
    address = models.CharField(max_length=255, blank=True, default="")
    guardian_name = models.CharField(max_length=120, blank=True, default="")
    guardian_phone = models.CharField(max_length=30, blank=True, default="")
    emergency_contact = models.CharField(max_length=30, blank=True, default="")
    preferred_join_date = models.DateField(null=True, blank=True)
    requested_bed = models.ForeignKey(
        "rooms.Bed",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admission_requests",
    )
    approved_bed = models.ForeignKey(
        "rooms.Bed",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_admission_requests",
    )
    student = models.OneToOneField(
        "students.Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admission_request",
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="INTERNAL")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    notes = models.TextField(blank=True, default="")
    decision_note = models.TextField(blank=True, default="")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_admissions",
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hostel", "status"]),
            models.Index(fields=["hostel", "phone"]),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.status})"
