from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import HasHostelContext, HostelMemberCanCreateStaffCanEdit, IsStaff
from .models import Complaint, ComplaintAttachment, ComplaintComment
from .serializers import (
    ComplaintAttachmentSerializer,
    ComplaintCommentCreateSerializer,
    ComplaintCommentSerializer,
    ComplaintSerializer,
    ComplaintStatusSerializer,
)


class ComplaintViewSet(viewsets.ModelViewSet):
    queryset = Complaint.objects.select_related("resident", "student", "assigned_to", "created_by").prefetch_related(
        "comments", "attachments"
    )
    serializer_class = ComplaintSerializer
    permission_classes = [HasHostelContext, HostelMemberCanCreateStaffCanEdit]
    filterset_fields = ["status", "priority", "category", "assigned_to", "resident", "student"]
    search_fields = ["title", "description", "resident__full_name", "student__full_name"]
    ordering_fields = ["created_at", "priority", "status", "resolved_at"]

    def get_queryset(self):
        return self.queryset.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel, created_by=self.request.user)

    def get_permissions(self):
        if self.action in ("set_status",):
            return [HasHostelContext(), IsStaff()]
        return super().get_permissions()

    @action(detail=True, methods=["post"], url_path="set-status")
    def set_status(self, request, pk=None):
        complaint = self.get_object()
        serializer = ComplaintStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        complaint.mark_status(serializer.validated_data["status"])
        complaint.save(update_fields=["status", "resolved_at", "updated_at"])
        return Response(self.get_serializer(complaint).data)

    @action(detail=True, methods=["post"], url_path="add-comment")
    def add_comment(self, request, pk=None):
        complaint = self.get_object()
        serializer = ComplaintCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        internal = serializer.validated_data.get("internal", False)
        if internal and getattr(request.user, "role", None) not in {"ADMIN", "OWNER", "MANAGER", "ACCOUNTANT", "WARDEN", "STAFF"}:
            return Response({"detail": "Only staff can add internal comments."}, status=status.HTTP_403_FORBIDDEN)
        comment = ComplaintComment.objects.create(
            hostel=request.hostel,
            complaint=complaint,
            author=request.user,
            body=serializer.validated_data["body"],
            internal=internal,
        )
        return Response(ComplaintCommentSerializer(comment).data, status=status.HTTP_201_CREATED)


class ComplaintCommentViewSet(viewsets.ModelViewSet):
    queryset = ComplaintComment.objects.select_related("complaint", "author").all()
    serializer_class = ComplaintCommentSerializer
    permission_classes = [HasHostelContext, HostelMemberCanCreateStaffCanEdit]
    filterset_fields = ["complaint", "internal"]

    def get_queryset(self):
        return self.queryset.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel, author=self.request.user)


class ComplaintAttachmentViewSet(viewsets.ModelViewSet):
    queryset = ComplaintAttachment.objects.select_related("complaint", "uploaded_by").all()
    serializer_class = ComplaintAttachmentSerializer
    permission_classes = [HasHostelContext, HostelMemberCanCreateStaffCanEdit]
    filterset_fields = ["complaint"]

    def get_queryset(self):
        return self.queryset.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel, uploaded_by=self.request.user)
