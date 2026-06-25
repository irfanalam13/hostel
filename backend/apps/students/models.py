from django.db import models
from apps.common.models import HostelScopedModel

class Student(HostelScopedModel):
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=255, blank=True, default="")
    guardian_name = models.CharField(max_length=120, blank=True, default="")
    guardian_phone = models.CharField(max_length=30, blank=True, default="")
    join_date = models.DateField()
    status = models.CharField(max_length=20, default="ACTIVE")  # ACTIVE/LEFT

    def __str__(self):
        return self.full_name

class StudentDocument(HostelScopedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=50, default="citizenship")  # citizenship/photo/other
    file = models.FileField(upload_to="students/docs/%Y/%m/")