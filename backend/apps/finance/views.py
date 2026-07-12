"""Finance Management API.

All viewsets are workspace-scoped (``request.hostel``), permission-gated via
``apps.common.rbac`` (``finance.*`` catalog) and plan-gated behind the
``finance`` feature. Mutations are audit-logged; money math and lifecycle
transitions live in ``apps.finance.services``.
"""
import csv
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce, TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet, ViewSet

from apps.auditlog.models import AuditEvent
from apps.auditlog.services import record_event
from apps.common.permissions import IsHostelResolved
from apps.common.rbac import ActionPermissions
from apps.residents.models import Resident
from apps.subscriptions.gates import RequiresFeature

from . import services
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
    LedgerTransaction,
    PaymentRecord,
    Refund,
    Scholarship,
    ScholarshipAward,
)
from .serializers import (
    BudgetSerializer,
    BulkFeeAssignmentSerializer,
    DiscountSerializer,
    ExpenseCategorySerializer,
    ExpenseSerializer,
    FeeAssignmentSerializer,
    FeeCategorySerializer,
    FeeStructureSerializer,
    IncomeSerializer,
    InvoiceCreateSerializer,
    InvoiceSerializer,
    LedgerTransactionSerializer,
    PaymentRecordSerializer,
    RefundSerializer,
    ScholarshipAwardSerializer,
    ScholarshipSerializer,
)

ZERO = Decimal("0.00")
_MONEY = DecimalField(max_digits=14, decimal_places=2)


def _money(value) -> str:
    """Format any money value as a fixed 2-decimal string.

    SQLite's ``Sum`` over a DecimalField drops the scale (returns ``7260`` not
    ``7260.00``); quantizing here keeps the wire format consistent across
    databases and gives clients a stable money shape to parse.
    """
    return str(Decimal(value or 0).quantize(ZERO))


def _notify(hostel, user, title, body, url="/finance", created_by=None):
    """Best-effort in-app/push notification to a single workspace member."""
    if user is None:
        return
    try:
        from apps.notifications.services import create_notification
        from apps.notifications.models import AudienceType

        create_notification(
            hostel=hostel, title=title, body=body, url=url,
            audience=AudienceType.USER, user_ids=[user.id], created_by=created_by,
        )
    except Exception:  # notifications must never break a finance mutation
        pass


class FinanceViewSet(ModelViewSet):
    """Base for all finance CRUD surfaces: membership + RBAC + plan feature."""

    permission_classes = [IsHostelResolved, ActionPermissions, RequiresFeature("finance")]

    def _audit(self, action_, entity_type, obj_id, message, meta=None):
        record_event(
            self.request, action=action_, actor=self.request.user,
            hostel=self.request.hostel, entity_type=entity_type,
            entity_id=obj_id, message=message, meta=meta,
        )


# --------------------------------------------------------------------------- #
# Fees
# --------------------------------------------------------------------------- #
class FeeCategoryViewSet(FinanceViewSet):
    serializer_class = FeeCategorySerializer
    permission_map = {
        "list": ["finance.view"], "retrieve": ["finance.view"],
        "create": ["finance.create"], "update": ["finance.edit"],
        "partial_update": ["finance.edit"], "destroy": ["finance.delete"],
    }
    search_fields = ["name"]

    def get_queryset(self):
        services.ensure_default_categories(self.request.hostel)
        return FeeCategory.objects.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "finance.feecategory", obj.id,
                    f"Fee category created: {obj.name}")

    def perform_destroy(self, instance):
        if instance.is_system:
            raise ValidationError({"detail": "System categories cannot be deleted (deactivate instead)."})
        name, oid = instance.name, instance.id
        instance.delete()
        self._audit(AuditEvent.Action.DELETE, "finance.feecategory", oid,
                    f"Fee category deleted: {name}")


class FeeStructureViewSet(FinanceViewSet):
    serializer_class = FeeStructureSerializer
    permission_map = {
        "list": ["finance.view"], "retrieve": ["finance.view"],
        "create": ["finance.create"], "update": ["finance.edit"],
        "partial_update": ["finance.edit"], "destroy": ["finance.delete"],
    }
    filterset_fields = ["category", "recurrence", "is_active"]
    search_fields = ["name"]

    def get_queryset(self):
        return FeeStructure.objects.filter(hostel=self.request.hostel).select_related("category")

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "finance.feestructure", obj.id,
                    f"Fee structure created: {obj.name}", meta={"amount": str(obj.amount)})

    def perform_update(self, serializer):
        obj = serializer.save()
        self._audit(AuditEvent.Action.UPDATE, "finance.feestructure", obj.id,
                    f"Fee structure updated: {obj.name}")

    def perform_destroy(self, instance):
        name, oid = instance.name, instance.id
        instance.delete()
        self._audit(AuditEvent.Action.DELETE, "finance.feestructure", oid,
                    f"Fee structure deleted: {name}")


