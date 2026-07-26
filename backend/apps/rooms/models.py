from django.conf import settings
from django.db import models
from apps.common.models import HostelScopedModel

class Block(HostelScopedModel):
    name = models.CharField(max_length=80)
    code = models.CharField(max_length=20, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        unique_together = ("hostel", "name")
        ordering = ["name"]

    def __str__(self):
        return self.name

class Floor(HostelScopedModel):
    block = models.ForeignKey(Block, on_delete=models.CASCADE, related_name="floors")
    name = models.CharField(max_length=80)
    number = models.IntegerField(default=0)

    class Meta:
        unique_together = ("block", "name")
        ordering = ["block__name", "number", "name"]

    def __str__(self):
        return f"{self.block.name} - {self.name}"

class Room(HostelScopedModel):
    block = models.ForeignKey(Block, on_delete=models.SET_NULL, null=True, blank=True, related_name="rooms")
    floor_ref = models.ForeignKey(Floor, on_delete=models.SET_NULL, null=True, blank=True, related_name="rooms")
    room_no = models.CharField(max_length=20)
    floor = models.CharField(max_length=20, blank=True, default="")
    room_type = models.CharField(max_length=40, blank=True, default="Standard")
    capacity = models.IntegerField(default=1)
    rent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amenities = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=20, default="ACTIVE")  # ACTIVE/MAINTENANCE/INACTIVE
    gender_type = models.CharField(max_length=10, default="ANY")  # MALE/FEMALE/ANY

    class Meta:
        unique_together = ("hostel", "room_no")
        ordering = ["room_no"]

    def __str__(self):
        return self.room_no

class Bed(HostelScopedModel):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="beds")
    bed_no = models.CharField(max_length=20)
    status = models.CharField(max_length=20, default="AVAILABLE")  # AVAILABLE/OCCUPIED/MAINTENANCE

    class Meta:
        unique_together = ("room", "bed_no")

class BedAssignment(HostelScopedModel):
    REASON_CHOICES = [
        ("INITIAL", "Initial Assignment"),  # created at admission approval
        ("TRANSFER", "Bed Transfer"),       # created by a room/bed change
    ]

    bed = models.ForeignKey(Bed, on_delete=models.PROTECT, related_name="assignments")
    student = models.ForeignKey("students.Student", on_delete=models.PROTECT, related_name="bed_assignments")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    # Transfer metadata: the chain of a student's assignments (linked by
    # previous_assignment) is the authoritative room/bed history.
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default="INITIAL")
    note = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    previous_assignment = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        indexes = [models.Index(fields=["hostel","is_active"])]
        constraints = [
            models.UniqueConstraint(
                fields=["bed"],
                condition=models.Q(is_active=True),
                name="unique_active_assignment_per_bed",
            ),
            models.UniqueConstraint(
                fields=["student"],
                condition=models.Q(is_active=True),
                name="unique_active_assignment_per_student",
            ),
        ]
