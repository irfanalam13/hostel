"""Accounting & Bookkeeping API.

Workspace-scoped (``request.hostel``), RBAC-gated (``accounting.*``) and
plan-gated behind the ``accounting`` feature. The double-entry engine and
statement builders live in ``services`` / ``statements``; views validate,
authorize and audit.
"""
import csv
from datetime import date

from django.db.models import Count
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
from apps.subscriptions.gates import RequiresFeature

from . import services, statements
from .models import (
    Account,
    AccountingPeriod,
    BankAccount,
    BankStatementLine,
    Branch,
    Budget,
    CostCenter,
    Currency,
    ExchangeRate,
    FiscalYear,
    FixedAsset,
    JournalEntry,
    LedgerEntry,
    TaxCode,
)
from .serializers import (
    AccountingPeriodSerializer,
    AccountSerializer,
    BankAccountSerializer,
    BankStatementLineSerializer,
    BranchSerializer,
    BudgetSerializer,
    CostCenterSerializer,
    CurrencySerializer,
    DepreciationEntrySerializer,
    ExchangeRateSerializer,
    FiscalYearSerializer,
    FixedAssetSerializer,
    JournalCreateSerializer,
    JournalEntrySerializer,
    LedgerEntrySerializer,
    TaxCodeSerializer,
)


def _parse_date(value, default):
    if not value:
        return default
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise ValidationError({"detail": f"Invalid date: {value}"}) from exc


class AccountingViewSet(ModelViewSet):
    permission_classes = [IsHostelResolved, ActionPermissions, RequiresFeature("accounting")]

    def _audit(self, action_, entity_type, obj_id, message, meta=None):
        record_event(
            self.request, action=action_, actor=self.request.user,
            hostel=self.request.hostel, entity_type=entity_type,
            entity_id=obj_id, message=message, meta=meta,
        )


# --------------------------------------------------------------------------- #
# Dimensions
# --------------------------------------------------------------------------- #
class BranchViewSet(AccountingViewSet):
    serializer_class = BranchSerializer
    permission_map = {
        "list": ["accounting.view"], "retrieve": ["accounting.view"],
        "create": ["accounting.create"], "update": ["accounting.edit"],
        "partial_update": ["accounting.edit"], "destroy": ["accounting.delete"],
    }
    search_fields = ["name", "code"]

    def get_queryset(self):
        return Branch.objects.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "accounting.branch", obj.id, f"Branch created: {obj.name}")


class CostCenterViewSet(AccountingViewSet):
    serializer_class = CostCenterSerializer
    permission_map = {
        "list": ["accounting.view"], "retrieve": ["accounting.view"],
        "create": ["accounting.create"], "update": ["accounting.edit"],
        "partial_update": ["accounting.edit"], "destroy": ["accounting.delete"],
    }
    search_fields = ["name", "code"]

    def get_queryset(self):
        return CostCenter.objects.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "accounting.costcenter", obj.id,
                    f"Cost center created: {obj.name}")


class CurrencyViewSet(AccountingViewSet):
    serializer_class = CurrencySerializer
    permission_map = {
        "list": ["accounting.view"], "retrieve": ["accounting.view"],
        "create": ["accounting.create"], "update": ["accounting.edit"],
        "partial_update": ["accounting.edit"], "destroy": ["accounting.delete"],
    }

    def get_queryset(self):
        return Currency.objects.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        # Only one base currency per workspace.
        if obj.is_base:
            Currency.objects.filter(hostel=self.request.hostel).exclude(id=obj.id).update(is_base=False)


class ExchangeRateViewSet(AccountingViewSet):
    serializer_class = ExchangeRateSerializer
    permission_map = {
        "list": ["accounting.view"], "retrieve": ["accounting.view"],
        "create": ["accounting.create"], "update": ["accounting.edit"],
        "partial_update": ["accounting.edit"], "destroy": ["accounting.delete"],
    }
    filterset_fields = ["currency"]

    def get_queryset(self):
        return ExchangeRate.objects.filter(hostel=self.request.hostel).select_related("currency")

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel)


