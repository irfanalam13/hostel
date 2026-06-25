from rest_framework import serializers
from apps.common.serializers import HostelScopedSerializer
from .models import Notice


class NoticeSerializer(HostelScopedSerializer):
    created_by_name = serializers.CharField(source="created_by.username", read_only=True)

    class Meta:
        model = Notice
        fields = "__all__"
        read_only_fields = ["created_by"]
