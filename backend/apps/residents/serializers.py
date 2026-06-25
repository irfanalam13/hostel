from rest_framework import serializers
from .models import Resident, BedAssignmentHistory, Stay

class BedAssignmentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BedAssignmentHistory
        fields = ["id", "bed", "start_at", "end_at"]

class ResidentSerializer(serializers.ModelSerializer):
    bed_history = BedAssignmentHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Resident
        fields = [
            "id", "full_name", "phone", "guardian_phone", "address",
            "join_date", "leave_date", "status",
            "current_bed", "monthly_fee", "security_deposit",
            "photo", "id_document",
            "bed_history", "created_at"
        ]
        read_only_fields = ["id", "created_at", "bed_history"]

class StaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Stay
        fields = ["id", "resident", "bed", "check_in", "check_out", "is_active"]
        read_only_fields = ["id"]
