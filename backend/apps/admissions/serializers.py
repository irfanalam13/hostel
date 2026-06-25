from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from apps.common.serializers import HostelScopedSerializer

from apps.rooms.models import Bed, BedAssignment
from apps.students.models import Student
from .models import AdmissionRequest


class AdmissionRequestSerializer(HostelScopedSerializer):
    requested_bed_code = serializers.SerializerMethodField()
    approved_bed_code = serializers.SerializerMethodField()
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = AdmissionRequest
        fields = "__all__"
        read_only_fields = ["status", "approved_bed", "student", "decided_by", "decided_at"]

    def get_requested_bed_code(self, obj):
        return self._bed_code(obj.requested_bed)

    def get_approved_bed_code(self, obj):
        return self._bed_code(obj.approved_bed)

    def _bed_code(self, bed):
        if not bed:
            return ""
        room_no = getattr(bed.room, "room_no", bed.room_id)
        return f"{room_no}-{bed.bed_no}"


class AdmissionDecisionSerializer(serializers.Serializer):
    bed = serializers.PrimaryKeyRelatedField(queryset=Bed.objects.all(), required=False, allow_null=True)
    join_date = serializers.DateField(required=False)
    decision_note = serializers.CharField(required=False, allow_blank=True)

    def validate_bed(self, bed):
        request = self.context.get("request")
        if bed and request and bed.hostel_id != request.hostel.id:
            raise serializers.ValidationError("Bed does not belong to this hostel.")
        if bed and bed.status == "MAINTENANCE":
            raise serializers.ValidationError("Bed is under maintenance.")
        if bed and BedAssignment.objects.filter(bed=bed, is_active=True).exists():
            raise serializers.ValidationError("Bed already has an active assignment.")
        return bed


def approve_admission(admission, user, *, bed=None, join_date=None, decision_note=""):
    join_date = join_date or admission.preferred_join_date or timezone.localdate()
    bed = bed or admission.requested_bed
    if bed and bed.status == "MAINTENANCE":
        raise serializers.ValidationError({"bed": "Bed is under maintenance."})
    if bed and BedAssignment.objects.filter(bed=bed, is_active=True).exists():
        raise serializers.ValidationError({"bed": "Bed already has an active assignment."})

    with transaction.atomic():
        student = Student.objects.create(
            hostel=admission.hostel,
            full_name=admission.full_name,
            phone=admission.phone,
            address=admission.address,
            guardian_name=admission.guardian_name,
            guardian_phone=admission.guardian_phone,
            join_date=join_date,
            status="ACTIVE",
        )

        if bed:
            BedAssignment.objects.create(
                hostel=admission.hostel,
                bed=bed,
                student=student,
                start_date=join_date,
                is_active=True,
            )
            bed.status = "OCCUPIED"
            bed.save(update_fields=["status", "updated_at"])

        admission.status = "APPROVED"
        admission.student = student
        admission.approved_bed = bed
        admission.decision_note = decision_note
        admission.decided_by = user
        admission.decided_at = timezone.now()
        admission.save(
            update_fields=[
                "status",
                "student",
                "approved_bed",
                "decision_note",
                "decided_by",
                "decided_at",
                "updated_at",
            ]
        )
        return admission
