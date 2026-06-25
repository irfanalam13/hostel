from apps.common.serializers import HostelScopedSerializer
from rest_framework import serializers
from .models import AuditEvent

class AuditEventSerializer(HostelScopedSerializer):
    class Meta:
        model = AuditEvent
        fields = "__all__"