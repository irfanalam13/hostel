from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import HasHostelContext, HostelMemberCanCreateStaffCanEdit, IsStaff, IsStaffOrReadOnly
from .models import EntryExitLog, LeaveRequest, VisitorLog
from .serializers import (
    EntryExitLogSerializer,
    LeaveDecisionSerializer,
    LeaveRequestSerializer,
    VisitorLogSerializer,
)


class HostelScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [HasHostelContext, IsStaffOrReadOnly]

    def get_queryset(self):
        return self.queryset.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel)


class EntryExitLogViewSet(HostelScopedViewSet):
    queryset = EntryExitLog.objects.select_related("resident", "student", "recorded_by").all()
    serializer_class = EntryExitLogSerializer
    search_fields = ["resident__full_name", "student__full_name", "purpose", "note"]
    filterset_fields = ["direction", "resident", "student"]
    ordering_fields = ["event_at", "created_at"]

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel, recorded_by=self.request.user)


class LeaveRequestViewSet(HostelScopedViewSet):
    queryset = LeaveRequest.objects.select_related("resident", "student", "decided_by").all()
    serializer_class = LeaveRequestSerializer
    permission_classes = [HasHostelContext, HostelMemberCanCreateStaffCanEdit]
    search_fields = ["resident__full_name", "student__full_name", "reason"]
    filterset_fields = ["status", "resident", "student", "start_date", "end_date"]
    ordering_fields = ["created_at", "start_date", "end_date", "status"]

    def get_permissions(self):
        if self.action in ("approve", "reject"):
            return [HasHostelContext(), IsStaff()]
        return super().get_permissions()

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        leave = self.get_object()
        if leave.status != "PENDING":
            return Response({"detail": "Only pending leave requests can be approved."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = LeaveDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave.status = "APPROVED"
        leave.decision_note = serializer.validated_data.get("decision_note", "")
        leave.decided_by = request.user
        leave.decided_at = timezone.now()
        leave.save(update_fields=["status", "decision_note", "decided_by", "decided_at", "updated_at"])
        return Response(self.get_serializer(leave).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        leave = self.get_object()
        if leave.status != "PENDING":
            return Response({"detail": "Only pending leave requests can be rejected."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = LeaveDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave.status = "REJECTED"
        leave.decision_note = serializer.validated_data.get("decision_note", "")
        leave.decided_by = request.user
        leave.decided_at = timezone.now()
        leave.save(update_fields=["status", "decision_note", "decided_by", "decided_at", "updated_at"])
        return Response(self.get_serializer(leave).data)


class VisitorLogViewSet(HostelScopedViewSet):
    queryset = VisitorLog.objects.select_related("resident", "student", "recorded_by").all()
    serializer_class = VisitorLogSerializer
    search_fields = ["visitor_name", "visitor_phone", "resident__full_name", "student__full_name", "purpose"]
    filterset_fields = ["resident", "student"]
    ordering_fields = ["check_in_at", "check_out_at", "created_at"]

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel, recorded_by=self.request.user)

    @action(detail=True, methods=["post"])
    def checkout(self, request, pk=None):
        visitor = self.get_object()
        if visitor.check_out_at:
            return Response({"detail": "Visitor is already checked out."}, status=status.HTTP_400_BAD_REQUEST)
        visitor.check_out_at = timezone.now()
        visitor.save(update_fields=["check_out_at", "updated_at"])
        return Response(self.get_serializer(visitor).data)
