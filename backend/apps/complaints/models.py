from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import HostelScopedModel


class Complaint(HostelScopedModel):
    PRIORITY_CHOICES = [
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("URGENT", "Urgent"),
    ]
    STATUS_CHOICES = [
        ("OPEN", "Open"),
        ("IN_PROGRESS", "In Progress"),
        ("RESOLVED", "Resolved"),
        ("CLOSED", "Closed"),
    ]

    resident = models.ForeignKey(
        "residents.Resident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
    )
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True, default="")
    category = models.CharField(max_length=80, default="General")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="MEDIUM")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="OPEN")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_complaints",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hostel", "status", "priority"]),
            models.Index(fields=["hostel", "category"]),
        ]

    def mark_status(self, status_value):
        self.status = status_value
        self.resolved_at = timezone.now() if status_value in {"RESOLVED", "CLOSED"} else None


class ComplaintComment(HostelScopedModel):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaint_comments",
    )
    body = models.TextField()
    internal = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at"]


class ComplaintAttachment(HostelScopedModel):
    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="complaints/%Y/%m/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaint_attachments",
    )

    class Meta:
        ordering = ["-created_at"]
