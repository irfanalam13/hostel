from rest_framework import viewsets
from apps.common.permissions import HasHostelContext, IsStaffOrReadOnly
from .models import Payment, Receipt
from .serializers import PaymentSerializer, PaymentCreateSerializer, ReceiptSerializer

class HostelScopedViewSet(viewsets.ModelViewSet):
    permission_classes = [HasHostelContext, IsStaffOrReadOnly]

    def get_queryset(self):
        return self.queryset.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel)

class PaymentViewSet(HostelScopedViewSet):
    queryset = Payment.objects.select_related("student").prefetch_related("allocations","receipt").all().order_by("-date")
    filterset_fields = ["student","method","date"]
    search_fields = ["student__full_name","student__phone","reference_no"]
    ordering_fields = ["date","amount","created_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return PaymentCreateSerializer
        return PaymentSerializer

class ReceiptViewSet(HostelScopedViewSet):
    queryset = Receipt.objects.select_related("payment","payment__student").all().order_by("-created_at")
    serializer_class = ReceiptSerializer
    search_fields = ["receipt_no","payment__student__full_name"]