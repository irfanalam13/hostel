from rest_framework import serializers
from apps.common.serializers import HostelScopedSerializer
from .models import Complaint, ComplaintAttachment, ComplaintComment


class ComplaintAttachmentSerializer(HostelScopedSerializer):
    class Meta:
        model = ComplaintAttachment
        fields = "__all__"
        read_only_fields = ["uploaded_by"]


class ComplaintCommentSerializer(HostelScopedSerializer):
    author_name = serializers.CharField(source="author.username", read_only=True)

    class Meta:
        model = ComplaintComment
        fields = "__all__"
        read_only_fields = ["author"]


class ComplaintSerializer(HostelScopedSerializer):
    resident_name = serializers.CharField(source="resident.full_name", read_only=True)
    student_name = serializers.CharField(source="student.full_name", read_only=True)
    assigned_to_name = serializers.CharField(source="assigned_to.username", read_only=True)
    comments = ComplaintCommentSerializer(many=True, read_only=True)
    attachments = ComplaintAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Complaint
        fields = "__all__"
        read_only_fields = ["created_by", "resolved_at"]


class ComplaintStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=[choice[0] for choice in Complaint.STATUS_CHOICES])


class ComplaintCommentCreateSerializer(serializers.Serializer):
    body = serializers.CharField()
    internal = serializers.BooleanField(required=False, default=False)
