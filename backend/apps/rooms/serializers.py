from rest_framework import serializers
from apps.common.serializers import HostelScopedSerializer
from .models import Block, Floor, Room, Bed, BedAssignment


class BlockSerializer(HostelScopedSerializer):
    class Meta:
        model = Block
        fields = "__all__"


class FloorSerializer(HostelScopedSerializer):
    block_detail = BlockSerializer(source="block", read_only=True)

    class Meta:
        model = Floor
        fields = "__all__"

class RoomSerializer(HostelScopedSerializer):
    block_detail = BlockSerializer(source="block", read_only=True)
    floor_detail = FloorSerializer(source="floor_ref", read_only=True)

    class Meta:
        model = Room
        fields = "__all__"

class BedSerializer(HostelScopedSerializer):
    code = serializers.SerializerMethodField()
    room_detail = RoomSerializer(source="room", read_only=True)

    class Meta:
        model = Bed
        fields = "__all__"

    def get_code(self, obj):
        room_no = getattr(obj.room, "room_no", obj.room_id)
        return f"{room_no}-{obj.bed_no}"

class RoomDetailSerializer(RoomSerializer):
    beds = BedSerializer(many=True, read_only=True)

    class Meta(RoomSerializer.Meta):
        fields = "__all__"

class BedAssignmentSerializer(HostelScopedSerializer):
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    bed_code = serializers.SerializerMethodField()
    room_no = serializers.CharField(source="bed.room.room_no", read_only=True)
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = BedAssignment
        fields = "__all__"

    def get_bed_code(self, obj):
        room_no = getattr(obj.bed.room, "room_no", obj.bed.room_id)
        return f"{room_no}-{obj.bed.bed_no}"

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        bed = attrs.get("bed") or getattr(instance, "bed", None)
        student = attrs.get("student") or getattr(instance, "student", None)
        is_active = attrs.get("is_active", getattr(instance, "is_active", True))

        if is_active:
            if bed and getattr(bed, "status", "") == "MAINTENANCE":
                raise serializers.ValidationError({"bed": "Bed is under maintenance."})

            active_bed_qs = BedAssignment.objects.filter(bed=bed, is_active=True)
            active_student_qs = BedAssignment.objects.filter(student=student, is_active=True)
            if instance:
                active_bed_qs = active_bed_qs.exclude(pk=instance.pk)
                active_student_qs = active_student_qs.exclude(pk=instance.pk)

            if bed and active_bed_qs.exists():
                raise serializers.ValidationError({"bed": "Bed already has an active assignment."})
            if student and active_student_qs.exists():
                raise serializers.ValidationError({"student": "Student already has an active bed assignment."})

        return attrs
