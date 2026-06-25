from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedModel
from apps.tenants.models import Hostel
from apps.hostel.models import Bed

class Resident(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)

    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=30, blank=True)
    guardian_phone = models.CharField(max_length=30, blank=True)
    address = models.CharField(max_length=255, blank=True)

    # localdate (not now()) — a DateField must default to a date, otherwise a
    # datetime leaks in and DRF's DateField refuses to serialize it (500).
    join_date = models.DateField(default=timezone.localdate)
    leave_date = models.DateField(null=True, blank=True)

    STATUS = (
        ("active", "Active"),
        ("went_home", "Went Home"),
        ("left", "Left"),
    )
    status = models.CharField(max_length=20, choices=STATUS, default="active")

    current_bed = models.ForeignKey(Bed, null=True, blank=True, on_delete=models.SET_NULL)

    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    photo = models.ImageField(upload_to="residents/photos/", null=True, blank=True)
    id_document = models.FileField(upload_to="residents/ids/", null=True, blank=True)

    def __str__(self):
        return self.full_name

class BedAssignmentHistory(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name="bed_history")
    bed = models.ForeignKey(Bed, on_delete=models.CASCADE)
    start_at = models.DateTimeField(default=timezone.now)
    end_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-start_at"]
        indexes = [
            models.Index(fields=["resident", "end_at"]),
            models.Index(fields=["hostel", "bed"]),
        ]


class Stay(models.Model):
    resident = models.ForeignKey(
        Resident,
        on_delete=models.CASCADE,
        related_name="stays"
    )

    bed = models.ForeignKey(
        "hostel.Bed",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    check_in = models.DateField()
    check_out = models.DateField(null=True, blank=True)

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-check_in"]
        indexes = [
            models.Index(fields=["resident", "is_active"]),
        ]

    def __str__(self):
        return f"{self.resident.full_name} - {self.check_in}"