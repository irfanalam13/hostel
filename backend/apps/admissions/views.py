from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.common.permissions import HasHostelContext, IsStaffOrReadOnly
from .models import AdmissionRequest
from .serializers import AdmissionDecisionSerializer, AdmissionRequestSerializer, approve_admission


class AdmissionRequestViewSet(viewsets.ModelViewSet):
    queryset = AdmissionRequest.objects.select_related(
        "requested_bed__room", "approved_bed__room", "student", "decided_by"
    ).all()
    serializer_class = AdmissionRequestSerializer
    permission_classes = [HasHostelContext, IsStaffOrReadOnly]
    filterset_fields = ["status", "source", "requested_bed", "approved_bed"]
    search_fields = ["full_name", "phone", "guardian_phone", "email"]
    ordering_fields = ["created_at", "preferred_join_date", "status"]

    def get_queryset(self):
        return self.queryset.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        admission = self.get_object()
        if admission.status != "PENDING":
            return Response({"detail": "Only pending requests can be approved."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = AdmissionDecisionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        admission = approve_admission(
            admission,
            request.user,
            bed=serializer.validated_data.get("bed"),
            join_date=serializer.validated_data.get("join_date"),
            decision_note=serializer.validated_data.get("decision_note", ""),
        )
        return Response(self.get_serializer(admission).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        admission = self.get_object()
        if admission.status != "PENDING":
            return Response({"detail": "Only pending requests can be rejected."}, status=status.HTTP_400_BAD_REQUEST)
        admission.status = "REJECTED"
        admission.decision_note = request.data.get("decision_note", "")
        admission.decided_by = request.user
        admission.decided_at = timezone.now()
        admission.save(update_fields=["status", "decision_note", "decided_by", "decided_at", "updated_at"])
        return Response(self.get_serializer(admission).data)


class PublicAdmissionRequestViewSet(AdmissionRequestViewSet):
    permission_classes = [AllowAny, HasHostelContext]
    http_method_names = ["post", "options"]

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel, source="PUBLIC")
