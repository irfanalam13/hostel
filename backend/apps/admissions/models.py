from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import HostelScopedModel, SoftDeleteModel


class SoftDeleteQuerySet(models.QuerySet):
    def delete(self):
        return self.update(is_deleted=True)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).filter(is_deleted=False)

    def all_with_deleted(self):
        return SoftDeleteQuerySet(self.model, using=self._db)


class AdmissionRequest(HostelScopedModel, SoftDeleteModel):
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("UNDER_REVIEW", "Under Review"),
        ("VERIFICATION_PENDING", "Verification Pending"),
        ("INTERVIEW_REQUIRED", "Interview Required"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("WAITLISTED", "Waitlisted"),
    ]
    
    SOURCE_CHOICES = [
        ("INTERNAL", "Internal"),
        ("PUBLIC", "Public"),
        ("WALK_IN", "Walk In"),
        ("WEBSITE", "Website"),
        ("REFERRAL", "Referral"),
    ]
    GENDER_CHOICES = [
        ("MALE", "Male"),
        ("FEMALE", "Female"),
        ("OTHER", "Other"),
    ]
    LEVEL_CHOICES = [
        ("SEE", "SEE"),
        ("PLUS2", "+2"),
        ("BACHELOR", "Bachelor"),
        ("MASTER", "Master"),
        ("OTHER", "Other"),
    ]
    TIMING_CHOICES = [
        ("MORNING", "Morning"),
        ("DAY", "Day"),
        ("EVENING", "Evening"),
    ]
    FOOD_CHOICES = [
        ("VEGETARIAN", "Vegetarian"),
        ("EGGITARIAN", "Only Egg"),
        ("NON_VEGETARIAN", "Non Vegetarian"),
    ]
    BLOOD_CHOICES = [
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
        ("O+", "O+"),
        ("O-", "O-"),
        ("UNKNOWN", "Unknown"),
    ]
    MARITAL_CHOICES = [
        ("SINGLE", "Single"),
        ("MARRIED", "Married"),
        ("OTHER", "Other"),
    ]
    ROOM_TYPE_CHOICES = [
        ("SINGLE", "Single"),
        ("DOUBLE", "Double"),
        ("TRIPLE", "Triple"),
        ("FOUR_SHARING", "Four Sharing"),
    ]
    PAYMENT_STATUS_CHOICES = [
        ("PAID", "Paid"),
        ("PENDING", "Pending"),
        ("PARTIAL", "Partial"),
    ]

    # Section 1: Application Information
    application_number = models.CharField(max_length=40, blank=True, db_index=True)
    application_date = models.DateField(default=timezone.localdate)
    application_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    form_number = models.CharField(max_length=12, blank=True, default="")
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default="INTERNAL")

    # Section 2: Student Profile
    full_name = models.CharField(max_length=120)  # English, uppercase validation in serializer
    name_nepali = models.CharField(max_length=120, blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=20, choices=GENDER_CHOICES, default="MALE")
    phone = models.CharField(max_length=30)
    alternate_phone = models.CharField(max_length=30, blank=True, default="")
    email = models.EmailField(max_length=30, blank=True, default="")
    photo = models.ImageField(upload_to="admissions/photos/%Y/%m/", null=True, blank=True)

    # Address Details
    province = models.CharField(max_length=100, blank=True, default="")
    district = models.CharField(max_length=100, blank=True, default="")
    municipality = models.CharField(max_length=100, blank=True, default="")
    ward_number = models.CharField(max_length=10, blank=True, default="")
    street_tole = models.CharField(max_length=150, blank=True, default="")

    # Temporary Address Details
    temp_province = models.CharField(max_length=100, blank=True, default="")
    temp_district = models.CharField(max_length=100, blank=True, default="")
    temp_municipality = models.CharField(max_length=100, blank=True, default="")
    temp_ward_number = models.CharField(max_length=10, blank=True, default="")
    temp_street_tole = models.CharField(max_length=150, blank=True, default="")

    # Identity
    citizenship_number = models.CharField(max_length=15, blank=True, default="")
    citizenship_issue_date = models.DateField(null=True, blank=True)
    citizenship_issue_district = models.CharField(max_length=100, blank=True, default="")
    nationality = models.CharField(max_length=80, default="Nepal")
    religion = models.CharField(max_length=60, blank=True, default="")
    blood_group = models.CharField(max_length=10, choices=BLOOD_CHOICES, default="UNKNOWN")
    marital_status = models.CharField(max_length=20, choices=MARITAL_CHOICES, default="SINGLE")

    # Health
    medical_condition = models.TextField(blank=True, default="")
    disability = models.CharField(max_length=150, blank=True, default="")

    # Emergency Contact
    emergency_contact_name = models.CharField(max_length=120, blank=True, default="")
    emergency_contact_phone = models.CharField(max_length=30, blank=True, default="")
    emergency_contact_relation = models.CharField(max_length=60, blank=True, default="")

    # Section 3: Education
    educational_institute = models.CharField(max_length=150, blank=True, default="")
    current_level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default="OTHER")
    faculty = models.CharField(max_length=80, blank=True, default="")
    roll_number = models.CharField(max_length=40, blank=True, default="")
    class_timing = models.CharField(max_length=20, choices=TIMING_CHOICES, default="DAY")
    hostel_stay_duration = models.IntegerField(default=12, help_text="Duration in months")
    expected_checkout_date = models.DateField(null=True, blank=True)

    # Section 4: Food Preference
    food_preference = models.CharField(max_length=30, choices=FOOD_CHOICES, default="NON_VEGETARIAN")
    food_allergy = models.CharField(max_length=150, blank=True, default="")
    special_diet = models.CharField(max_length=150, blank=True, default="")

    # Section 5: Guardian Information
    father_name = models.CharField(max_length=120, blank=True, default="")
    father_phone = models.CharField(max_length=30, blank=True, default="")
    father_occupation = models.CharField(max_length=100, blank=True, default="")
    mother_name = models.CharField(max_length=120, blank=True, default="")
    mother_phone = models.CharField(max_length=30, blank=True, default="")
    mother_occupation = models.CharField(max_length=100, blank=True, default="")
    spouse_name = models.CharField(max_length=120, blank=True, default="")
    spouse_phone = models.CharField(max_length=30, blank=True, default="")
    spouse_occupation = models.CharField(max_length=100, blank=True, default="")

    local_guardian_name = models.CharField(max_length=120, blank=True, default="")
    local_guardian_phone = models.CharField(max_length=30, blank=True, default="")
    local_guardian_address = models.CharField(max_length=255, blank=True, default="")
    local_guardian_occupation = models.CharField(max_length=100, blank=True, default="")
    local_guardian_relation = models.CharField(max_length=60, blank=True, default="")
    guardian_citizenship = models.CharField(max_length=60, blank=True, default="")
    guardian_email = models.EmailField(blank=True, default="")

    # Section 6: Hostel Allocation
    preferred_room_type = models.CharField(max_length=30, choices=ROOM_TYPE_CHOICES, default="DOUBLE")
    preferred_floor = models.CharField(max_length=40, blank=True, default="")
    preferred_room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_admission_requests",
    )

    preferred_bed = models.ForeignKey(
        "rooms.Bed",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preferred_admission_requests",
    )
    
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
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_admissions",
    )
    assigned_date = models.DateTimeField(null=True, blank=True)

    student = models.OneToOneField(
        "students.Student",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="admission_request",
    )

    # Section 7: Admission Decision
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="PENDING")
    rejection_reason = models.TextField(blank=True, default="")
    notes = models.TextField(blank=True, default="")  # custom notes
    decision_note = models.TextField(blank=True, default="")
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_admissions",
    )
    decided_at = models.DateTimeField(null=True, blank=True)

    # Section 8: Official Use Only
    booking_date = models.DateField(null=True, blank=True)
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    security_deposit = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    admission_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    scholarship = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    receipt_number = models.CharField(max_length=60, blank=True, default="")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default="PENDING")
    remarks = models.TextField(blank=True, default="")

    objects = SoftDeleteManager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hostel", "status"]),
            models.Index(fields=["hostel", "phone"]),
            models.Index(fields=["hostel", "application_number"]),
            models.Index(fields=["hostel", "district"]),
            models.Index(fields=["is_deleted"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "application_number"],
                name="unique_application_number_per_hostel_non_deleted",
                condition=models.Q(is_deleted=False)
            )
        ]

    def __str__(self):
        return f"{self.application_number or self.full_name} ({self.status})"


class AdmissionDocument(HostelScopedModel):
    DOC_TYPES = [
        ("passport_photo", "Passport Photo"),
        ("citizenship_front", "Citizenship Front"),
        ("citizenship_back", "Citizenship Back"),
        ("birth_certificate", "Birth Certificate"),
        ("guardian_citizenship", "Guardian Citizenship"),
        ("academic_certificate", "Previous Academic Certificate"),
        ("migration_certificate", "Migration Certificate"),
        ("character_certificate", "Character Certificate"),
        ("medical_report", "Medical Report"),
        ("other_documents", "Other Documents"),
    ]

    admission_request = models.ForeignKey(
        AdmissionRequest,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    doc_type = models.CharField(max_length=50, choices=DOC_TYPES)
    file = models.FileField(upload_to="admissions/docs/%Y/%m/")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admission_request.application_number} - {self.doc_type}"

