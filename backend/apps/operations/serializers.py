from rest_framework import serializers
from apps.common.serializers import HostelScopedSerializer
from .models import EntryExitLog, LeaveRequest, VisitorLog


class PersonRequiredMixin:
    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        resident = attrs.get("resident") or getattr(instance, "resident", None)
        student = attrs.get("student") or getattr(instance, "student", None)
        if not resident and not student:
            raise serializers.ValidationError("Select a resident or student.")
        return attrs


class EntryExitLogSerializer(PersonRequiredMixin, HostelScopedSerializer):
    resident_name = serializers.CharField(source="resident.full_name", read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = EntryExitLog
        fields = "__all__"
        read_only_fields = ["recorded_by"]


class LeaveRequestSerializer(PersonRequiredMixin, HostelScopedSerializer):
    resident_name = serializers.CharField(source="resident.full_name", read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = ["status", "decision_note", "decided_by", "decided_at"]

    def validate(self, attrs):
        attrs = super().validate(attrs)
        start_date = attrs.get("start_date") or getattr(self.instance, "start_date", None)
        end_date = attrs.get("end_date") or getattr(self.instance, "end_date", None)
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date cannot be before start date."})
        return attrs


class LeaveDecisionSerializer(serializers.Serializer):
    decision_note = serializers.CharField(required=False, allow_blank=True)


class VisitorLogSerializer(PersonRequiredMixin, HostelScopedSerializer):
    resident_name = serializers.CharField(source="resident.full_name", read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)

    class Meta:
        model = VisitorLog
        fields = "__all__"
        read_only_fields = ["recorded_by", "check_out_at"]
