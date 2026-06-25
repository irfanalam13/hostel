from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
import datetime as dt
from apps.common.permissions import HasHostelContext, IsStaffOrReadOnly, IsOwnerOrManager
from apps.common.utils import month_key
from .models import FeePlan, StudentFeePlan, FeeLedger
from .serializers import FeePlanSerializer, StudentFeePlanSerializer, FeeLedgerSerializer
from .services import generate_monthly_ledger

class HostelScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [HasHostelContext, IsStaffOrReadOnly]

    def get_queryset(self):
        return self.queryset.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel)

class FeePlanViewSet(HostelScopedViewSet):
    queryset = FeePlan.objects.all().order_by("name")
    serializer_class = FeePlanSerializer
    filterset_fields = ["is_active"]
    search_fields = ["name"]

class StudentFeePlanViewSet(HostelScopedViewSet):
    queryset = StudentFeePlan.objects.select_related("student","fee_plan").all().order_by("-created_at")
    serializer_class = StudentFeePlanSerializer
    filterset_fields = ["student","fee_plan"]

class FeeLedgerViewSet(HostelScopedViewSet):
    queryset = FeeLedger.objects.select_related("student").all().order_by("-month","student__full_name")
    serializer_class = FeeLedgerSerializer
    filterset_fields = ["month","status","student"]
    search_fields = ["student__full_name","student__phone"]

    @action(detail=False, methods=["post"], permission_classes=[HasHostelContext, IsOwnerOrManager])
    def generate_month(self, request):
        month = request.data.get("month")
        if not month:
            month = month_key(dt.date.today())
        data = generate_monthly_ledger(request.hostel, month)
        return Response(data)