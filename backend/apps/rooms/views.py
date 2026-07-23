from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.common.permissions import HasHostelContext, IsStaffOrReadOnly
from apps.auditlog.services import record_event
from .models import Block, Floor, Room, Bed, BedAssignment
from .serializers import (
    BlockSerializer,
    FloorSerializer,
    RoomSerializer,
    BedSerializer,
    BedAssignmentSerializer,
)

class HostelScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [HasHostelContext, IsStaffOrReadOnly]

    def get_queryset(self):
        return self.queryset.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel)

class BlockViewSet(HostelScopedViewSet):
    queryset = Block.objects.all().order_by("name")
    serializer_class = BlockSerializer
    search_fields = ["name", "code"]
    ordering_fields = ["name", "created_at"]

class FloorViewSet(HostelScopedViewSet):
    queryset = Floor.objects.select_related("block").all().order_by("block__name", "number", "name")
    serializer_class = FloorSerializer
    search_fields = ["name", "block__name"]
    filterset_fields = ["block"]
    ordering_fields = ["number", "name", "created_at"]

class RoomViewSet(HostelScopedViewSet):
    queryset = Room.objects.select_related("block", "floor_ref").all().order_by("room_no")
    serializer_class = RoomSerializer
    search_fields = ["room_no", "floor", "block__name", "floor_ref__name", "room_type"]
    filterset_fields = ["block", "floor_ref", "status", "gender_type"]
    ordering_fields = ["room_no", "created_at", "rent", "capacity"]

    def perform_create(self, serializer):
        from apps.subscriptions.gates import enforce_limit

        enforce_limit(self.request.hostel, "max_rooms")
        super().perform_create(serializer)

class BedViewSet(HostelScopedViewSet):
    # room__block / room__floor_ref are rendered by the nested RoomSerializer,
    # so join them here or every bed in a list costs two extra queries.
    queryset = Bed.objects.select_related("room", "room__block", "room__floor_ref").all().order_by("room__room_no","bed_no")
    serializer_class = BedSerializer
    search_fields = ["bed_no","room__room_no"]
    filterset_fields = ["status", "room"]
    ordering_fields = ["bed_no","created_at","status"]

    def perform_create(self, serializer):
        from apps.subscriptions.gates import enforce_limit

        enforce_limit(self.request.hostel, "max_beds")
        super().perform_create(serializer)

class BedAssignmentViewSet(HostelScopedViewSet):
    queryset = BedAssignment.objects.select_related("bed","student").all().order_by("-start_date")
    serializer_class = BedAssignmentSerializer
    filterset_fields = ["is_active","student","bed"]

    def perform_create(self, serializer):
        assignment = serializer.save(hostel=self.request.hostel)
        if assignment.is_active:
            assignment.bed.status = "OCCUPIED"
            assignment.bed.save(update_fields=["status", "updated_at"])

    def perform_update(self, serializer):
        assignment = serializer.save()
        has_active = assignment.bed.assignments.filter(is_active=True).exclude(pk=assignment.pk).exists()
        assignment.bed.status = "OCCUPIED" if assignment.is_active or has_active else "AVAILABLE"
        assignment.bed.save(update_fields=["status", "updated_at"])

    @action(detail=False, methods=["post"], url_path="transfer")
    def transfer(self, request):
        """Move a student from their current bed to another, atomically.

        Closes the active assignment (freeing the old bed) and opens a new one
        (occupying the target bed). Both rows survive as the student's history;
        the new row links back via previous_assignment. Initial assignment is
        NOT done here — that happens at admission approval.
        """
        student_id = request.data.get("student")
        bed_id = request.data.get("bed")
        note = (request.data.get("note") or "").strip()

        if not student_id or not bed_id:
            return Response({"detail": "student and bed are required."}, status=status.HTTP_400_BAD_REQUEST)

        current = (
            BedAssignment.objects.filter(hostel=request.hostel, student_id=student_id, is_active=True)
            .select_related("bed", "bed__room")
            .first()
        )
        if not current:
            return Response(
                {"detail": "Student has no active bed assignment to transfer. Assign a bed via admission approval first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            target = Bed.objects.select_related("room").get(pk=bed_id, room__hostel=request.hostel)
        except Bed.DoesNotExist:
            return Response({"detail": "Target bed not found."}, status=status.HTTP_404_NOT_FOUND)

        if target.id == current.bed_id:
            return Response({"detail": "Student is already assigned to this bed."}, status=status.HTTP_400_BAD_REQUEST)
        if target.status == "MAINTENANCE":
            return Response({"detail": "Target bed is under maintenance."}, status=status.HTTP_400_BAD_REQUEST)
        if BedAssignment.objects.filter(bed=target, is_active=True).exists():
            return Response({"detail": "Target bed already has an active assignment."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            old_bed = current.bed
            current.is_active = False
            current.end_date = timezone.localdate()
            current.save(update_fields=["is_active", "end_date", "updated_at"])
            old_bed.status = "AVAILABLE"
            old_bed.save(update_fields=["status", "updated_at"])

            new_assignment = BedAssignment.objects.create(
                hostel=request.hostel,
                bed=target,
                student_id=student_id,
                start_date=timezone.localdate(),
                is_active=True,
                reason="TRANSFER",
                note=note,
                created_by=request.user,
                previous_assignment=current,
            )
            target.status = "OCCUPIED"
            target.save(update_fields=["status", "updated_at"])

        record_event(
            request,
            action="update",
            entity_type="bed_assignment",
            entity_id=new_assignment.id,
            message=(
                f"Transferred student from {old_bed.room.room_no}-{old_bed.bed_no} "
                f"to {target.room.room_no}-{target.bed_no}"
            ),
        )

        serializer = self.get_serializer(new_assignment)
        return Response(serializer.data, status=status.HTTP_200_OK)