class FeeAssignmentViewSet(FinanceViewSet):
    serializer_class = FeeAssignmentSerializer
    permission_map = {
        "list": ["finance.view"], "retrieve": ["finance.view"],
        "create": ["finance.create"], "update": ["finance.edit"],
        "partial_update": ["finance.edit"], "destroy": ["finance.delete"],
        "bulk_assign": ["finance.create"], "waive": ["finance.edit"],
    }
    filterset_fields = ["fee_structure", "resident", "status"]

    def get_queryset(self):
        return (
            FeeAssignment.objects.filter(hostel=self.request.hostel)
            .select_related("fee_structure", "resident")
        )

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel, created_by=self.request.user)
        self._audit(AuditEvent.Action.CREATE, "finance.feeassignment", obj.id,
                    f"Fee assigned: {obj.fee_structure.name} → {obj.resident.full_name}")

    @action(detail=False, methods=["post"], url_path="bulk-assign")
    def bulk_assign(self, request):
        """Assign one fee structure to many residents at once."""
        serializer = BulkFeeAssignmentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        residents = Resident.objects.filter(
            hostel=request.hostel, id__in=data["resident_ids"]
        )
        created = [
            FeeAssignment.objects.create(
                hostel=request.hostel,
                fee_structure=data["fee_structure"],
                resident=resident,
                amount_override=data.get("amount_override"),
                start_date=data.get("start_date") or timezone.localdate(),
                created_by=request.user,
            )
            for resident in residents
        ]
        self._audit(AuditEvent.Action.CREATE, "finance.feeassignment", "",
                    f"Bulk fee assignment: {data['fee_structure'].name} → {len(created)} resident(s)")
        return Response({"created": len(created)}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def waive(self, request, pk=None):
        assignment = self.get_object()
        assignment.status = FeeAssignment.Status.WAIVED
        assignment.waived_reason = str(request.data.get("reason", ""))[:255]
        assignment.save(update_fields=["status", "waived_reason", "updated_at"])
        self._audit(AuditEvent.Action.UPDATE, "finance.feeassignment", assignment.id,
                    f"Fee waived: {assignment.fee_structure.name} → {assignment.resident.full_name}")
        return Response(self.get_serializer(assignment).data)


# --------------------------------------------------------------------------- #
# Discounts & scholarships
# --------------------------------------------------------------------------- #
class DiscountViewSet(FinanceViewSet):
    serializer_class = DiscountSerializer
    permission_map = {
        "list": ["finance.view"], "retrieve": ["finance.view"],
        "create": ["finance.create"], "update": ["finance.edit"],
        "partial_update": ["finance.edit"], "destroy": ["finance.delete"],
    }
    filterset_fields = ["discount_type", "reason", "is_active"]
    search_fields = ["name"]

    def get_queryset(self):
        return Discount.objects.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "finance.discount", obj.id,
                    f"Discount created: {obj.name}")

    def perform_update(self, serializer):
        obj = serializer.save()
        self._audit(AuditEvent.Action.UPDATE, "finance.discount", obj.id,
                    f"Discount updated: {obj.name}")

    def perform_destroy(self, instance):
        name, oid = instance.name, instance.id
        instance.delete()
        self._audit(AuditEvent.Action.DELETE, "finance.discount", oid,
                    f"Discount deleted: {name}")


class ScholarshipViewSet(FinanceViewSet):
    serializer_class = ScholarshipSerializer
    permission_map = {
        "list": ["finance.view"], "retrieve": ["finance.view"],
        "create": ["finance.create"], "update": ["finance.edit"],
        "partial_update": ["finance.edit"], "destroy": ["finance.delete"],
    }
    filterset_fields = ["scholarship_type", "award_type", "is_active"]
    search_fields = ["name"]

    def get_queryset(self):
        return (
            Scholarship.objects.filter(hostel=self.request.hostel)
            .annotate(awards_count=Count("awards"))
        )

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "finance.scholarship", obj.id,
                    f"Scholarship created: {obj.name}")

    def perform_update(self, serializer):
        obj = serializer.save()
        self._audit(AuditEvent.Action.UPDATE, "finance.scholarship", obj.id,
                    f"Scholarship updated: {obj.name}")

    def perform_destroy(self, instance):
        name, oid = instance.name, instance.id
        instance.delete()
        self._audit(AuditEvent.Action.DELETE, "finance.scholarship", oid,
                    f"Scholarship deleted: {name}")


