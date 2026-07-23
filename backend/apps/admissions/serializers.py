import logging
import re
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.common.serializers import HostelScopedSerializer
from apps.rooms.models import Bed, BedAssignment
from apps.students.models import Student, StudentDocument
from apps.accounts.models import UserHostel
from .models import AdmissionRequest, AdmissionDocument

User = get_user_model()
logger = logging.getLogger(__name__)


class AdmissionDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdmissionDocument
        fields = ["id", "doc_type", "file", "uploaded_at"]


class AdmissionRequestSerializer(HostelScopedSerializer):
    documents = AdmissionDocumentSerializer(many=True, read_only=True)
    requested_bed_code = serializers.SerializerMethodField()
    approved_bed_code = serializers.SerializerMethodField()
    preferred_bed_code = serializers.SerializerMethodField()
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = AdmissionRequest
        fields = "__all__"
        read_only_fields = [
            "id",
            "application_number",
            "application_date",
            "status",
            "approved_bed",
            "student",
            "decided_by",
            "decided_at",
            "assigned_by",
            "assigned_date",
            "is_deleted",
            "created_at",
            "updated_at",
        ]

    def get_requested_bed_code(self, obj):
        return self._bed_code(obj.requested_bed)

    def get_approved_bed_code(self, obj):
        return self._bed_code(obj.approved_bed)

    def get_preferred_bed_code(self, obj):
        return self._bed_code(obj.preferred_bed)

    def _bed_code(self, bed):
        if not bed:
            return ""
        room_no = getattr(bed.room, "room_no", bed.room_id)
        return f"{room_no}-{bed.bed_no}"

    # Validation rules
    def validate_phone(self, value):
        # Validate phone format (Nepal standard e.g. 98 or 97 or 01)
        if not re.match(r"^\+?[0-9\-\s\(\)]{7,20}$", value):
            raise serializers.ValidationError("Enter a valid phone number (7 to 20 digits).")

        request = self.context.get("request")
        if not request or not getattr(request, "hostel", None):
            return value
        hostel = request.hostel

        # Check duplicate student phone
        if Student.objects.filter(hostel=hostel, phone=value).exists():
            raise serializers.ValidationError("A student with this phone number is already registered in this hostel.")

        # Check duplicate pending/active admission phone
        qs = AdmissionRequest.objects.filter(hostel=hostel, phone=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        
        active_statuses = ["PENDING", "UNDER_REVIEW", "VERIFICATION_PENDING", "WAITLISTED", "INTERVIEW_REQUIRED"]
        if qs.filter(status__in=active_statuses).exists():
            raise serializers.ValidationError("An active admission application with this phone number already exists.")

        return value

    def validate_citizenship_number(self, value):
        if not value:
            return value
        request = self.context.get("request")
        if not request or not getattr(request, "hostel", None):
            return value
        hostel = request.hostel

        # Duplicate citizenship checks in student database
        if Student.objects.filter(hostel=hostel, citizenship_number=value).exists():
            raise serializers.ValidationError("A student with this citizenship number is already registered.")

        # Duplicate citizenship checks in active admissions
        qs = AdmissionRequest.objects.filter(hostel=hostel, citizenship_number=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        
        active_statuses = ["PENDING", "UNDER_REVIEW", "VERIFICATION_PENDING", "WAITLISTED", "INTERVIEW_REQUIRED", "APPROVED"]
        if qs.filter(status__in=active_statuses).exists():
            raise serializers.ValidationError("An admission request with this citizenship number is already in progress.")

        return value

    def validate_email(self, value):
        if not value:
            return value
        # Simple syntax validation is handled by EmailField, check duplicates
        request = self.context.get("request")
        if not request or not getattr(request, "hostel", None):
            return value
        hostel = request.hostel

        qs = AdmissionRequest.objects.filter(hostel=hostel, email=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        
        active_statuses = ["PENDING", "UNDER_REVIEW", "VERIFICATION_PENDING", "WAITLISTED"]
        if qs.filter(status__in=active_statuses).exists():
            raise serializers.ValidationError("An active application with this email already exists.")
        return value

    def validate_date_of_birth(self, value):
        if value:
            if value >= timezone.localdate():
                raise serializers.ValidationError("Date of birth cannot be in the future.")
            age = (timezone.localdate() - value).days // 365
            if age < 5 or age > 100:
                raise serializers.ValidationError("Age must be between 5 and 100 years.")
        return value

    def validate(self, attrs):
        # 1. English name capital letter check
        full_name = attrs.get("full_name", "")
        if full_name:
            # Capitalize name
            attrs["full_name"] = full_name.upper()

        # 2. Guardian requirements
        # Must have at least father_name, mother_name, or spouse_name
        father_name = attrs.get("father_name", "").strip()
        mother_name = attrs.get("mother_name", "").strip()
        spouse_name = attrs.get("spouse_name", "").strip()

        if not father_name and not mother_name and not spouse_name:
            raise serializers.ValidationError(
                {"father_name": "At least one parent's (Father or Mother) or Spouse's details must be provided."}
            )

        # Local guardian requirement: required if parents live in a different district
        # We can compare permanent district with local guardian address/district.
        # If parents' contact is outside student's permanent district:
        # We assume local guardian is required if local_guardian_name is provided or if parents live outside.
        # Let's enforce that if local_guardian_name is provided, it must have name, phone, and address.
        local_guardian_name = attrs.get("local_guardian_name", "").strip()
        
        # If local guardian is provided, validate phone and address
        if local_guardian_name:
            if not attrs.get("local_guardian_phone", "").strip():
                raise serializers.ValidationError({"local_guardian_phone": "Local guardian phone is required."})
            if not attrs.get("local_guardian_address", "").strip():
                raise serializers.ValidationError({"local_guardian_address": "Local guardian address is required."})
            if not attrs.get("local_guardian_relation", "").strip():
                raise serializers.ValidationError({"local_guardian_relation": "Local guardian relation is required."})

        # 3. Education requirements
        # Institute and Level are required
        if not attrs.get("educational_institute", "").strip():
            raise serializers.ValidationError({"educational_institute": "Educational institute is required."})
        if not attrs.get("current_level"):
            raise serializers.ValidationError({"current_level": "Current level is required."})

        # 4. Scope checks for preferred bed/room
        request = self.context.get("request")
        if request and getattr(request, "hostel", None):
            hostel = request.hostel
            pref_room = attrs.get("preferred_room")
            pref_bed = attrs.get("preferred_bed")

            if pref_room and pref_room.hostel_id != hostel.id:
                raise serializers.ValidationError({"preferred_room": "Selected room does not belong to this hostel."})
            if pref_bed and pref_bed.room.hostel_id != hostel.id:
                raise serializers.ValidationError({"preferred_bed": "Selected bed does not belong to this hostel."})

        return attrs


class AdmissionDecisionSerializer(serializers.Serializer):
    bed = serializers.PrimaryKeyRelatedField(queryset=Bed.objects.all(), required=False, allow_null=True)
    join_date = serializers.DateField(required=False)
    decision_note = serializers.CharField(required=False, allow_blank=True)
    
    # Official Use fields to set on approval
    monthly_fee = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    security_deposit = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    admission_fee = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    discount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    scholarship = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    receipt_number = serializers.CharField(required=False, allow_blank=True)
    payment_status = serializers.ChoiceField(choices=AdmissionRequest.PAYMENT_STATUS_CHOICES, required=False)

    def validate_bed(self, bed):
        request = self.context.get("request")
        if not bed:
            return bed
        if request and getattr(request, "hostel", None):
            if bed.room.hostel_id != request.hostel.id:
                raise serializers.ValidationError("Bed does not belong to this hostel.")
        if bed.status == "MAINTENANCE":
            raise serializers.ValidationError("Bed is under maintenance.")
        if BedAssignment.objects.filter(bed=bed, is_active=True).exists():
            raise serializers.ValidationError("Bed already has an active assignment.")
        return bed


def send_student_welcome_email(hostel, *, email, student_name, workspace_url_hint=None):
    """Best-effort tenant-branded welcome email for a newly-approved student.

    Only meaningful when the applicant supplied a real email at admission time
    (the caller guards on that). The initial password value is NOT printed — the
    student is told it's their registered phone number and is forced to change it
    on first login (User.must_change_password=True). Never raises.
    """
    if not email:
        return
    try:
        from apps.common.emails import send_account_welcome, welcome_context_from_branding
        from apps.tenants.branding import email_branding

        brand = email_branding(hostel)
        context = welcome_context_from_branding(brand)
        context.update({
            "recipient_name": student_name,
            "workspace_name": hostel.name,
            "hostel_code": hostel.code,
            "login_identity": email,
            "role_label": "Resident",
            "credential_note": (
                "Your initial password is your registered phone number.\n"
                "You'll be asked to set a new password the first time you sign in."
            ),
            "first_login_note": (
                f"Your admission to {hostel.name} is approved. Sign in with your "
                f"email ({email}) at your workspace address above."
            ),
        })
        send_account_welcome(
            to=email,
            subject=f"Welcome to {brand['sender_name']} — your admission is approved",
            from_email=brand["from_email"],
            context=context,
            fail_silently=True,
        )
    except Exception:
        pass


def approve_admission(admission, user, *, bed=None, join_date=None, decision_note="", **official_data):
    join_date = join_date or admission.booking_date or timezone.localdate()
    # A bed reserved pre-approval via the assign-bed action lands on approved_bed;
    # honour it (and the applicant's requested/preferred bed) when none is passed.
    bed = bed or admission.approved_bed or admission.requested_bed or admission.preferred_bed

    if bed:
        if bed.status == "MAINTENANCE":
            raise serializers.ValidationError({"bed": "Bed is under maintenance."})
        if BedAssignment.objects.filter(bed=bed, is_active=True).exists():
            raise serializers.ValidationError({"bed": "Bed already has an active assignment."})

    with transaction.atomic():
        # 1. Update official use fields on admission
        for field, value in official_data.items():
            if hasattr(admission, field) and value is not None:
                setattr(admission, field, value)

        # 2. Create Student profile with all fields
        permanent_address = f"{admission.street_tole}, Ward {admission.ward_number}, {admission.municipality}, {admission.district}, {admission.province}"
        
        student = Student.objects.create(
            hostel=admission.hostel,
            full_name=admission.full_name,
            phone=admission.phone,
            address=permanent_address,
            guardian_name=admission.local_guardian_name or admission.father_name or admission.mother_name,
            guardian_phone=admission.local_guardian_phone or admission.father_phone or admission.mother_phone,
            join_date=join_date,
            status="ACTIVE",
            # Extended fields
            name_nepali=admission.name_nepali,
            date_of_birth=admission.date_of_birth,
            gender=admission.gender,
            photo=admission.photo,
            citizenship_number=admission.citizenship_number,
            father_name=admission.father_name,
            mother_name=admission.mother_name,
            emergency_contact_name=admission.emergency_contact_name,
            emergency_contact_phone=admission.emergency_contact_phone,
            emergency_contact_relation=admission.emergency_contact_relation,
        )

        # 3. Create Student Bed Assignment if bed is specified. This is the ONLY
        #    place an initial bed assignment is created; later moves go through
        #    the rooms bed-transfer action.
        if bed:
            BedAssignment.objects.create(
                hostel=admission.hostel,
                bed=bed,
                student=student,
                start_date=join_date,
                is_active=True,
                reason="INITIAL",
                created_by=user,
            )
            bed.status = "OCCUPIED"
            bed.save(update_fields=["status", "updated_at"])

        # 4. Create Student User account (role RESIDENT)
        username = f"std_{admission.phone.replace(' ', '').replace('-', '').replace('+', '')}"
        
        # Ensure username is unique
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}_{counter}"
            counter += 1

        email = admission.email or f"{username}@hostel.local"
        
        resident_user = User.objects.create(
            username=username,
            email=email,
            first_name=admission.full_name.split()[0] if admission.full_name.split() else "",
            last_name=" ".join(admission.full_name.split()[1:]) if len(admission.full_name.split()) > 1 else "",
            role="RESIDENT",
            is_active=True,
            # Default password is their phone number — force a change on first login.
            must_change_password=True,
        )
        resident_user.set_password(admission.phone)  # Default password is their phone number
        resident_user.save()

        # Link user to hostel
        UserHostel.objects.get_or_create(
            user=resident_user,
            hostel=admission.hostel,
            defaults={"is_active": True}
        )

        # 5. Copy uploaded documents to StudentDocument
        for doc in admission.documents.all():
            StudentDocument.objects.create(
                hostel=admission.hostel,
                student=student,
                doc_type=doc.doc_type,
                file=doc.file,
            )

        # 6. Complete admission request
        admission.status = "APPROVED"
        admission.student = student
        admission.approved_bed = bed
        admission.decision_note = decision_note
        admission.decided_by = user
        admission.decided_at = timezone.now()
        admission.assigned_by = user
        admission.assigned_date = timezone.now()
        admission.save()

        # Mock Notifications (Log & print)
        bed_label = f"{bed.room.room_no}-{bed.bed_no}" if bed else "None"
        logger.info(f"NOTIFICATION [Email/SMS] to student {student.full_name} ({student.phone}): Your admission request {admission.application_number} is APPROVED. Bed assigned: {bed_label}. Credentials: Username={username}, Password={student.phone}")

        # Welcome email with the workspace URL + login details — only when the
        # applicant gave a real email (skip the synthetic @hostel.local fallback).
        # Sent after the approval commits so a rollback never emails the student.
        if admission.email:
            hostel = admission.hostel
            student_email = admission.email
            student_name = student.full_name
            transaction.on_commit(
                lambda: send_student_welcome_email(
                    hostel, email=student_email, student_name=student_name
                )
            )

        return admission
