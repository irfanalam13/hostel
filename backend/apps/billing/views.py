from datetime import date
from django.db.models import Sum
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.common.permissions import IsHostelResolved, IsStaff, IsOwnerOrManager
from apps.residents.models import Resident
from .models import MonthlyDue, Payment
from .serializers import MonthlyDueSerializer, PaymentSerializer
from .services import recalc_due_paid_amount

class MonthlyDueViewSet(ModelViewSet):
    serializer_class = MonthlyDueSerializer
    permission_classes = [IsHostelResolved, IsStaff]
    filterset_fields = ["year", "month", "resident"]

    def get_queryset(self):
        return MonthlyDue.objects.filter(hostel=self.request.hostel).select_related("resident")

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel)

class PaymentViewSet(ModelViewSet):
    serializer_class = PaymentSerializer
    permission_classes = [IsHostelResolved, IsStaff]
    throttle_scope = "payment"
    filterset_fields = ["resident", "method", "due"]

    def get_queryset(self):
        return Payment.objects.filter(hostel=self.request.hostel).select_related("resident", "due")

    def perform_create(self, serializer):
        payment = serializer.save(hostel=self.request.hostel)
        if payment.due_id:
            recalc_due_paid_amount(payment.due)

    def perform_update(self, serializer):
        payment = serializer.save()
        if payment.due_id:
            recalc_due_paid_amount(payment.due)

    def perform_destroy(self, instance):
        due = instance.due
        super().perform_destroy(instance)
        if due:
            recalc_due_paid_amount(due)

class DashboardViewSet(ModelViewSet):
    """
    fake ViewSet only for dashboard endpoints via @action
    """
    permission_classes = [IsHostelResolved, IsOwnerOrManager]
    http_method_names = ["get"]
    queryset = MonthlyDue.objects.none()

    @action(detail=False, methods=["get"])
    def summary(self, request):
        today = date.today()
        year, month = today.year, today.month

        dues_qs = MonthlyDue.objects.filter(hostel=request.hostel, year=year, month=month)
        total_due = dues_qs.aggregate(s=Sum("amount"))["s"] or 0
        total_paid = dues_qs.aggregate(s=Sum("paid_amount"))["s"] or 0
        pending = total_due - total_paid

        active_residents = Resident.objects.filter(hostel=request.hostel, status="active").count()

        return Response({
            "month": month,
            "year": year,
            "total_due": total_due,
            "total_paid": total_paid,
            "pending": pending if pending > 0 else 0,
            "active_residents": active_residents,
        })