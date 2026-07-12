"""Finance serializers.

Every relational field is constrained to the request's workspace at
construction time (``_HostelScopedRelationsMixin``) so a payload can never
reference another tenant's rows. Money rollups (invoice totals, paid amounts,
receipt numbers) are read-only — the service layer owns them.
"""
from rest_framework import serializers

from apps.residents.models import Resident

from .models import (
    Budget,
    Discount,
    Expense,
    ExpenseCategory,
    FeeAssignment,
    FeeCategory,
    FeeStructure,
    Income,
    Invoice,
    InvoiceAdjustment,
    InvoiceLine,
    LedgerTransaction,
    PaymentRecord,
    Refund,
    Scholarship,
    ScholarshipAward,
)


class _HostelScopedRelationsMixin:
    """Restrict the querysets of listed relational fields to ``request.hostel``."""

    scoped_relations: dict = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        hostel = getattr(request, "hostel", None)
        for field_name, model in self.scoped_relations.items():
            field = self.fields.get(field_name)
            if field is not None and hostel is not None:
                field.queryset = model.objects.filter(hostel=hostel)


# --------------------------------------------------------------------------- #
# Fees
# --------------------------------------------------------------------------- #
class FeeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeCategory
        fields = [
            "id", "name", "code", "description", "is_system", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]


class FeeStructureSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"category": FeeCategory}
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)

    class Meta:
        model = FeeStructure
        fields = [
            "id", "name", "category", "category_name", "description", "amount",
            "recurrence", "tax_rate", "allow_installments", "due_day",
            "grace_period_days", "late_fine_type", "late_fine_amount",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "category_name", "created_at", "updated_at"]


class FeeAssignmentSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"fee_structure": FeeStructure, "resident": Resident}
    fee_name = serializers.CharField(source="fee_structure.name", read_only=True)
    resident_name = serializers.CharField(source="resident.full_name", read_only=True)
    effective_amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = FeeAssignment
        fields = [
            "id", "fee_structure", "fee_name", "resident", "resident_name",
            "amount_override", "effective_amount", "start_date", "end_date",
            "status", "waived_reason", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "fee_name", "resident_name", "effective_amount",
                            "created_at", "updated_at"]


class BulkFeeAssignmentSerializer(_HostelScopedRelationsMixin, serializers.Serializer):
    """Assign one fee structure to many residents in a single call."""

    scoped_relations = {"fee_structure": FeeStructure}

    fee_structure = serializers.PrimaryKeyRelatedField(queryset=FeeStructure.objects.none())
    resident_ids = serializers.ListField(
        child=serializers.UUIDField(), allow_empty=False, max_length=500
    )
    amount_override = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )
    start_date = serializers.DateField(required=False)


# --------------------------------------------------------------------------- #
# Discounts & scholarships
# --------------------------------------------------------------------------- #
class DiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Discount
        fields = [
            "id", "name", "discount_type", "value", "reason", "description",
            "valid_from", "valid_until", "max_uses", "used_count", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "used_count", "created_at", "updated_at"]


class ScholarshipSerializer(serializers.ModelSerializer):
    awards_count = serializers.IntegerField(read_only=True, default=0)

    class Meta:
        model = Scholarship
        fields = [
            "id", "name", "scholarship_type", "award_type", "value",
            "description", "is_active", "awards_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "awards_count", "created_at", "updated_at"]


class ScholarshipAwardSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"scholarship": Scholarship, "resident": Resident}
    scholarship_name = serializers.CharField(source="scholarship.name", read_only=True)
    resident_name = serializers.CharField(source="resident.full_name", read_only=True)

    class Meta:
        model = ScholarshipAward
        fields = [
            "id", "scholarship", "scholarship_name", "resident", "resident_name",
            "status", "valid_from", "valid_until", "note", "approved_by",
            "approved_at", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "scholarship_name", "resident_name", "status",
                            "approved_by", "approved_at", "created_at", "updated_at"]


# --------------------------------------------------------------------------- #
# Invoicing
# --------------------------------------------------------------------------- #
class InvoiceLineSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"fee_structure": FeeStructure}

    class Meta:
        model = InvoiceLine
        fields = [
            "id", "fee_structure", "description", "quantity", "unit_price",
            "tax_rate", "amount", "tax_amount",
        ]
        read_only_fields = ["id", "amount", "tax_amount"]


class InvoiceAdjustmentSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"discount": Discount, "scholarship_award": ScholarshipAward}

    class Meta:
        model = InvoiceAdjustment
        fields = ["id", "kind", "discount", "scholarship_award", "amount", "note"]
        read_only_fields = ["id"]
        extra_kwargs = {"amount": {"required": False}}


class PaymentBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentRecord
        fields = [
            "id", "receipt_number", "amount", "method", "status", "reference",
            "received_at",
        ]


class InvoiceSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"resident": Resident}
    resident_name = serializers.CharField(source="resident.full_name", read_only=True)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, read_only=True)
    lines = InvoiceLineSerializer(many=True, read_only=True)
    adjustments = InvoiceAdjustmentSerializer(many=True, read_only=True)
    payments = PaymentBriefSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "number", "resident", "resident_name", "status", "issue_date",
            "due_date", "currency", "subtotal", "tax_total", "discount_total",
            "scholarship_total", "total", "paid_amount", "balance", "notes",
            "terms", "lines", "adjustments", "payments", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "number", "resident_name", "status", "subtotal", "tax_total",
            "discount_total", "scholarship_total", "total", "paid_amount",
            "balance", "lines", "adjustments", "payments", "created_at", "updated_at",
        ]


class InvoiceCreateSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    """Create payload: header fields + nested lines and adjustments. The
    service computes every amount; clients only send quantities and rates."""

    scoped_relations = {"resident": Resident}
    lines = InvoiceLineSerializer(many=True)
    adjustments = InvoiceAdjustmentSerializer(many=True, required=False)
    as_draft = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model = Invoice
        fields = [
            "resident", "issue_date", "due_date", "currency", "notes", "terms",
            "lines", "adjustments", "as_draft",
        ]
        extra_kwargs = {"currency": {"required": False}}

    def validate_lines(self, value):
        if not value:
            raise serializers.ValidationError("An invoice needs at least one line.")
        return value

    def validate(self, attrs):
        # Nested serializers are constructed without request context, so the
        # scoped-relations mixin can't constrain their querysets — enforce the
        # workspace boundary on every nested relation here instead.
        hostel = getattr(self.context.get("request"), "hostel", None)
        if hostel is not None:
            for line in attrs.get("lines", []):
                fee = line.get("fee_structure")
                if fee is not None and fee.hostel_id != hostel.id:
                    raise serializers.ValidationError(
                        {"lines": "Unknown fee structure."}
                    )
            for adj in attrs.get("adjustments", []):
                for rel in (adj.get("discount"), adj.get("scholarship_award")):
                    if rel is not None and rel.hostel_id != hostel.id:
                        raise serializers.ValidationError(
                            {"adjustments": "Unknown discount or scholarship."}
                        )
        return attrs


# --------------------------------------------------------------------------- #
# Collection
# --------------------------------------------------------------------------- #
class PaymentRecordSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"invoice": Invoice, "resident": Resident}
    resident_name = serializers.CharField(source="resident.full_name", read_only=True, default=None)
    invoice_number = serializers.CharField(source="invoice.number", read_only=True, default=None)

    class Meta:
        model = PaymentRecord
        fields = [
            "id", "receipt_number", "invoice", "invoice_number", "resident",
            "resident_name", "amount", "method", "status", "reference", "note",
            "proof", "received_at", "recorded_by", "verified_by", "verified_at",
            "created_at",
        ]
        read_only_fields = [
            "id", "receipt_number", "invoice_number", "resident_name", "status",
            "recorded_by", "verified_by", "verified_at", "created_at",
        ]

    def validate(self, attrs):
        invoice = attrs.get("invoice")
        resident = attrs.get("resident")
        if invoice is None and resident is None:
            raise serializers.ValidationError(
                {"detail": "A payment needs an invoice or a resident."}
            )
        if invoice is not None and invoice.status in (
            Invoice.Status.CANCELLED, Invoice.Status.REFUNDED
        ):
            raise serializers.ValidationError(
                {"invoice": "This invoice is closed and cannot accept payments."}
            )
        return attrs


# --------------------------------------------------------------------------- #
# Expenses / income / refunds / budgets
# --------------------------------------------------------------------------- #
class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = [
            "id", "name", "code", "description", "is_system", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at"]


class ExpenseSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"category": ExpenseCategory}
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)

    class Meta:
        model = Expense
        fields = [
            "id", "category", "category_name", "title", "description", "amount",
            "tax_amount", "expense_date", "payment_method", "vendor_name",
            "vendor_contact", "reference", "status", "recurrence", "attachment",
            "created_by", "approved_by", "approved_at", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "category_name", "status", "created_by", "approved_by",
            "approved_at", "created_at", "updated_at",
        ]


class IncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Income
        fields = [
            "id", "source", "title", "description", "amount", "income_date",
            "payment_method", "reference", "attachment", "recorded_by",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "recorded_by", "created_at", "updated_at"]


class RefundSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {
        "payment": PaymentRecord,
        "invoice": Invoice,
        "resident": Resident,
    }
    resident_name = serializers.CharField(source="resident.full_name", read_only=True, default=None)
    invoice_number = serializers.CharField(source="invoice.number", read_only=True, default=None)
    payment_receipt = serializers.CharField(
        source="payment.receipt_number", read_only=True, default=None
    )

    class Meta:
        model = Refund
        fields = [
            "id", "refund_type", "payment", "payment_receipt", "invoice",
            "invoice_number", "resident", "resident_name", "amount", "method",
            "reason", "status", "requested_by", "approved_by", "processed_at",
            "note", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "payment_receipt", "invoice_number", "resident_name", "status",
            "requested_by", "approved_by", "processed_at", "created_at", "updated_at",
        ]

    def validate(self, attrs):
        payment = attrs.get("payment")
        amount = attrs.get("amount")
        if payment is not None and amount is not None and amount > payment.amount:
            raise serializers.ValidationError(
                {"amount": "Refund cannot exceed the original payment amount."}
            )
        return attrs


class BudgetSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"category": ExpenseCategory}
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)
    spent = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = [
            "id", "name", "category", "category_name", "period_year",
            "period_month", "amount", "spent", "note", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "category_name", "spent", "created_at", "updated_at"]

    def get_spent(self, obj) -> str:
        from django.db.models import Sum

        from .models import Expense

        qs = Expense.objects.filter(
            hostel=obj.hostel, status=Expense.Status.PAID,
            expense_date__year=obj.period_year,
        )
        if obj.period_month:
            qs = qs.filter(expense_date__month=obj.period_month)
        if obj.category_id:
            qs = qs.filter(category=obj.category)
        total = qs.aggregate(s=Sum("amount"))["s"] or 0
        return str(total)


class LedgerTransactionSerializer(serializers.ModelSerializer):
    resident_name = serializers.CharField(source="resident.full_name", read_only=True, default=None)

    class Meta:
        model = LedgerTransaction
        fields = [
            "id", "direction", "category", "amount", "method", "occurred_at",
            "entity_type", "entity_id", "resident", "resident_name", "memo",
        ]
        read_only_fields = fields
