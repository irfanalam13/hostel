from rest_framework import serializers
from .models import BackupSnapshot


class BackupSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupSnapshot
        fields = ["id", "hostel", "file", "kind", "note", "created_at", "updated_at"]
        read_only_fields = ["id", "file", "created_at", "updated_at"]