# --------------------------------------------------------------------------- #
# Fiscal calendar
# --------------------------------------------------------------------------- #
class FiscalYearViewSet(AccountingViewSet):
    serializer_class = FiscalYearSerializer
    permission_map = {
        "list": ["accounting.view"], "retrieve": ["accounting.view"],
        "create": ["accounting.create"], "update": ["accounting.edit"],
        "partial_update": ["accounting.edit"], "destroy": ["accounting.delete"],
        "generate_periods": ["accounting.edit"], "close": ["accounting.close"],
        "post_opening_balances": ["accounting.post"],
    }

    def get_queryset(self):
        return FiscalYear.objects.filter(hostel=self.request.hostel).prefetch_related("periods")

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "accounting.fiscalyear", obj.id,
                    f"Fiscal year created: {obj.name}")

    def perform_destroy(self, instance):
        if instance.journals.exists():
            raise ValidationError({"detail": "Fiscal years with journals cannot be deleted."})
        instance.delete()

    @action(detail=True, methods=["post"], url_path="generate-periods")
    def generate_periods(self, request, pk=None):
        """Create monthly accounting periods spanning the fiscal year."""
        fy = self.get_object()
        if fy.periods.exists():
            raise ValidationError({"detail": "Periods already exist for this fiscal year."})
        from datetime import timedelta

        created = []
        cursor = fy.start_date.replace(day=1)
        while cursor <= fy.end_date:
            if cursor.month == 12:
                nxt = cursor.replace(year=cursor.year + 1, month=1)
            else:
                nxt = cursor.replace(month=cursor.month + 1)
            # Last calendar day of the month, clamped to the fiscal-year end.
            period_end = min(nxt - timedelta(days=1), fy.end_date)
            created.append(AccountingPeriod.objects.create(
                hostel=request.hostel, fiscal_year=fy, name=cursor.strftime("%Y-%m"),
                start_date=max(cursor, fy.start_date), end_date=period_end,
            ))
            cursor = nxt
        self._audit(AuditEvent.Action.CREATE, "accounting.fiscalyear", fy.id,
                    f"Generated {len(created)} periods for {fy.name}")
        # Re-fetch so the prefetched (previously empty) periods reflect the new rows.
        fresh = FiscalYear.objects.prefetch_related("periods").get(pk=fy.pk)
        return Response(FiscalYearSerializer(fresh, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"], url_path="post-opening-balances")
    def post_opening_balances(self, request, pk=None):
        fy = self.get_object()
        journal = services.post_opening_balances(hostel=request.hostel, actor=request.user, fiscal_year=fy)
        self._audit(AuditEvent.Action.CREATE, "accounting.journalentry", journal.id,
                    f"Opening balances posted: {journal.number}")
        return Response(JournalEntrySerializer(journal, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        fy = self.get_object()
        services.close_fiscal_year(hostel=request.hostel, actor=request.user, fiscal_year=fy)
        self._audit(AuditEvent.Action.UPDATE, "accounting.fiscalyear", fy.id,
                    f"Fiscal year closed: {fy.name}")
        return Response(FiscalYearSerializer(fy, context=self.get_serializer_context()).data)


class AccountingPeriodViewSet(AccountingViewSet):
    serializer_class = AccountingPeriodSerializer
    permission_map = {
        "list": ["accounting.view"], "retrieve": ["accounting.view"],
        "close": ["accounting.close"], "reopen": ["accounting.close"],
    }
    http_method_names = ["get", "post", "head", "options"]
    filterset_fields = ["fiscal_year", "is_closed"]

    def get_queryset(self):
        return AccountingPeriod.objects.filter(hostel=self.request.hostel).select_related("fiscal_year")

    @action(detail=True, methods=["post"])
    def close(self, request, pk=None):
        period = self.get_object()
        services.close_period(period)
        self._audit(AuditEvent.Action.UPDATE, "accounting.period", period.id,
                    f"Period closed: {period.name}")
        return Response(self.get_serializer(period).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        period = self.get_object()
        services.reopen_period(period)
        self._audit(AuditEvent.Action.UPDATE, "accounting.period", period.id,
                    f"Period reopened: {period.name}")
        return Response(self.get_serializer(period).data)


# --------------------------------------------------------------------------- #
# Chart of accounts
# --------------------------------------------------------------------------- #
class AccountViewSet(AccountingViewSet):
    serializer_class = AccountSerializer
    permission_map = {
        "list": ["accounting.view"], "retrieve": ["accounting.view"],
        "create": ["accounting.create"], "update": ["accounting.edit"],
        "partial_update": ["accounting.edit"], "destroy": ["accounting.delete"],
        "seed_defaults": ["accounting.create"], "ledger": ["accounting.view"],
    }
    filterset_fields = ["type", "is_group", "is_active", "parent", "branch"]
    search_fields = ["code", "name"]
    ordering_fields = ["code", "name"]

    def get_queryset(self):
        services.ensure_chart_of_accounts(self.request.hostel)
        return Account.objects.filter(hostel=self.request.hostel).select_related("parent")

    def perform_create(self, serializer):
        code = serializer.validated_data.get("code")
        if not code:
            # Auto-code: next in the type's range.
            serializer.validated_data["code"] = self._auto_code(serializer.validated_data["type"])
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "accounting.account", obj.id,
                    f"Account created: {obj.code} {obj.name}")

    def _auto_code(self, account_type) -> str:
        prefix = {"asset": "1", "liability": "2", "equity": "3", "income": "4", "expense": "5"}.get(
            str(account_type), "9"
        )
        existing = (
            Account.objects.filter(hostel=self.request.hostel, code__startswith=prefix)
            .values_list("code", flat=True)
        )
        nums = [int(c) for c in existing if c.isdigit()]
        return str((max(nums) + 10)) if nums else f"{prefix}000"

    def perform_update(self, serializer):
        if serializer.instance.is_system and "type" in serializer.validated_data:
            raise ValidationError({"detail": "The type of a system account cannot be changed."})
        obj = serializer.save()
        self._audit(AuditEvent.Action.UPDATE, "accounting.account", obj.id,
                    f"Account updated: {obj.code}")

    def perform_destroy(self, instance):
        if instance.is_system:
            raise ValidationError({"detail": "System accounts cannot be deleted (deactivate instead)."})
        if instance.ledger_entries.exists():
            raise ValidationError({"detail": "Accounts with ledger history cannot be deleted."})
        code, oid = instance.code, instance.id
        instance.delete()
        self._audit(AuditEvent.Action.DELETE, "accounting.account", oid, f"Account deleted: {code}")

    @action(detail=False, methods=["post"], url_path="seed-defaults")
    def seed_defaults(self, request):
        services.ensure_chart_of_accounts(request.hostel)
        return Response({"detail": "Chart of accounts is ready."})

    @action(detail=True, methods=["get"])
    def ledger(self, request, pk=None):
        """General ledger (running balance) for one account."""
        account = self.get_object()
        start = _parse_date(request.query_params.get("start"), None)
        end = _parse_date(request.query_params.get("end"), None)
        return Response(statements.general_ledger(request.hostel, account, start=start, end=end))


class TaxCodeViewSet(AccountingViewSet):
    serializer_class = TaxCodeSerializer
    permission_map = {
        "list": ["accounting.view"], "retrieve": ["accounting.view"],
        "create": ["accounting.create"], "update": ["accounting.edit"],
        "partial_update": ["accounting.edit"], "destroy": ["accounting.delete"],
    }
    search_fields = ["name"]

    def get_queryset(self):
        return TaxCode.objects.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "accounting.taxcode", obj.id,
                    f"Tax code created: {obj.name}")


# --------------------------------------------------------------------------- #
# Journals
# --------------------------------------------------------------------------- #
class JournalEntryViewSet(AccountingViewSet):
    permission_map = {
        "list": ["accounting.view"], "retrieve": ["accounting.view"],
        "create": ["accounting.create"], "update": ["accounting.edit"],
        "partial_update": ["accounting.edit"], "destroy": ["accounting.delete"],
        "submit": ["accounting.edit"], "approve": ["accounting.approve"],
        "post": ["accounting.post"], "reverse": ["accounting.post"],
    }
    filterset_fields = ["status", "journal_type", "period", "branch"]
    search_fields = ["number", "reference", "description"]
    ordering_fields = ["date", "number", "created_at"]

    def get_serializer_class(self):
        return JournalCreateSerializer if self.action == "create" else JournalEntrySerializer

    def get_queryset(self):
        return (
            JournalEntry.objects.filter(hostel=self.request.hostel)
            .select_related("period", "branch")
            .prefetch_related("lines__account")
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        lines = data.pop("lines")
        do_post = data.pop("post", False)
        journal = services.create_journal(
            hostel=request.hostel, actor=request.user, lines=lines,
            status=JournalEntry.Status.POSTED if do_post else JournalEntry.Status.DRAFT,
            **data,
        )
        self._audit(
            AuditEvent.Action.CREATE, "accounting.journalentry", journal.id,
            f"Journal {'posted' if do_post else 'created'}: {journal.number}",
            meta={"total": str(journal.total_debit)},
        )
        out = JournalEntrySerializer(journal, context=self.get_serializer_context())
        return Response(out.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        journal = self.get_object()
        if journal.status in (JournalEntry.Status.POSTED, JournalEntry.Status.REVERSED):
            raise ValidationError({"detail": "Posted journals are immutable — reverse instead."})
        partial = kwargs.pop("partial", False)
        serializer = JournalCreateSerializer(
            data=request.data, partial=partial, context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        lines = data.pop("lines", None)
        data.pop("post", None)
        for field in ("date", "posting_date", "reference", "description",
                      "journal_type", "branch", "currency", "exchange_rate", "notes"):
            if field in data:
                setattr(journal, field, data[field])
        journal.save()
        if lines is not None:
            services.replace_lines(journal, lines)
        self._audit(AuditEvent.Action.UPDATE, "accounting.journalentry", journal.id,
                    f"Journal updated: {journal.number}")
        return Response(JournalEntrySerializer(journal, context=self.get_serializer_context()).data)

    def perform_destroy(self, instance):
        if instance.status in (JournalEntry.Status.POSTED, JournalEntry.Status.REVERSED):
            raise ValidationError({"detail": "Posted journals cannot be deleted — reverse instead."})
        number, oid = instance.number, instance.id
        instance.delete()
        self._audit(AuditEvent.Action.DELETE, "accounting.journalentry", oid,
                    f"Journal deleted: {number}")

    def _reserialize(self, journal):
        return Response(JournalEntrySerializer(journal, context=self.get_serializer_context()).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        journal = services.submit_journal(self.get_object(), actor=request.user)
        self._audit(AuditEvent.Action.UPDATE, "accounting.journalentry", journal.id,
                    f"Journal submitted: {journal.number}")
        return self._reserialize(journal)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        journal = services.approve_journal(self.get_object(), actor=request.user)
        self._audit(AuditEvent.Action.UPDATE, "accounting.journalentry", journal.id,
                    f"Journal approved: {journal.number}")
        return self._reserialize(journal)

    @action(detail=True, methods=["post"])
    def post(self, request, pk=None):
        journal = services.post_journal(self.get_object(), actor=request.user)
        self._audit(AuditEvent.Action.UPDATE, "accounting.journalentry", journal.id,
                    f"Journal posted: {journal.number}", meta={"total": str(journal.total_debit)})
        return self._reserialize(journal)

    @action(detail=True, methods=["post"])
    def reverse(self, request, pk=None):
        reversal = services.reverse_journal(
            self.get_object(), actor=request.user,
            date=_parse_date(request.data.get("date"), timezone.localdate()),
        )
        self._audit(AuditEvent.Action.CREATE, "accounting.journalentry", reversal.id,
                    f"Journal reversed: {reversal.reference} → {reversal.number}")
        return self._reserialize(reversal)


class LedgerEntryViewSet(ReadOnlyModelViewSet):
    """Read-only general ledger feed (immutable by design)."""

    serializer_class = LedgerEntrySerializer
    permission_classes = [IsHostelResolved, ActionPermissions, RequiresFeature("accounting")]
    permission_map = {"list": ["accounting.view"], "retrieve": ["accounting.view"]}
    filterset_fields = ["account", "journal", "branch", "cost_center"]
    search_fields = ["description"]
    ordering_fields = ["date"]

    def get_queryset(self):
        return (
            LedgerEntry.objects.filter(hostel=self.request.hostel)
            .select_related("account", "journal")
        )


# --------------------------------------------------------------------------- #
# Budgets
# --------------------------------------------------------------------------- #
class BudgetViewSet(AccountingViewSet):
    serializer_class = BudgetSerializer
    permission_map = {
        "list": ["accounting.view"], "retrieve": ["accounting.view"],
        "create": ["accounting.create"], "update": ["accounting.edit"],
        "partial_update": ["accounting.edit"], "destroy": ["accounting.delete"],
        "approve": ["accounting.approve"], "variance": ["accounting.view"],
    }
    filterset_fields = ["fiscal_year", "branch", "cost_center", "is_approved"]

    def get_queryset(self):
        return (
            Budget.objects.filter(hostel=self.request.hostel)
            .select_related("fiscal_year").prefetch_related("lines__account")
        )

    def perform_create(self, serializer):
        obj = serializer.save()
        self._audit(AuditEvent.Action.CREATE, "accounting.budget", obj.id, f"Budget created: {obj.name}")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        budget = self.get_object()
        budget.is_approved = True
        budget.save(update_fields=["is_approved", "updated_at"])
        self._audit(AuditEvent.Action.UPDATE, "accounting.budget", budget.id,
                    f"Budget approved: {budget.name}")
        return Response(self.get_serializer(budget).data)

    @action(detail=True, methods=["get"])
    def variance(self, request, pk=None):
        """Budget-vs-actual variance analysis over the budget's fiscal year."""
        budget = self.get_object()
        return Response(services.budget_variance(hostel=request.hostel, budget=budget))


# --------------------------------------------------------------------------- #
# Fixed assets
# --------------------------------------------------------------------------- #
class FixedAssetViewSet(AccountingViewSet):
    serializer_class = FixedAssetSerializer
    permission_map = {
        "list": ["accounting.view"], "retrieve": ["accounting.view"],
        "create": ["accounting.create"], "update": ["accounting.edit"],
        "partial_update": ["accounting.edit"], "destroy": ["accounting.delete"],
        "depreciate": ["accounting.post"], "dispose": ["accounting.edit"],
        "depreciations": ["accounting.view"],
    }
    filterset_fields = ["status", "category", "branch"]
    search_fields = ["name", "code", "category"]

    def get_queryset(self):
        return FixedAsset.objects.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        obj = serializer.save(hostel=self.request.hostel)
        self._audit(AuditEvent.Action.CREATE, "accounting.fixedasset", obj.id,
                    f"Fixed asset added: {obj.name}")

    @action(detail=True, methods=["post"])
    def depreciate(self, request, pk=None):
        asset = self.get_object()
        journal = services.run_depreciation(
            hostel=request.hostel, actor=request.user, asset=asset,
            on_date=_parse_date(request.data.get("date"), timezone.localdate()),
        )
        self._audit(AuditEvent.Action.CREATE, "accounting.fixedasset", asset.id,
                    f"Depreciation posted for {asset.name}: {journal.number}")
        return Response(self.get_serializer(asset).data)

    @action(detail=True, methods=["post"])
    def dispose(self, request, pk=None):
        asset = self.get_object()
        asset.status = FixedAsset.Status.DISPOSED
        asset.disposed_date = _parse_date(request.data.get("date"), timezone.localdate())
        asset.save(update_fields=["status", "disposed_date", "updated_at"])
        self._audit(AuditEvent.Action.UPDATE, "accounting.fixedasset", asset.id,
                    f"Asset disposed: {asset.name}")
        return Response(self.get_serializer(asset).data)

    @action(detail=True, methods=["get"])
    def depreciations(self, request, pk=None):
        asset = self.get_object()
        rows = asset.depreciations.all()
        return Response(DepreciationEntrySerializer(rows, many=True).data)


# --------------------------------------------------------------------------- #
# Bank reconciliation
# --------------------------------------------------------------------------- #
class BankAccountViewSet(AccountingViewSet):
    serializer_class = BankAccountSerializer
    permission_map = {
        "list": ["accounting.view"], "retrieve": ["accounting.view"],
        "create": ["accounting.create"], "update": ["accounting.edit"],
        "partial_update": ["accounting.edit"], "destroy": ["accounting.delete"],
        "auto_match": ["accounting.reconcile"],
    }

    def get_queryset(self):
        return BankAccount.objects.filter(hostel=self.request.hostel).select_related("account")

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel)

    @action(detail=True, methods=["post"], url_path="auto-match")
    def auto_match(self, request, pk=None):
        """Auto-reconcile statement lines against ledger movements by amount+date."""
        bank_account = self.get_object()
        try:
            tolerance = max(0, min(30, int(request.data.get("tolerance_days", 4))))
        except (TypeError, ValueError):
            tolerance = 4
        matched = services.auto_match_bank_account(
            hostel=request.hostel, bank_account=bank_account, tolerance_days=tolerance
        )
        self._audit(AuditEvent.Action.UPDATE, "accounting.bankaccount", bank_account.id,
                    f"Auto-matched {matched} statement line(s) for {bank_account.name}")
        return Response({"matched": matched})


class BankStatementLineViewSet(AccountingViewSet):
    serializer_class = BankStatementLineSerializer
    permission_map = {
        "list": ["accounting.view"], "retrieve": ["accounting.view"],
        "create": ["accounting.create"], "update": ["accounting.edit"],
        "partial_update": ["accounting.edit"], "destroy": ["accounting.delete"],
        "reconcile": ["accounting.reconcile"], "unreconcile": ["accounting.reconcile"],
        "import_csv": ["accounting.create"],
    }
    filterset_fields = ["bank_account", "is_reconciled"]

    def get_queryset(self):
        return BankStatementLine.objects.filter(hostel=self.request.hostel)

    def perform_create(self, serializer):
        serializer.save(hostel=self.request.hostel)

    @action(detail=False, methods=["post"], url_path="import-csv")
    def import_csv(self, request):
        """Bulk-import statement lines from CSV text (``content``) or an uploaded
        file (``file``) for a given ``bank_account``."""
        bank_id = request.data.get("bank_account")
        bank_account = BankAccount.objects.filter(hostel=request.hostel, id=bank_id).first()
        if bank_account is None:
            raise ValidationError({"bank_account": "Unknown bank account."})
        upload = request.FILES.get("file")
        if upload is not None:
            csv_text = upload.read().decode("utf-8-sig", errors="replace")
        else:
            csv_text = request.data.get("content", "")
        if not str(csv_text).strip():
            raise ValidationError({"detail": "Provide CSV content or a file to import."})
        created = services.import_bank_statement(
            hostel=request.hostel, bank_account=bank_account, csv_text=csv_text
        )
        self._audit(AuditEvent.Action.CREATE, "accounting.bankaccount", bank_account.id,
                    f"Imported {len(created)} statement line(s) for {bank_account.name}")
        return Response({"imported": len(created)}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def reconcile(self, request, pk=None):
        line = self.get_object()
        line.is_reconciled = True
        line.reconciled_at = timezone.now()
        matched = request.data.get("matched_line")
        if matched:
            from .models import JournalLine

            jl = JournalLine.objects.filter(hostel=request.hostel, id=matched).first()
            if jl is None:
                raise ValidationError({"matched_line": "Unknown journal line."})
            line.matched_line = jl
        line.save(update_fields=["is_reconciled", "reconciled_at", "matched_line", "updated_at"])
        self._audit(AuditEvent.Action.UPDATE, "accounting.bankstatementline", line.id,
                    "Bank line reconciled")
        return Response(self.get_serializer(line).data)

    @action(detail=True, methods=["post"])
    def unreconcile(self, request, pk=None):
        line = self.get_object()
        line.is_reconciled = False
        line.reconciled_at = None
        line.matched_line = None
        line.save(update_fields=["is_reconciled", "reconciled_at", "matched_line", "updated_at"])
        return Response(self.get_serializer(line).data)


# --------------------------------------------------------------------------- #
# Statements, reports & dashboard
# --------------------------------------------------------------------------- #
class AccountingReportsViewSet(ViewSet):
    permission_classes = [IsHostelResolved, ActionPermissions, RequiresFeature("accounting")]
    permission_map = {
        "trial_balance": ["accounting.view"],
        "profit_loss": ["accounting.view"],
        "balance_sheet": ["accounting.view"],
        "cash_flow": ["accounting.view"],
        "statement_of_equity": ["accounting.view"],
        "journal_register": ["accounting.view"],
        "trends": ["accounting.view"],
        "export": ["accounting.export"],
    }

    def _range(self, request):
        today = timezone.localdate()
        start = _parse_date(request.query_params.get("start"), today.replace(month=1, day=1))
        end = _parse_date(request.query_params.get("end"), today)
        return start, end

    def _branch(self, request):
        bid = request.query_params.get("branch")
        return Branch.objects.filter(hostel=request.hostel, id=bid).first() if bid else None

    @action(detail=False, methods=["get"], url_path="trial-balance")
    def trial_balance(self, request):
        _, end = self._range(request)
        return Response(statements.trial_balance(request.hostel, as_of=end, branch=self._branch(request)))

    @action(detail=False, methods=["get"], url_path="profit-loss")
    def profit_loss(self, request):
        start, end = self._range(request)
        return Response(statements.profit_and_loss(
            request.hostel, start=start, end=end, branch=self._branch(request)))

    @action(detail=False, methods=["get"], url_path="balance-sheet")
    def balance_sheet(self, request):
        _, end = self._range(request)
        return Response(statements.balance_sheet(request.hostel, as_of=end, branch=self._branch(request)))

    @action(detail=False, methods=["get"], url_path="cash-flow")
    def cash_flow(self, request):
        start, end = self._range(request)
        return Response(statements.cash_flow(
            request.hostel, start=start, end=end, branch=self._branch(request)))

    @action(detail=False, methods=["get"], url_path="statement-of-equity")
    def statement_of_equity(self, request):
        start, end = self._range(request)
        return Response(statements.statement_of_equity(
            request.hostel, start=start, end=end, branch=self._branch(request)))

    @action(detail=False, methods=["get"])
    def trends(self, request):
        _, end = self._range(request)
        try:
            months = max(1, min(24, int(request.query_params.get("months", 12))))
        except (TypeError, ValueError):
            months = 12
        return Response(statements.monthly_trends(
            request.hostel, end=end, months=months, branch=self._branch(request)))

    @action(detail=False, methods=["get"], url_path="journal-register")
    def journal_register(self, request):
        start, end = self._range(request)
        rows = (
            JournalEntry.objects.filter(
                hostel=request.hostel, status=JournalEntry.Status.POSTED,
                date__gte=start, date__lte=end,
            )
            .order_by("date", "number")
            .values("id", "number", "date", "description", "total_debit", "journal_type")
        )
        return Response({
            "start": start, "end": end,
            "rows": [
                {
                    "id": str(r["id"]), "number": r["number"], "date": r["date"],
                    "description": r["description"], "amount": str(r["total_debit"]),
                    "type": r["journal_type"],
                }
                for r in rows
            ],
        })

    @action(detail=False, methods=["get"])
    def export(self, request):
        """CSV export of the trial balance or the general ledger."""
        kind = request.query_params.get("type", "trial-balance")
        _, end = self._range(request)
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="accounting-{kind}.csv"'
        writer = csv.writer(response)
        start, end = self._range(request)
        if kind == "trial-balance":
            tb = statements.trial_balance(request.hostel, as_of=end)
            writer.writerow(["Code", "Account", "Type", "Debit", "Credit"])
            for row in tb["rows"]:
                writer.writerow([row["code"], row["name"], row["type"], row["debit"], row["credit"]])
            writer.writerow(["", "TOTAL", "", tb["total_debit"], tb["total_credit"]])
        elif kind == "general-ledger":
            writer.writerow(["Date", "Journal", "Account", "Description", "Debit", "Credit"])
            for entry in LedgerEntry.objects.filter(
                hostel=request.hostel, date__gte=start, date__lte=end
            ).select_related("account", "journal").order_by("date"):
                writer.writerow([
                    entry.date, entry.journal.number, entry.account.code,
                    entry.description, entry.debit, entry.credit,
                ])
        elif kind == "profit-loss":
            pl = statements.profit_and_loss(request.hostel, start=start, end=end)
            writer.writerow(["Section", "Code", "Account", "Amount"])
            for row in pl["income"]:
                writer.writerow(["Income", row["code"], row["name"], row["amount"]])
            for row in pl["expenses"]:
                writer.writerow(["Expense", row["code"], row["name"], row["amount"]])
            writer.writerow(["Total Income", "", "", pl["total_income"]])
            writer.writerow(["Total Expenses", "", "", pl["total_expenses"]])
            writer.writerow(["Net Profit", "", "", pl["net_profit"]])
        elif kind == "balance-sheet":
            bs = statements.balance_sheet(request.hostel, as_of=end)
            writer.writerow(["Section", "Code", "Account", "Amount"])
            for section, rows in (
                ("Asset", bs["assets"]), ("Liability", bs["liabilities"]), ("Equity", bs["equity"])
            ):
                for row in rows:
                    writer.writerow([section, row["code"], row["name"], row["amount"]])
            writer.writerow(["Total Assets", "", "", bs["total_assets"]])
            writer.writerow(["Total Liabilities", "", "", bs["total_liabilities"]])
            writer.writerow(["Total Equity", "", "", bs["total_equity"]])
        elif kind == "journal-register":
            writer.writerow(["Number", "Date", "Type", "Description", "Amount"])
            for j in JournalEntry.objects.filter(
                hostel=request.hostel, status=JournalEntry.Status.POSTED,
                date__gte=start, date__lte=end,
            ).order_by("date", "number"):
                writer.writerow([j.number, j.date, j.journal_type, j.description, j.total_debit])
        else:
            raise ValidationError({
                "type": "Unknown export type (trial-balance | general-ledger | "
                        "profit-loss | balance-sheet | journal-register)."
            })
        record_event(
            request, action=AuditEvent.Action.EXPORT, actor=request.user,
            hostel=request.hostel, entity_type=f"accounting.{kind}", entity_id="",
            message=f"Accounting export: {kind}",
        )
        return response


class AccountingDashboardViewSet(ViewSet):
    permission_classes = [IsHostelResolved, ActionPermissions, RequiresFeature("accounting")]
    permission_map = {"summary": ["accounting.view"]}

    @action(detail=False, methods=["get"])
    def summary(self, request):
        services.ensure_chart_of_accounts(request.hostel)
        today = timezone.localdate()
        start = today.replace(month=1, day=1)
        snapshot = statements.dashboard_snapshot(
            request.hostel, as_of=today, start=start, end=today
        )
        snapshot["pending_approvals"] = JournalEntry.objects.filter(
            hostel=request.hostel,
            status__in=[JournalEntry.Status.SUBMITTED, JournalEntry.Status.APPROVED],
        ).count()
        snapshot["draft_journals"] = JournalEntry.objects.filter(
            hostel=request.hostel, status=JournalEntry.Status.DRAFT
        ).count()
        snapshot["account_counts"] = dict(
            Account.objects.filter(hostel=request.hostel, is_group=False)
            .values_list("type").annotate(c=Count("id"))
        )
        snapshot["recent_journals"] = JournalEntrySerializer(
            JournalEntry.objects.filter(hostel=request.hostel)
            .prefetch_related("lines__account").order_by("-created_at")[:8],
            many=True, context={"request": request},
        ).data
        return Response(snapshot)
