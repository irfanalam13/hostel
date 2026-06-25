from rest_framework import serializers
from .models import Attendance

class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = ["id", "resident", "date", "status", "note", "created_at"]
        read_only_fields = ["id", "created_at"]