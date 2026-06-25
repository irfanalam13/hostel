from rest_framework.viewsets import ModelViewSet
from apps.common.permissions import IsHostelResolved, IsStaff
from .models import Room, Bed
from .serializers import RoomSerializer, BedSerializer

class TenantQuerySetMixin:
    def get_queryset(self):
        return self.queryset.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel)

class RoomViewSet(TenantQuerySetMixin, ModelViewSet):
    queryset = Room.objects.all().order_by("number")
    serializer_class = RoomSerializer
    permission_classes = [IsHostelResolved, IsStaff]
    search_fields = ["number", "floor"]
    ordering_fields = ["number", "created_at"]

class BedViewSet(TenantQuerySetMixin, ModelViewSet):
    queryset = Bed.objects.all().select_related("room").order_by("created_at")
    serializer_class = BedSerializer
    permission_classes = [IsHostelResolved, IsStaff]
    search_fields = ["label", "room__number"]