class ScholarshipAwardViewSet(FinanceViewSet):
    serializer_class = ScholarshipAwardSerializer
    permission_map = {
        "list": ["finance.view"], "retrieve": ["finance.view"],
        "create": ["finance.create"], "update": ["finance.edit"],
        "partial_update": ["finance.edit"], "destroy": ["finance.delete"],
        "approve": ["finance.approve"], "reject": ["finance.approve"],
        "revoke": ["finance.approve"],
    }
    filterset_fields = ["scholarship", "resident", "status"]

    def get_queryset(self):
        return (
            ScholarshipAward.objects.filter(hostel=self.request.hostel)
            .select_related("scholarship", "resident")
        )

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "finance.scholarshipaward", obj.id,
                    f"Scholarship award requested: {obj.scholarship.name} → {obj.resident.full_name}")

    def _transition(self, request, new_status, message):
        award = self.get_object()
        award.status = new_status
        if new_status == ScholarshipAward.Status.APPROVED:
            award.approved_by = request.user
            award.approved_at = timezone.now()
        award.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        self._audit(AuditEvent.Action.UPDATE, "finance.scholarshipaward", award.id,
                    f"{message}: {award.scholarship.name} → {award.resident.full_name}")
        return Response(self.get_serializer(award).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self._transition(request, ScholarshipAward.Status.APPROVED, "Scholarship approved")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self._transition(request, ScholarshipAward.Status.REJECTED, "Scholarship rejected")

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        return self._transition(request, ScholarshipAward.Status.REVOKED, "Scholarship revoked")


# --------------------------------------------------------------------------- #
# Invoices
# --------------------------------------------------------------------------- #
class InvoiceViewSet(FinanceViewSet):
    permission_map = {
        "list": ["finance.view"], "retrieve": ["finance.view"],
        "create": ["finance.create"], "update": ["finance.edit"],
        "partial_update": ["finance.edit"], "destroy": ["finance.delete"],
        "cancel": ["finance.edit"], "issue": ["finance.edit"],
    }
    filterset_fields = ["resident", "status"]
    search_fields = ["number", "resident__full_name"]
    ordering_fields = ["issue_date", "due_date", "total", "created_at"]

    def get_serializer_class(self):
        return InvoiceCreateSerializer if self.action == "create" else InvoiceSerializer

    def get_queryset(self):
        if self.action == "list":
            services.refresh_overdue(self.request.hostel)
        return (
            Invoice.objects.filter(hostel=self.request.hostel)
            .select_related("resident")
            .prefetch_related("lines", "adjustments", "payments")
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        lines = data.pop("lines")
        adjustments = data.pop("adjustments", [])
        as_draft = data.pop("as_draft", False)
        resident = data.pop("resident")
        invoice = services.create_invoice(
            hostel=request.hostel, actor=request.user, resident=resident,
            lines=lines, adjustments=adjustments,
            status=Invoice.Status.DRAFT if as_draft else Invoice.Status.PENDING,
            **data,
        )
        self._audit(AuditEvent.Action.CREATE, "finance.invoice", invoice.id,
                    f"Invoice created: {invoice.number} ({invoice.total} {invoice.currency})",
                    meta={"resident": str(invoice.resident_id), "total": str(invoice.total)})
        out = InvoiceSerializer(invoice, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def perform_update(self, serializer):
        invoice = serializer.save()
        services.recalc_invoice(invoice)
        self._audit(AuditEvent.Action.UPDATE, "finance.invoice", invoice.id,
                    f"Invoice updated: {invoice.number}")

    def perform_destroy(self, instance):
        if instance.payments.filter(status=PaymentRecord.Status.VERIFIED).exists():
            raise ValidationError(
                {"detail": "Invoices with verified payments cannot be deleted — cancel or refund instead."}
            )
        number, oid = instance.number, instance.id
        instance.delete()
        self._audit(AuditEvent.Action.DELETE, "finance.invoice", oid,
                    f"Invoice deleted: {number}")

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        invoice = self.get_object()
        if invoice.status in (Invoice.Status.PAID, Invoice.Status.REFUNDED):
            raise ValidationError({"detail": "Settled invoices cannot be cancelled — issue a refund."})
        invoice.status = Invoice.Status.CANCELLED
        invoice.save(update_fields=["status", "updated_at"])
        self._audit(AuditEvent.Action.UPDATE, "finance.invoice", invoice.id,
                    f"Invoice cancelled: {invoice.number}")
        return Response(InvoiceSerializer(invoice, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def issue(self, request, pk=None):
        """Promote a draft to a live (pending) invoice."""
        invoice = self.get_object()
        if invoice.status != Invoice.Status.DRAFT:
            raise ValidationError({"detail": "Only draft invoices can be issued."})
        invoice.status = Invoice.Status.PENDING
        invoice.save(update_fields=["status", "updated_at"])
        services.recalc_invoice(invoice)
        self._audit(AuditEvent.Action.UPDATE, "finance.invoice", invoice.id,
                    f"Invoice issued: {invoice.number}")
        return Response(InvoiceSerializer(invoice, context=self.get_serializer_context()).data)


# --------------------------------------------------------------------------- #
# Payments
# --------------------------------------------------------------------------- #
class PaymentRecordViewSet(FinanceViewSet):
    serializer_class = PaymentRecordSerializer
    permission_map = {
        "list": ["finance.view"], "retrieve": ["finance.view"],
        "create": ["finance.collect"], "update": ["finance.edit"],
        "partial_update": ["finance.edit"], "destroy": ["finance.delete"],
        "verify": ["finance.approve"], "cancel": ["finance.edit"],
        "fail": ["finance.edit"],
    }
    filterset_fields = ["invoice", "resident", "status", "method"]
    search_fields = ["receipt_number", "reference", "resident__full_name"]
    ordering_fields = ["received_at", "amount"]

    def get_queryset(self):
        return (
            PaymentRecord.objects.filter(hostel=self.request.hostel)
            .select_related("invoice", "resident")
        )

    def perform_create(self, serializer):
        # `require_verification` (payload flag) parks the payment as pending
        # until someone with finance.approve verifies it; the default settles
        # immediately (receipt minted, ledger posted, invoice refreshed).
        hold = str(self.request.data.get("require_verification", "")).lower() in ("1", "true", "yes")
        payment = serializer.save(
            hostel=self.request.hostel,
            recorded_by=self.request.user,
            status=PaymentRecord.Status.PENDING,
        )
        if not hold:
            services.settle_payment(payment, verified_by=self.request.user)
        self._audit(AuditEvent.Action.PAYMENT, "finance.paymentrecord", payment.id,
                    f"Payment {'recorded (pending verification)' if hold else f'collected: {payment.receipt_number}'}"
                    f" — {payment.amount}",
                    meta={"method": payment.method, "invoice": str(payment.invoice_id or "")})

    def perform_destroy(self, instance):
        if instance.status == PaymentRecord.Status.VERIFIED:
            raise ValidationError(
                {"detail": "Verified payments cannot be deleted — cancel or refund instead."}
            )
        oid = instance.id
        instance.delete()
        self._audit(AuditEvent.Action.DELETE, "finance.paymentrecord", oid, "Payment deleted")

    @action(detail=True, methods=["post"])
    def verify(self, request, pk=None):
        payment = self.get_object()
        if payment.status != PaymentRecord.Status.PENDING:
            raise ValidationError({"detail": "Only pending payments can be verified."})
        services.settle_payment(payment, verified_by=request.user)
        self._audit(AuditEvent.Action.PAYMENT, "finance.paymentrecord", payment.id,
                    f"Payment verified: {payment.receipt_number} — {payment.amount}")
        return Response(self.get_serializer(payment).data)

    def _void(self, request, new_status, label):
        payment = self.get_object()
        if payment.status == PaymentRecord.Status.REFUNDED:
            raise ValidationError({"detail": "Refunded payments cannot change status."})
        services.void_payment(payment, status=new_status)
        self._audit(AuditEvent.Action.UPDATE, "finance.paymentrecord", payment.id,
                    f"Payment {label}: {payment.receipt_number or payment.id}")
        return Response(self.get_serializer(payment).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self._void(request, PaymentRecord.Status.CANCELLED, "cancelled")

    @action(detail=True, methods=["post"])
    def fail(self, request, pk=None):
        return self._void(request, PaymentRecord.Status.FAILED, "marked failed")


# --------------------------------------------------------------------------- #
# Expenses
# --------------------------------------------------------------------------- #
class ExpenseCategoryViewSet(FinanceViewSet):
    serializer_class = ExpenseCategorySerializer
    permission_map = {
        "list": ["finance.view"], "retrieve": ["finance.view"],
        "create": ["finance.create"], "update": ["finance.edit"],
        "partial_update": ["finance.edit"], "destroy": ["finance.delete"],
    }
    search_fields = ["name"]

    def get_queryset(self):
        services.ensure_default_categories(self.request.hostel)
        return ExpenseCategory.objects.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "finance.expensecategory", obj.id,
                    f"Expense category created: {obj.name}")

    def perform_destroy(self, instance):
        if instance.is_system:
            raise ValidationError({"detail": "System categories cannot be deleted (deactivate instead)."})
        name, oid = instance.name, instance.id
        instance.delete()
        self._audit(AuditEvent.Action.DELETE, "finance.expensecategory", oid,
                    f"Expense category deleted: {name}")


class ExpenseViewSet(FinanceViewSet):
    serializer_class = ExpenseSerializer
    permission_map = {
        "list": ["finance.view"], "retrieve": ["finance.view"],
        "create": ["finance.create"], "update": ["finance.edit"],
        "partial_update": ["finance.edit"], "destroy": ["finance.delete"],
        "approve": ["finance.approve"], "reject": ["finance.approve"],
        "mark_paid": ["finance.approve"],
    }
    filterset_fields = ["category", "status", "payment_method"]
    search_fields = ["title", "vendor_name", "reference"]
    ordering_fields = ["expense_date", "amount", "created_at"]

    def get_queryset(self):
        return Expense.objects.filter(hostel=self.request.hostel).select_related("category")

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel, created_by=self.request.user)
        self._audit(AuditEvent.Action.CREATE, "finance.expense", obj.id,
                    f"Expense added: {obj.title} — {obj.amount}")

    def perform_update(self, serializer):
        if serializer.instance.status == Expense.Status.PAID:
            raise ValidationError({"detail": "Paid expenses are locked — record an adjustment instead."})
        obj = serializer.save()
        self._audit(AuditEvent.Action.UPDATE, "finance.expense", obj.id,
                    f"Expense updated: {obj.title}")

    def perform_destroy(self, instance):
        if instance.status == Expense.Status.PAID:
            raise ValidationError({"detail": "Paid expenses cannot be deleted."})
        title, oid = instance.title, instance.id
        instance.delete()
        self._audit(AuditEvent.Action.DELETE, "finance.expense", oid,
                    f"Expense deleted: {title}")

    def _transition(self, request, new_status, message, notify_body=None):
        expense = self.get_object()
        expense.status = new_status
        expense.approved_by = request.user
        expense.approved_at = timezone.now()
        expense.save(update_fields=["status", "approved_by", "approved_at", "updated_at"])
        self._audit(AuditEvent.Action.UPDATE, "finance.expense", expense.id,
                    f"{message}: {expense.title}")
        if notify_body and expense.created_by_id and expense.created_by_id != request.user.id:
            _notify(request.hostel, expense.created_by, message,
                    notify_body.format(title=expense.title, amount=expense.amount),
                    url="/finance/expenses", created_by=request.user)
        return Response(self.get_serializer(expense).data)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        expense = self.get_object()
        if expense.status != Expense.Status.PENDING:
            raise ValidationError({"detail": "Only pending expenses can be approved."})
        return self._transition(request, Expense.Status.APPROVED, "Expense approved",
                                notify_body="“{title}” ({amount}) was approved.")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        expense = self.get_object()
        if expense.status not in (Expense.Status.PENDING, Expense.Status.APPROVED):
            raise ValidationError({"detail": "Only open expenses can be rejected."})
        return self._transition(request, Expense.Status.REJECTED, "Expense rejected",
                                notify_body="“{title}” ({amount}) was rejected.")

    @action(detail=True, methods=["post"], url_path="mark-paid")
    def mark_paid(self, request, pk=None):
        expense = self.get_object()
        if expense.status == Expense.Status.PAID:
            raise ValidationError({"detail": "This expense is already paid."})
        if expense.status == Expense.Status.REJECTED:
            raise ValidationError({"detail": "Rejected expenses cannot be paid."})
        services.mark_expense_paid(expense, actor=request.user)
        self._audit(AuditEvent.Action.UPDATE, "finance.expense", expense.id,
                    f"Expense paid: {expense.title} — {expense.amount}")
        return Response(self.get_serializer(expense).data)


# --------------------------------------------------------------------------- #
# Income
# --------------------------------------------------------------------------- #
class IncomeViewSet(FinanceViewSet):
    serializer_class = IncomeSerializer
    permission_map = {
        "list": ["finance.view"], "retrieve": ["finance.view"],
        "create": ["finance.create"], "update": ["finance.edit"],
        "partial_update": ["finance.edit"], "destroy": ["finance.delete"],
    }
    filterset_fields = ["source", "payment_method"]
    search_fields = ["title", "reference"]
    ordering_fields = ["income_date", "amount", "created_at"]

    def get_queryset(self):
        return Income.objects.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        income = serializer.save(hostel=self.request.hostel, recorded_by=self.request.user)
        services.record_income_transaction(income)
        self._audit(AuditEvent.Action.CREATE, "finance.income", income.id,
                    f"Income recorded: {income.title} — {income.amount}")

    def perform_update(self, serializer):
        income = serializer.save()
        # The ledger row is a frozen copy of the money fields — repost it.
        services.remove_income_transaction(income)
        services.record_income_transaction(income)
        self._audit(AuditEvent.Action.UPDATE, "finance.income", income.id,
                    f"Income updated: {income.title}")

    def perform_destroy(self, instance):
        services.remove_income_transaction(instance)
        title, oid = instance.title, instance.id
        instance.delete()
        self._audit(AuditEvent.Action.DELETE, "finance.income", oid,
                    f"Income deleted: {title}")


# --------------------------------------------------------------------------- #
# Refunds
# --------------------------------------------------------------------------- #
class RefundViewSet(FinanceViewSet):
    serializer_class = RefundSerializer
    permission_map = {
        "list": ["finance.view"], "retrieve": ["finance.view"],
        "create": ["finance.refund"], "update": ["finance.edit"],
        "partial_update": ["finance.edit"], "destroy": ["finance.delete"],
        "approve": ["finance.approve"], "reject": ["finance.approve"],
        "process": ["finance.refund"],
    }
    filterset_fields = ["refund_type", "status", "resident"]
    search_fields = ["reason", "resident__full_name"]

    def get_queryset(self):
        return (
            Refund.objects.filter(hostel=self.request.hostel)
            .select_related("payment", "invoice", "resident")
        )

    def perform_create(self, serializer):
        refund = serializer.save(hostel=self.request.hostel, requested_by=self.request.user)
        self._audit(AuditEvent.Action.CREATE, "finance.refund", refund.id,
                    f"Refund requested: {refund.get_refund_type_display()} — {refund.amount}")

    def perform_destroy(self, instance):
        if instance.status == Refund.Status.PROCESSED:
            raise ValidationError({"detail": "Processed refunds cannot be deleted."})
        oid = instance.id
        instance.delete()
        self._audit(AuditEvent.Action.DELETE, "finance.refund", oid, "Refund request deleted")

    def _notify_requester(self, request, refund, title, body):
        if refund.requested_by_id and refund.requested_by_id != request.user.id:
            _notify(request.hostel, refund.requested_by, title, body,
                    url="/finance/refunds", created_by=request.user)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        refund = self.get_object()
        if refund.status != Refund.Status.REQUESTED:
            raise ValidationError({"detail": "Only requested refunds can be approved."})
        refund.status = Refund.Status.APPROVED
        refund.approved_by = request.user
        refund.save(update_fields=["status", "approved_by", "updated_at"])
        self._audit(AuditEvent.Action.UPDATE, "finance.refund", refund.id,
                    f"Refund approved: {refund.amount}")
        self._notify_requester(request, refund, "Refund approved",
                               f"Refund of {refund.amount} was approved.")
        return Response(self.get_serializer(refund).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        refund = self.get_object()
        if refund.status not in (Refund.Status.REQUESTED, Refund.Status.APPROVED):
            raise ValidationError({"detail": "Only open refunds can be rejected."})
        refund.status = Refund.Status.REJECTED
        refund.approved_by = request.user
        refund.save(update_fields=["status", "approved_by", "updated_at"])
        self._audit(AuditEvent.Action.UPDATE, "finance.refund", refund.id,
                    f"Refund rejected: {refund.amount}")
        self._notify_requester(request, refund, "Refund rejected",
                               f"Refund of {refund.amount} was rejected.")
        return Response(self.get_serializer(refund).data)

    @action(detail=True, methods=["post"])
    def process(self, request, pk=None):
        refund = self.get_object()
        if refund.status != Refund.Status.APPROVED:
            raise ValidationError({"detail": "Refunds must be approved before processing."})
        services.process_refund(refund, actor=request.user)
        self._audit(AuditEvent.Action.PAYMENT, "finance.refund", refund.id,
                    f"Refund processed: {refund.amount} via {refund.method}")
        self._notify_requester(request, refund, "Refund completed",
                               f"Refund of {refund.amount} was processed.")
        return Response(self.get_serializer(refund).data)


# --------------------------------------------------------------------------- #
# Budgets & transactions
# --------------------------------------------------------------------------- #
class BudgetViewSet(FinanceViewSet):
    serializer_class = BudgetSerializer
    permission_map = {
        "list": ["finance.view"], "retrieve": ["finance.view"],
        "create": ["finance.create"], "update": ["finance.edit"],
        "partial_update": ["finance.edit"], "destroy": ["finance.delete"],
    }
    filterset_fields = ["category", "period_year", "period_month"]

    def get_queryset(self):
        return Budget.objects.filter(hostel=self.request.hostel).select_related("category")

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "finance.budget", obj.id,
                    f"Budget created: {obj}")


class LedgerTransactionViewSet(ReadOnlyModelViewSet):
    """The immutable transaction feed (read-only by design)."""

    serializer_class = LedgerTransactionSerializer
    permission_classes = [IsHostelResolved, ActionPermissions, RequiresFeature("finance")]
    permission_map = {"list": ["finance.view"], "retrieve": ["finance.view"]}
    filterset_fields = ["direction", "method", "resident"]
    search_fields = ["category", "memo"]
    ordering_fields = ["occurred_at", "amount"]

    def get_queryset(self):
        return (
            LedgerTransaction.objects.filter(hostel=self.request.hostel)
            .select_related("resident")
        )


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
class FinanceDashboardViewSet(ViewSet):
    permission_classes = [IsHostelResolved, ActionPermissions, RequiresFeature("finance")]
    permission_map = {"summary": ["finance.view"]}

    @action(detail=False, methods=["get"])
    def summary(self, request):
        hostel = request.hostel
        today = timezone.localdate()
        month_start = today.replace(day=1)
        year_start = today.replace(month=1, day=1)
        services.refresh_overdue(hostel)

        txns = LedgerTransaction.objects.filter(hostel=hostel)
        money_in = txns.filter(direction=LedgerTransaction.Direction.IN)
        money_out = txns.filter(direction=LedgerTransaction.Direction.OUT)

        def _sum(qs):
            return qs.aggregate(s=Coalesce(Sum("amount"), Value(ZERO, output_field=_MONEY)))["s"]

        total_revenue = _sum(money_in)
        total_expenses = _sum(money_out.filter(category__startswith="expense:"))
        refund_total = _sum(money_out.filter(category__startswith="refund:"))
        total_out = _sum(money_out)

        open_invoices = Invoice.objects.filter(
            hostel=hostel,
            status__in=[Invoice.Status.PENDING, Invoice.Status.PARTIAL, Invoice.Status.OVERDUE],
        )
        outstanding = open_invoices.aggregate(
            s=Coalesce(Sum(F("total") - F("paid_amount"), output_field=_MONEY),
                       Value(ZERO, output_field=_MONEY))
        )["s"]

        invoice_aggregates = Invoice.objects.filter(hostel=hostel).exclude(
            status=Invoice.Status.CANCELLED
        ).aggregate(
            discounts=Coalesce(Sum("discount_total"), Value(ZERO, output_field=_MONEY)),
            scholarships=Coalesce(Sum("scholarship_total"), Value(ZERO, output_field=_MONEY)),
        )

        # 12-month in/out trend for the collection & expense charts.
        trend_start = (month_start - timedelta(days=365)).replace(day=1)
        trend_rows = (
            txns.filter(occurred_at__date__gte=trend_start)
            .annotate(month=TruncMonth("occurred_at"))
            .values("month", "direction")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )
        trend: dict = {}
        for row in trend_rows:
            key = row["month"].strftime("%Y-%m")
            entry = trend.setdefault(key, {"month": key, "in": "0.00", "out": "0.00"})
            entry["in" if row["direction"] == "in" else "out"] = _money(row["total"])

        method_rows = (
            money_in.values("method").annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )

        upcoming = (
            open_invoices.filter(due_date__gte=today, due_date__lte=today + timedelta(days=14))
            .select_related("resident")
            .order_by("due_date")[:10]
        )

        recent = txns.select_related("resident").order_by("-occurred_at")[:10]

        status_counts = dict(
            Invoice.objects.filter(hostel=hostel)
            .values_list("status")
            .annotate(c=Count("id"))
        )

        return Response({
            "totals": {
                "total_revenue": _money(total_revenue),
                "total_expenses": _money(total_expenses),
                "net_profit": _money(total_revenue - total_out),
                "outstanding_due": _money(outstanding),
                "total_collected": _money(_sum(money_in.filter(category="fee_collection"))),
                "todays_collection": _money(_sum(money_in.filter(occurred_at__date=today))),
                "monthly_collection": _money(_sum(money_in.filter(occurred_at__date__gte=month_start))),
                "annual_revenue": _money(_sum(money_in.filter(occurred_at__date__gte=year_start))),
                "refund_total": _money(refund_total),
                "discount_total": _money(invoice_aggregates["discounts"]),
                "scholarship_total": _money(invoice_aggregates["scholarships"]),
                "pending_payments": PaymentRecord.objects.filter(
                    hostel=hostel, status=PaymentRecord.Status.PENDING
                ).count(),
                "open_invoices": open_invoices.count(),
                "overdue_invoices": status_counts.get(Invoice.Status.OVERDUE, 0),
            },
            "invoice_status_counts": status_counts,
            "cash_flow": sorted(trend.values(), key=lambda r: r["month"]),
            "payment_methods": [
                {"method": r["method"], "total": _money(r["total"]), "count": r["count"]}
                for r in method_rows
            ],
            "upcoming_dues": [
                {
                    "id": str(inv.id), "number": inv.number,
                    "resident_name": inv.resident.full_name,
                    "due_date": inv.due_date, "balance": _money(inv.balance),
                    "status": inv.status,
                }
                for inv in upcoming
            ],
            "recent_transactions": LedgerTransactionSerializer(recent, many=True).data,
        })


# --------------------------------------------------------------------------- #
# Reports & exports
# --------------------------------------------------------------------------- #
class FinanceReportsViewSet(ViewSet):
    permission_classes = [IsHostelResolved, ActionPermissions, RequiresFeature("finance")]
    permission_map = {
        "collections": ["finance.view", "reports.view"],
        "profit_loss": ["finance.view", "reports.view"],
        "expense_breakdown": ["finance.view", "reports.view"],
        "dues": ["finance.view", "reports.view"],
        "export": ["finance.export"],
    }

    def _range(self, request):
        today = timezone.localdate()
        try:
            start = request.query_params.get("start") or str(today.replace(day=1))
            end = request.query_params.get("end") or str(today)
            return start, end
        except ValueError as exc:  # pragma: no cover — DRF validates most of this
            raise ValidationError({"detail": "Invalid date range."}) from exc

    @action(detail=False, methods=["get"])
    def collections(self, request):
        """Daily collection totals in a date range (defaults to this month)."""
        start, end = self._range(request)
        rows = (
            LedgerTransaction.objects.filter(
                hostel=request.hostel, direction=LedgerTransaction.Direction.IN,
                occurred_at__date__gte=start, occurred_at__date__lte=end,
            )
            .values("occurred_at__date")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("occurred_at__date")
        )
        return Response({
            "start": start, "end": end,
            "rows": [
                {"date": r["occurred_at__date"], "total": _money(r["total"]), "count": r["count"]}
                for r in rows
            ],
        })

    @action(detail=False, methods=["get"], url_path="profit-loss")
    def profit_loss(self, request):
        start, end = self._range(request)
        txns = LedgerTransaction.objects.filter(
            hostel=request.hostel,
            occurred_at__date__gte=start, occurred_at__date__lte=end,
        )
        rows = txns.values("direction", "category").annotate(total=Sum("amount")).order_by("category")
        income = [
            {"category": r["category"], "total": _money(r["total"])}
            for r in rows if r["direction"] == "in"
        ]
        expense = [
            {"category": r["category"], "total": _money(r["total"])}
            for r in rows if r["direction"] == "out"
        ]
        total_in = sum((Decimal(r["total"]) for r in rows if r["direction"] == "in"), ZERO)
        total_out = sum((Decimal(r["total"]) for r in rows if r["direction"] == "out"), ZERO)
        return Response({
            "start": start, "end": end,
            "income": income, "expenses": expense,
            "total_income": _money(total_in), "total_expenses": _money(total_out),
            "net": _money(total_in - total_out),
        })

    @action(detail=False, methods=["get"], url_path="expense-breakdown")
    def expense_breakdown(self, request):
        start, end = self._range(request)
        rows = (
            Expense.objects.filter(
                hostel=request.hostel, status=Expense.Status.PAID,
                expense_date__gte=start, expense_date__lte=end,
            )
            .values(name=Coalesce("category__name", Value("Uncategorized")))
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )
        return Response({
            "start": start, "end": end,
            "rows": [
                {"category": r["name"], "total": _money(r["total"]), "count": r["count"]}
                for r in rows
            ],
        })

    @action(detail=False, methods=["get"])
    def dues(self, request):
        services.refresh_overdue(request.hostel)
        rows = (
            Invoice.objects.filter(
                hostel=request.hostel,
                status__in=[Invoice.Status.PENDING, Invoice.Status.PARTIAL, Invoice.Status.OVERDUE],
            )
            .select_related("resident")
            .order_by("due_date")
        )
        return Response({
            "rows": [
                {
                    "id": str(inv.id), "number": inv.number,
                    "resident_name": inv.resident.full_name, "status": inv.status,
                    "issue_date": inv.issue_date, "due_date": inv.due_date,
                    "total": _money(inv.total), "paid_amount": _money(inv.paid_amount),
                    "balance": _money(inv.balance),
                }
                for inv in rows
            ],
        })

    _EXPORTS = {
        "transactions": (
            lambda hostel: LedgerTransaction.objects.filter(hostel=hostel).select_related("resident"),
            ["occurred_at", "direction", "category", "amount", "method", "memo"],
        ),
        "invoices": (
            lambda hostel: Invoice.objects.filter(hostel=hostel).select_related("resident"),
            ["number", "resident", "status", "issue_date", "due_date", "subtotal",
             "tax_total", "discount_total", "scholarship_total", "total", "paid_amount"],
        ),
        "payments": (
            lambda hostel: PaymentRecord.objects.filter(hostel=hostel).select_related("resident"),
            ["receipt_number", "resident", "amount", "method", "status", "reference", "received_at"],
        ),
        "expenses": (
            lambda hostel: Expense.objects.filter(hostel=hostel).select_related("category"),
            ["expense_date", "title", "category", "vendor_name", "amount", "tax_amount",
             "payment_method", "status", "reference"],
        ),
        "income": (
            lambda hostel: Income.objects.filter(hostel=hostel),
            ["income_date", "title", "source", "amount", "payment_method", "reference"],
        ),
    }

    @action(detail=False, methods=["get"])
    def export(self, request):
        """CSV export of a finance dataset (?type=transactions|invoices|payments|expenses|income)."""
        kind = request.query_params.get("type", "transactions")
        if kind not in self._EXPORTS:
            raise ValidationError({"type": f"Unknown export type. One of: {', '.join(self._EXPORTS)}"})
        queryset_fn, columns = self._EXPORTS[kind]

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="finance-{kind}.csv"'
        writer = csv.writer(response)
        writer.writerow(columns)
        for obj in queryset_fn(request.hostel).iterator():
            row = []
            for col in columns:
                value = getattr(obj, col, "")
                if col in ("resident", "category"):
                    value = getattr(value, "full_name", None) or getattr(value, "name", "") if value else ""
                row.append(str(value) if value is not None else "")
            writer.writerow(row)

        record_event(
            request, action=AuditEvent.Action.EXPORT, actor=request.user,
            hostel=request.hostel, entity_type=f"finance.{kind}", entity_id="",
            message=f"Finance export: {kind}",
        )
        return response
