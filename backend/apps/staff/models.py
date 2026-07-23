"""Staff Management domain models (Phase 1 — core + RBAC).

Everything is tenant-scoped to ``tenants.Hostel`` via ``HostelScopedModel``
(UUID pk + created/updated timestamps + hostel FK). Staff accounts reuse
``accounts.User`` + ``accounts.UserHostel`` for authentication and workspace
membership; ``StaffProfile`` holds the HR record and links one profile per
user per workspace.

Custom per-tenant RBAC lives in :class:`Role`: a workspace builds unlimited
roles, each a set of ``module.action`` permission strings drawn from the same
catalog as ``apps.common.rbac``. A staff member's assigned role is unioned into
their effective permissions by ``apps.staff.rbac`` (wired into
``apps.common.rbac.user_permissions``).
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.common.models import HostelScopedModel


class Department(HostelScopedModel):
    name = models.CharField(max_length=120)
    code = models.CharField(max_length=32, blank=True, default="")
    description = models.TextField(blank=True, default="")
    # The department head is a staff member; string ref avoids the definition
    # cycle with StaffProfile (which points back at Department).
    head = models.ForeignKey(
        "staff.StaffProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="headed_departments",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "name"], name="uniq_department_per_hostel"),
        ]

    def __str__(self):
        return self.name


class Designation(HostelScopedModel):
    title = models.CharField(max_length=120)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="designations",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "title"], name="uniq_designation_per_hostel"),
        ]

    def __str__(self):
        return self.title


class Role(HostelScopedModel):
    """A custom, per-workspace RBAC role.

    ``permissions`` is a list of ``module.action`` grants (``*`` and
    ``module.*`` wildcards allowed) from the ``apps.common.rbac`` catalog.
    System roles are seeded per workspace and cannot be deleted (only their
    grants may be tuned).
    """

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90)
    description = models.CharField(max_length=255, blank=True, default="")
    permissions = models.JSONField(default=list, blank=True)
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "slug"], name="uniq_role_slug_per_hostel"),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:90] or "role"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class StaffProfile(HostelScopedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        INVITED = "invited", "Invited"
        SUSPENDED = "suspended", "Suspended"
        DISABLED = "disabled", "Disabled"
        LOCKED = "locked", "Locked"

    class EmploymentType(models.TextChoices):
        FULL_TIME = "full_time", "Full Time"
        PART_TIME = "part_time", "Part Time"
        CONTRACT = "contract", "Contract"
        TEMPORARY = "temporary", "Temporary"
        INTERNSHIP = "internship", "Internship"

    class SalaryType(models.TextChoices):
        MONTHLY = "monthly", "Monthly"
        HOURLY = "hourly", "Hourly"
        DAILY = "daily", "Daily Wage"
        CONTRACT = "contract", "Contract"

    # Auth / membership: the login account. Unique per (hostel, user) so a
    # single account can only carry one staff record within a workspace.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="staff_profiles",
    )
    employee_id = models.CharField(max_length=32)

    # --- Personal ---
    first_name = models.CharField(max_length=80, blank=True, default="")
    middle_name = models.CharField(max_length=80, blank=True, default="")
    last_name = models.CharField(max_length=80, blank=True, default="")
    photo = models.ImageField(upload_to="staff/photos/%Y/%m/", null=True, blank=True)
    gender = models.CharField(max_length=20, blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=80, blank=True, default="")
    citizenship_number = models.CharField(max_length=64, blank=True, default="")
    passport_number = models.CharField(max_length=64, blank=True, default="")
    marital_status = models.CharField(max_length=20, blank=True, default="")

    # --- Contact (email lives on the User account) ---
    phone = models.CharField(max_length=32, blank=True, default="")
    emergency_contact_name = models.CharField(max_length=120, blank=True, default="")
    emergency_contact_phone = models.CharField(max_length=32, blank=True, default="")

    # --- Address ---
    country = models.CharField(max_length=80, blank=True, default="")
    province = models.CharField(max_length=80, blank=True, default="")
    district = models.CharField(max_length=80, blank=True, default="")
    city = models.CharField(max_length=80, blank=True, default="")
    ward = models.CharField(max_length=40, blank=True, default="")
    street = models.CharField(max_length=160, blank=True, default="")
    postal_code = models.CharField(max_length=20, blank=True, default="")

    # --- Employment ---
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff",
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff",
    )
    designation = models.ForeignKey(
        Designation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="staff",
    )
    reporting_manager = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
    )
    joining_date = models.DateField(null=True, blank=True)
    employment_type = models.CharField(
        max_length=20, choices=EmploymentType.choices, default=EmploymentType.FULL_TIME
    )
    work_location = models.CharField(max_length=120, blank=True, default="")
    shift = models.CharField(max_length=80, blank=True, default="")
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )

    # --- Salary ---
    salary_type = models.CharField(
        max_length=20, choices=SalaryType.choices, default=SalaryType.MONTHLY
    )
    basic_salary = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    allowances = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=40, blank=True, default="")
    bank_name = models.CharField(max_length=120, blank=True, default="")
    bank_account = models.CharField(max_length=64, blank=True, default="")
    pan_number = models.CharField(max_length=64, blank=True, default="")

    notes = models.TextField(blank=True, default="")
    # Advisory flag surfaced to the UI; enforcement of a forced reset at login
    # is a later-phase concern (no password-change gate exists yet).
    must_change_password = models.BooleanField(default=False)

    # Soft delete: the account and its history are preserved; the profile is
    # hidden from the directory and its seat is freed for the plan quota.
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "user"], name="uniq_staff_user_per_hostel"),
            models.UniqueConstraint(
                fields=["hostel", "employee_id"], name="uniq_staff_empid_per_hostel"
            ),
        ]
        indexes = [
            models.Index(fields=["hostel", "is_deleted", "status"]),
        ]

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.middle_name, self.last_name]
        name = " ".join(p for p in parts if p).strip()
        if name:
            return name
        return (self.user.get_full_name() or self.user.username) if self.user_id else ""

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"


def staff_document_path(instance, filename):
    return f"staff/documents/{instance.hostel_id}/{instance.staff_id}/{filename}"


class StaffDocument(HostelScopedModel):
    class DocType(models.TextChoices):
        CITIZENSHIP = "citizenship", "Citizenship"
        PASSPORT = "passport", "Passport"
        LICENSE = "license", "Driving License"
        CV = "cv", "CV / Résumé"
        OFFER_LETTER = "offer_letter", "Offer Letter"
        CONTRACT = "contract", "Employment Contract"
        CERTIFICATE = "certificate", "Certificate"
        POLICE_REPORT = "police_report", "Police Report"
        OTHER = "other", "Other"

    staff = models.ForeignKey(StaffProfile, on_delete=models.CASCADE, related_name="documents")
    doc_type = models.CharField(max_length=24, choices=DocType.choices, default=DocType.OTHER)
    title = models.CharField(max_length=160, blank=True, default="")
    file = models.FileField(upload_to=staff_document_path)
    expiry_date = models.DateField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_doc_type_display()} — {self.staff_id}"
