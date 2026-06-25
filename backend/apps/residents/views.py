from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.common.permissions import IsHostelResolved, IsStaff
from .models import Resident, BedAssignmentHistory, Stay
from .serializers import ResidentSerializer, StaySerializer

class ResidentViewSet(ModelViewSet):
    serializer_class = ResidentSerializer
    permission_classes = [IsHostelResolved, IsStaff]
    search_fields = ["full_name", "phone"]
    ordering_fields = ["created_at", "full_name", "join_date"]

    def get_queryset(self):
        # prefetch bed_history: the serializer nests it, so without this a list
        # of N residents fires N extra queries (classic N+1).
        return (
            Resident.objects.filter(hostel=self.request.hostel)
            .prefetch_related("bed_history")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        resident = serializer.save(hostel=self.request.hostel)
        if resident.current_bed:
            BedAssignmentHistory.objects.create(
                hostel=self.request.hostel, resident=resident, bed=resident.current_bed
            )

    def perform_update(self, serializer):
        old = self.get_object()
        new = serializer.save()

        if old.current_bed_id != new.current_bed_id:
            BedAssignmentHistory.objects.filter(
                hostel=self.request.hostel,
                resident=new,
                end_at__isnull=True
            ).update(end_at=timezone.now())
            if new.current_bed:
                BedAssignmentHistory.objects.create(
                    hostel=self.request.hostel, resident=new, bed=new.current_bed
                )

    @action(detail=True, methods=["post"])
    def mark_went_home(self, request, pk=None):
        r = self.get_object()
        r.status = "went_home"
        r.save(update_fields=["status", "updated_at"])
        return Response({"status": "ok", "resident": str(r.id)})

    @action(detail=True, methods=["post"])
    def mark_active(self, request, pk=None):
        r = self.get_object()
        r.status = "active"
        r.save(update_fields=["status", "updated_at"])
        return Response({"status": "ok"})

    @action(detail=True, methods=["post"])
    def checkout(self, request, pk=None):
        r = self.get_object()

        # Refuse checkout while the resident still owes money, unless the caller
        # explicitly overrides (e.g. waiving the balance). Imported lazily to
        # avoid a circular import (billing.models -> residents.models).
        force = str(request.data.get("force", "")).lower() in ("1", "true", "yes")
        if not force:
            from apps.billing.models import MonthlyDue

            outstanding = MonthlyDue.objects.filter(
                resident=r, amount__gt=F("paid_amount")
            )
            if outstanding.exists():
                return Response(
                    {
                        "detail": "Resident has outstanding dues. Settle them or pass "
                        "force=true to override.",
                        "outstanding_months": outstanding.count(),
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        checkout_date = request.data.get("checkout_date") or timezone.localdate()
        with transaction.atomic():
            BedAssignmentHistory.objects.filter(
                hostel=self.request.hostel,
                resident=r,
                end_at__isnull=True,
            ).update(end_at=timezone.now())
            Stay.objects.filter(resident=r, is_active=True).update(
                is_active=False, check_out=checkout_date
            )
            r.status = "left"
            r.leave_date = checkout_date
            r.current_bed = None
            r.save(update_fields=["status", "leave_date", "current_bed", "updated_at"])
        return Response({"status": "ok", "resident": str(r.id)})

class StayViewSet(ModelViewSet):
    serializer_class = StaySerializer
    permission_classes = [IsHostelResolved, IsStaff]
    filterset_fields = ["resident", "bed", "is_active"]

    def get_queryset(self):
        return Stay.objects.filter(resident__hostel=self.request.hostel).order_by("-check_in")
