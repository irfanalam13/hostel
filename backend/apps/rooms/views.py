from rest_framework import viewsets
from apps.common.permissions import HasHostelContext, IsStaffOrReadOnly
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
