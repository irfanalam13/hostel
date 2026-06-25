from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedModel
from apps.tenants.models import Hostel
from apps.residents.models import Resident

class Attendance(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    resident = models.ForeignKey(Resident, on_delete=models.CASCADE, related_name="attendance")

    date = models.DateField(default=timezone.now)

    STATUS = (
        ("present", "Present"),
        ("absent", "Absent"),
        ("went_home", "Went Home"),
    )
    status = models.CharField(max_length=20, choices=STATUS, default="present")
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("resident", "date")]
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["hostel", "date"]),
            models.Index(fields=["resident", "date"]),
        ]