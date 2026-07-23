from rest_framework import serializers
from .models import MonthlyDue, Payment

class MonthlyDueSerializer(serializers.ModelSerializer):
    remaining = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = MonthlyDue
        fields = ["id", "resident", "year", "month", "amount", "paid_amount", "remaining", "created_at"]
        read_only_fields = ["id", "paid_amount", "remaining", "created_at"]

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "resident", "due", "amount", "method", "note", "received_at", "created_at"]
        read_only_fields = ["id", "created_at"]