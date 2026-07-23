import uuid
from django.db import models
from django.conf import settings

class TimeStampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True

class HostelScopedModel(TimeStampedModel):
    hostel = models.ForeignKey("tenants.Hostel", on_delete=models.CASCADE, related_name="%(class)s_items")
    class Meta:
        abstract = True

class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    class Meta:
        abstract = True

class FileUpload(TimeStampedModel):
    file = models.FileField(upload_to="uploads/%Y/%m/")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)