import logging
from django.db import transaction, IntegrityError
from django.utils import timezone
from django.template.loader import render_to_string
from django.http import HttpResponse
from rest_framework import status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.common.permissions import HasHostelContext, IsStaffOrReadOnly
from apps.rooms.models import Bed, BedAssignment
from apps.auditlog.services import record_event

from .models import AdmissionRequest, AdmissionDocument
from .serializers import (
    AdmissionRequestSerializer,
    AdmissionDecisionSerializer,
    AdmissionDocumentSerializer,
    approve_admission,
)

logger = logging.getLogger(__name__)


def get_next_application_number(hostel):
    year = timezone.localdate().year
    prefix = f"ADM-{year}-"
    
    # Query database to find the last request (including soft deleted to avoid collisions)
    last_req = AdmissionRequest.objects.all_with_deleted().filter(
        hostel=hostel,
        application_number__startswith=prefix
    ).order_by("-application_number").first()

    if last_req:
        try:
            last_num_str = last_req.application_number.split("-")[-1]
            next_num = int(last_num_str) + 1
        except (ValueError, IndexError):
            next_num = 1
    else:
        next_num = 1

    return f"{prefix}{next_num:06d}"


class AdmissionRequestViewSet(viewsets.ModelViewSet):
    queryset = AdmissionRequest.objects.select_related(
        "requested_bed__room",
        "approved_bed__room",
        "preferred_bed__room",
        "preferred_room",
        "student",
        "decided_by",
        "assigned_by",
    ).prefetch_related("documents").all()
    serializer_class = AdmissionRequestSerializer
    permission_classes = [HasHostelContext, IsStaffOrReadOnly]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        "status",
        "source",
        "gender",
        "food_preference",
        "current_level",
        "preferred_room_type",
        "district",
        "payment_status",
    ]
    search_fields = [
        "application_number",
        "full_name",
        "phone",
        "local_guardian_name",
        "father_name",
        "email",
        "district",
        "educational_institute",
    ]
    ordering_fields = ["created_at", "application_date", "status", "full_name"]

    def get_queryset(self):
        return self.queryset.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        hostel = self.request.hostel
        
        # Retry loop to prevent concurrent code generation race conditions
        retries = 3
        while retries > 0:
            app_num = get_next_application_number(hostel)
            fee = hostel.settings.get("default_application_fee", 500.00)
            try:
                with transaction.atomic():
                    instance = serializer.save(
                        hostel=hostel,
                        application_number=app_num,
                        application_fee=fee,
                        application_date=timezone.localdate(),
                        status="PENDING",
                    )
                    
                    # Record audit log
                    record_event(
                        self.request,
                        action="create",
                        entity_type="admission_request",
                        entity_id=instance.id,
                        message=f"Created admission request {app_num}",
                    )
                    return
            except IntegrityError:
                retries -= 1
                if retries == 0:
                    raise

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        admission = self.get_object()
        if admission.status not in ["PENDING", "UNDER_REVIEW", "VERIFICATION_PENDING"]:
            return Response(
                {"detail": "Only pending, under review, or verification pending requests can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AdmissionDecisionSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data
        bed = validated_data.get("bed")
        join_date = validated_data.get("join_date")
        decision_note = validated_data.get("decision_note", "")

        official_fields = [
            "monthly_fee", "security_deposit", "admission_fee", 
            "discount", "scholarship", "receipt_number", "payment_status"
        ]
        official_data = {f: validated_data.get(f) for f in official_fields if validated_data.get(f) is not None}

        admission = approve_admission(
            admission,
            request.user,
            bed=bed,
            join_date=join_date,
            decision_note=decision_note,
            **official_data
        )

        record_event(
            request,
            action="update",
            entity_type="admission_request",
            entity_id=admission.id,
            message=f"Approved admission request {admission.application_number}",
        )

        return Response(self.get_serializer(admission).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        admission = self.get_object()
        if admission.status not in ["PENDING", "UNDER_REVIEW", "VERIFICATION_PENDING"]:
            return Response(
                {"detail": "Only pending, under review, or verification pending requests can be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        admission.status = "REJECTED"
        admission.decision_note = request.data.get("decision_note", "")
        admission.rejection_reason = request.data.get("rejection_reason", "")
        admission.decided_by = request.user
        admission.decided_at = timezone.now()
        admission.save(update_fields=["status", "decision_note", "rejection_reason", "decided_by", "decided_at", "updated_at"])

        record_event(
            request,
            action="update",
            entity_type="admission_request",
            entity_id=admission.id,
            message=f"Rejected admission request {admission.application_number}",
        )

        return Response(self.get_serializer(admission).data)

    @action(detail=True, methods=["post"], url_path="assign-bed")
    def assign_bed(self, request, pk=None):
        admission = self.get_object()
        bed_id = request.data.get("bed")
        if not bed_id:
            return Response({"detail": "bed is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            bed = Bed.objects.get(pk=bed_id, room__hostel=request.hostel)
        except Bed.DoesNotExist:
            return Response({"detail": "Bed not found."}, status=status.HTTP_404_NOT_FOUND)

        if bed.status == "MAINTENANCE":
            return Response({"detail": "Bed is under maintenance."}, status=status.HTTP_400_BAD_REQUEST)
        if BedAssignment.objects.filter(bed=bed, is_active=True).exists():
            return Response({"detail": "Bed already has an active assignment."}, status=status.HTTP_400_BAD_REQUEST)

        admission.approved_bed = bed
        admission.assigned_by = request.user
        admission.assigned_date = timezone.now()
        admission.save(update_fields=["approved_bed", "assigned_by", "assigned_date", "updated_at"])

        record_event(
            request,
            action="update",
            entity_type="admission_request",
            entity_id=admission.id,
            message=f"Assigned bed {bed.room.room_no}-{bed.bed_no} to {admission.application_number}",
        )

        return Response(self.get_serializer(admission).data)

    @action(detail=True, methods=["post"], url_path="upload-document")
    def upload_document(self, request, pk=None):
        admission = self.get_object()
        doc_type = request.data.get("doc_type")
        file_obj = request.FILES.get("file")

        if not doc_type or not file_obj:
            return Response({"detail": "doc_type and file are required."}, status=status.HTTP_400_BAD_REQUEST)

        # File size verification
        hostel = request.hostel
        max_size_mb = hostel.settings.get("max_upload_size_mb", 10)
        if file_obj.size > max_size_mb * 1024 * 1024:
            return Response(
                {"detail": f"File size exceeds maximum allowed size of {max_size_mb}MB."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Format verification
        ext = file_obj.name.split(".")[-1].lower()
        if ext not in ["pdf", "png", "jpg", "jpeg"]:
            return Response({"detail": "Allowed formats: PDF, PNG, JPG, JPEG."}, status=status.HTTP_400_BAD_REQUEST)

        doc = AdmissionDocument.objects.create(
            hostel=hostel,
            admission_request=admission,
            doc_type=doc_type,
            file=file_obj,
        )

        record_event(
            request,
            action="update",
            entity_type="admission_request",
            entity_id=admission.id,
            message=f"Uploaded document {doc_type} for application {admission.application_number}",
        )

        return Response(AdmissionDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="pdf")
    def generate_pdf(self, request, pk=None):
        admission = self.get_object()
        html_string = render_to_string("admissions/admission_pdf.html", {"admission": admission})
        
        try:
            import weasyprint
            pdf_bytes = weasyprint.HTML(string=html_string).write_pdf()
            response = HttpResponse(pdf_bytes, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="Admission_Form_{admission.application_number}.pdf"'
            
            record_event(
                request,
                action="export",
                entity_type="admission_request",
                entity_id=admission.id,
                message=f"Exported PDF for {admission.application_number}",
            )
            return response
        except Exception as e:
            logger.exception("Failed to generate PDF")
            return Response({"detail": f"PDF Generation Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["post"], url_path="bulk-approve")
    def bulk_approve(self, request):
        ids = request.data.get("ids", [])
        if not ids:
            return Response({"detail": "ids list is required."}, status=status.HTTP_400_BAD_REQUEST)

        admissions = AdmissionRequest.objects.filter(id__in=ids, hostel=request.hostel, status__in=["PENDING", "UNDER_REVIEW"])
        count = 0
        errors = []
        for adm in admissions:
            try:
                approve_admission(adm, request.user, decision_note="Bulk approved.")
                count += 1
            except Exception as e:
                errors.append(f"Failed to approve {adm.application_number}: {str(e)}")

        record_event(
            request,
            action="update",
            entity_type="admission_request",
            entity_id="bulk",
            message=f"Bulk approved {count} admissions",
        )

        return Response({"approved_count": count, "errors": errors})

    @action(detail=False, methods=["post"], url_path="bulk-reject")
    def bulk_reject(self, request):
        ids = request.data.get("ids", [])
        if not ids:
            return Response({"detail": "ids list is required."}, status=status.HTTP_400_BAD_REQUEST)

        admissions = AdmissionRequest.objects.filter(id__in=ids, hostel=request.hostel, status__in=["PENDING", "UNDER_REVIEW"])
        count = admissions.update(
            status="REJECTED",
            decision_note="Bulk rejected by administrator.",
            decided_by=request.user,
            decided_at=timezone.now(),
            updated_at=timezone.now(),
        )

        record_event(
            request,
            action="update",
            entity_type="admission_request",
            entity_id="bulk",
            message=f"Bulk rejected {count} admissions",
        )

        return Response({"rejected_count": count})

    @action(detail=False, methods=["get"], url_path="export-excel")
    def export_excel(self, request):
        hostel = request.hostel
        queryset = self.get_queryset()

        headers = [
            "Application Number", "Date", "Full Name", "Phone", "Email", 
            "Status", "Source", "Gender", "District", "Guardian Name", 
            "Educational Institute", "Current Level", "Preferred Room Type"
        ]
        rows = []
        for item in queryset:
            rows.append([
                item.application_number,
                str(item.application_date),
                item.full_name,
                item.phone,
                item.email,
                item.status,
                item.source,
                item.gender,
                item.district,
                item.local_guardian_name or item.father_name,
                item.educational_institute,
                item.current_level,
                item.preferred_room_type,
            ])

        from apps.exports.views import csv_response
        
        record_event(
            request,
            action="export",
            entity_type="admission_request",
            entity_id="list",
            message=f"Exported admissions Excel list for {hostel.code}",
        )
        return csv_response(f"{hostel.code}_admissions.csv", headers, rows)

    @action(detail=False, methods=["get"], url_path="analytics")
    def analytics(self, request):
        from django.db.models import Count, Sum
        hostel = request.hostel
        today = timezone.localdate()
        this_month = today.month
        this_year = today.year

        qs = AdmissionRequest.objects.filter(hostel=hostel)

        today_count = qs.filter(created_at__date=today).count()
        monthly_count = qs.filter(created_at__year=this_year, created_at__month=this_month).count()

        # Counts by status
        status_counts = dict(qs.values_list("status").annotate(Count("id")))
        
        # Complete pending stats
        pending_total = (
            status_counts.get("PENDING", 0) +
            status_counts.get("UNDER_REVIEW", 0) +
            status_counts.get("VERIFICATION_PENDING", 0) +
            status_counts.get("WAITLISTED", 0) +
            status_counts.get("INTERVIEW_REQUIRED", 0)
        )

        # Distributions
        food_dist = dict(qs.values_list("food_preference").annotate(Count("id")))
        level_dist = dict(qs.values_list("current_level").annotate(Count("id")))
        district_dist = dict(qs.values_list("district").annotate(Count("id")))

        # Revenue
        rev_approved = qs.filter(status="APPROVED").aggregate(
            adm=Sum("admission_fee"),
            app=Sum("application_fee"),
            sec=Sum("security_deposit")
        )
        revenue_sum = (
            (rev_approved["adm"] or 0) + 
            (rev_approved["app"] or 0) + 
            (rev_approved["sec"] or 0)
        )

        # Occupancy %
        from apps.rooms.models import Bed
        total_beds = Bed.objects.filter(room__hostel=hostel).count()
        occupied_beds = Bed.objects.filter(room__hostel=hostel, status="OCCUPIED").count()
        occupancy_pct = (occupied_beds / total_beds * 100) if total_beds > 0 else 0

        # Recent Admissions
        recent = qs.order_by("-created_at")[:10]
        recent_data = AdmissionRequestSerializer(recent, many=True, context={"request": request}).data

        return Response({
            "cards": {
                "today": today_count,
                "pending": pending_total,
                "approved": status_counts.get("APPROVED", 0),
                "rejected": status_counts.get("REJECTED", 0),
                "monthly": monthly_count,
                "occupancy": round(occupancy_pct, 1),
                "revenue": float(revenue_sum),
            },
            "recent": recent_data,
            "charts": {
                "food": food_dist,
                "education": level_dist,
                "district": district_dist,
                "status": status_counts,
            }
        })


class PublicAdmissionRequestViewSet(AdmissionRequestViewSet):
    permission_classes = [AllowAny, HasHostelContext]
    http_method_names = ["post", "options"]

    def perform_create(self, serializer):
        hostel = self.request.hostel
        retries = 3
        while retries > 0:
            app_num = get_next_application_number(hostel)
            fee = hostel.settings.get("default_application_fee", 500.00)
            try:
                with transaction.atomic():
                    instance = serializer.save(
                        hostel=hostel,
                        application_number=app_num,
                        application_fee=fee,
                        application_date=timezone.localdate(),
                        source="PUBLIC",
                        status="PENDING",
                    )
                    # Record audit log
                    record_event(
                        self.request,
                        action="create",
                        entity_type="admission_request",
                        entity_id=instance.id,
                        message=f"Created public admission request {app_num}",
                    )
                    return
            except IntegrityError:
                retries -= 1
                if retries == 0:
                    raise
