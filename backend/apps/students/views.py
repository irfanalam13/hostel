from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.common.permissions import HasHostelContext, IsStaffOrReadOnly
from apps.rooms.models import Bed, BedAssignment
from apps.fees.models import FeeLedger
from apps.payments.models import Payment
from apps.complaints.models import Complaint
from .models import Student, StudentDocument
from .serializers import StudentSerializer, StudentDocumentSerializer

class HostelScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [HasHostelContext, IsStaffOrReadOnly]

    def get_queryset(self):
        return self.queryset.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel)

class StudentViewSet(HostelScopedViewSet):
    queryset = Student.objects.all().order_by("full_name")
    serializer_class = StudentSerializer
    search_fields = ["full_name","phone","guardian_phone"]
    filterset_fields = ["status"]

    @action(detail=True, methods=["post"], url_path="transfer-bed")
    def transfer_bed(self, request, pk=None):
        student = self.get_object()
        bed_id = request.data.get("bed")
        start_date = request.data.get("start_date") or timezone.localdate()
        if not bed_id:
            return Response({"detail": "bed is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_bed = Bed.objects.get(pk=bed_id, hostel=request.hostel)
        except Bed.DoesNotExist:
            return Response({"detail": "Bed not found."}, status=status.HTTP_404_NOT_FOUND)
        if new_bed.status == "MAINTENANCE":
            return Response({"detail": "Bed is under maintenance."}, status=status.HTTP_400_BAD_REQUEST)
        if BedAssignment.objects.filter(bed=new_bed, is_active=True).exists():
            return Response({"detail": "Bed already has an active assignment."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            active_assignments = BedAssignment.objects.filter(student=student, is_active=True)
            for assignment in active_assignments:
                assignment.is_active = False
                assignment.end_date = start_date
                assignment.save(update_fields=["is_active", "end_date", "updated_at"])
                if not assignment.bed.assignments.filter(is_active=True).exists():
                    assignment.bed.status = "AVAILABLE"
                    assignment.bed.save(update_fields=["status", "updated_at"])

            new_assignment = BedAssignment.objects.create(
                hostel=request.hostel,
                bed=new_bed,
                student=student,
                start_date=start_date,
                is_active=True,
            )
            new_bed.status = "OCCUPIED"
            new_bed.save(update_fields=["status", "updated_at"])

        return Response({"detail": "Bed transferred.", "assignment": str(new_assignment.id)})

    @action(detail=True, methods=["post"])
    def checkout(self, request, pk=None):
        student = self.get_object()
        checkout_date = request.data.get("checkout_date") or timezone.localdate()
        with transaction.atomic():
            assignments = BedAssignment.objects.filter(student=student, is_active=True)
            for assignment in assignments:
                assignment.is_active = False
                assignment.end_date = checkout_date
                assignment.save(update_fields=["is_active", "end_date", "updated_at"])
                if not assignment.bed.assignments.filter(is_active=True).exists():
                    assignment.bed.status = "AVAILABLE"
                    assignment.bed.save(update_fields=["status", "updated_at"])
            student.status = "LEFT"
            student.save(update_fields=["status", "updated_at"])
        return Response({"detail": "Student checked out and active bed freed."})

    @action(detail=True, methods=["get"])
    def timeline(self, request, pk=None):
        student = self.get_object()
        assignments = [
            {
                "type": "bed_assignment",
                "date": item.start_date,
                "label": f"{item.bed.room.room_no}-{item.bed.bed_no}",
                "status": "active" if item.is_active else "ended",
            }
            for item in BedAssignment.objects.filter(student=student).select_related("bed__room").order_by("-start_date")
        ]
        ledgers = [
            {
                "type": "invoice",
                "date": item.month,
                "label": f"{item.month} fee ledger",
                "status": item.status,
                "amount": str(item.net_due),
            }
            for item in FeeLedger.objects.filter(student=student).order_by("-month")
        ]
        payments = [
            {
                "type": "payment",
                "date": item.date,
                "label": item.method,
                "status": "received",
                "amount": str(item.amount),
            }
            for item in Payment.objects.filter(student=student).order_by("-date")
        ]
        complaints = [
            {
                "type": "complaint",
                "date": item.created_at,
                "label": item.title,
                "status": item.status,
            }
            for item in Complaint.objects.filter(student=student).order_by("-created_at")
        ]
        return Response(assignments + ledgers + payments + complaints)

class StudentDocumentViewSet(HostelScopedViewSet):
    queryset = StudentDocument.objects.select_related("student").all().order_by("-created_at")
    serializer_class = StudentDocumentSerializer
    filterset_fields = ["student","doc_type"]
