from django.db import models
from apps.common.models import TimeStampedModel
from apps.tenants.models import Hostel
import uuid

class Room(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    number = models.CharField(max_length=20)
    floor = models.CharField(max_length=20, blank=True)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("hostel", "number")]

    def __str__(self):
        return f"Room {self.number}"

class Bed(TimeStampedModel):
    hostel = models.ForeignKey(Hostel, on_delete=models.CASCADE)
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="beds")
    label = models.CharField(max_length=20)  # e.g. A, B, 1, 2

    class Meta:
        unique_together = [("room", "label")]

    def __str__(self):
        return f"{self.room.number}-{self.label}"
    
    

def generate_hostel_code():
    return uuid.uuid4().hex[:6].upper()