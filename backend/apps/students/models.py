from django.db import models
from apps.common.models import HostelScopedModel


class Student(HostelScopedModel):
    GENDER_CHOICES = [
        ("MALE", "Male"),
        ("FEMALE", "Female"),
        ("OTHER", "Other"),
    ]

    # ACTIVE = current resident; LEFT = former resident (checked out / vacated).
    # Single "former" state — legacy INACTIVE rows are migrated to LEFT.
    STATUS_CHOICES = [
        ("ACTIVE", "Active"),
        ("LEFT", "Left"),
    ]

    full_name = models.CharField(max_length=120)
    name_nepali = models.CharField(max_length=120, blank=True, default="")
    phone = models.CharField(max_length=30)
    address = models.CharField(max_length=255, blank=True, default="")
    
    guardian_name = models.CharField(max_length=120, blank=True, default="")
    guardian_phone = models.CharField(max_length=30, blank=True, default="")
    
    join_date = models.DateField()
    status = models.CharField(max_length=20, default="ACTIVE", choices=STATUS_CHOICES)

    # Extended profile details matching Admission Form
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default="OTHER")
    photo = models.ImageField(upload_to="students/photos/%Y/%m/", null=True, blank=True)
    citizenship_number = models.CharField(max_length=60, blank=True, default="")
    
    father_name = models.CharField(max_length=120, blank=True, default="")
    mother_name = models.CharField(max_length=120, blank=True, default="")
    
    emergency_contact_name = models.CharField(max_length=120, blank=True, default="")
    emergency_contact_phone = models.CharField(max_length=30, blank=True, default="")
    emergency_contact_relation = models.CharField(max_length=60, blank=True, default="")

    def __str__(self):
        return self.full_name


class StudentDocument(HostelScopedModel):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=50, default="citizenship")  # citizenship/photo/other
    file = models.FileField(upload_to="students/docs/%Y/%m/")
    