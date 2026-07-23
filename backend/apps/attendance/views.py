from rest_framework.viewsets import ModelViewSet
from apps.common.permissions import IsHostelResolved, IsStaff
from .models import Attendance
from .serializers import AttendanceSerializer

class AttendanceViewSet(ModelViewSet):
    serializer_class = AttendanceSerializer
    permission_classes = [IsHostelResolved, IsStaff]
    filterset_fields = ["date", "status", "resident"]

    def get_queryset(self):
        return Attendance.objects.filter(hostel=self.request.hostel).select_related("resident")

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel)