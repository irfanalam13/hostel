from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import HostelScopedModel


class EntryExitLog(HostelScopedModel):
    DIRECTION_CHOICES = [
        ("IN", "In"),
        ("OUT", "Out"),
    ]

    resident = models.ForeignKey(
        "residents.Resident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entry_exit_logs",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="entry_exit_logs",
    )
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    event_at = models.DateTimeField(default=timezone.now)
    purpose = models.CharField(max_length=120, blank=True, default="")
    note = models.CharField(max_length=255, blank=True, default="")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_entry_exit_logs",
    )

    class Meta:
        ordering = ["-event_at"]
        indexes = [models.Index(fields=["hostel", "event_at", "direction"])]


class LeaveRequest(HostelScopedModel):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
    ]

    resident = models.ForeignKey(
        "residents.Resident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leave_requests",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leave_requests",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING")
    decision_note = models.TextField(blank=True, default="")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_leave_requests",
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["hostel", "status", "start_date"])]


class VisitorLog(HostelScopedModel):
    resident = models.ForeignKey(
        "residents.Resident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visitor_logs",
    )
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="visitor_logs",
    )
    visitor_name = models.CharField(max_length=120)
    visitor_phone = models.CharField(max_length=30, blank=True, default="")
    relation = models.CharField(max_length=80, blank=True, default="")
    purpose = models.CharField(max_length=160, blank=True, default="")
    id_proof = models.CharField(max_length=120, blank=True, default="")
    check_in_at = models.DateTimeField(default=timezone.now)
    check_out_at = models.DateTimeField(null=True, blank=True)
    notes = models.CharField(max_length=255, blank=True, default="")
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_visitor_logs",
    )

    class Meta:
        ordering = ["-check_in_at"]
        indexes = [models.Index(fields=["hostel", "check_in_at"])]
