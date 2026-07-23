from rest_framework import serializers
from apps.common.serializers import HostelScopedSerializer
from django.db import transaction
from .models import Payment, PaymentAllocation, Receipt

class PaymentAllocationSerializer(HostelScopedSerializer):
    class Meta:
        model = PaymentAllocation
        fields = "__all__"

class ReceiptSerializer(HostelScopedSerializer):
    class Meta:
        model = Receipt
        fields = "__all__"

class PaymentSerializer(HostelScopedSerializer):
    allocations = PaymentAllocationSerializer(many=True, read_only=True)
    receipt = ReceiptSerializer(read_only=True)

    class Meta:
        model = Payment
        fields = "__all__"

class PaymentCreateSerializer(HostelScopedSerializer):
    allocations = serializers.ListField(child=serializers.DictField(), write_only=True)

    class Meta:
        model = Payment
        fields = ["id","student","amount","date","method","reference_no","allocations"]

    def create(self, validated_data):
        allocations = validated_data.pop("allocations", [])
        hostel = self.context["request"].hostel

        from .services import allocate_payment

        try:
            with transaction.atomic():
                payment = Payment.objects.create(hostel=hostel, **validated_data)
                allocate_payment(hostel, payment, allocations)
        except (KeyError, ValueError) as exc:
            raise serializers.ValidationError({"allocations": str(exc)}) from exc

        return payment
