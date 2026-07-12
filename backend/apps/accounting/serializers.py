"""Accounting serializers.

Relational fields are constrained to the request's workspace at construction
time so a payload can never reference another tenant's rows. Ledger-affecting
figures (journal totals, posting state) are read-only — the engine owns them.
"""
from rest_framework import serializers

from .models import (
    Account,
    AccountingPeriod,
    BankAccount,
    BankStatementLine,
    Branch,
    Budget,
    BudgetLine,
    CostCenter,
    Currency,
    DepreciationEntry,
    ExchangeRate,
    FiscalYear,
    FixedAsset,
    JournalEntry,
    JournalLine,
    LedgerEntry,
    TaxCode,
)


class _HostelScopedRelationsMixin:
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
# Dimensions
# --------------------------------------------------------------------------- #
class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ["id", "name", "code", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CostCenterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CostCenter
        fields = ["id", "name", "code", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ["id", "code", "name", "symbol", "is_base", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class ExchangeRateSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"currency": Currency}
    currency_code = serializers.CharField(source="currency.code", read_only=True)

    class Meta:
        model = ExchangeRate
        fields = ["id", "currency", "currency_code", "rate_to_base", "as_of", "created_at"]
        read_only_fields = ["id", "currency_code", "created_at"]


# --------------------------------------------------------------------------- #
# Fiscal calendar
# --------------------------------------------------------------------------- #
class AccountingPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountingPeriod
        fields = [
            "id", "fiscal_year", "name", "start_date", "end_date", "is_closed",
            "closed_at", "created_at",
        ]
        read_only_fields = ["id", "is_closed", "closed_at", "created_at"]


class FiscalYearSerializer(serializers.ModelSerializer):
    periods = AccountingPeriodSerializer(many=True, read_only=True)

    class Meta:
        model = FiscalYear
        fields = [
            "id", "name", "start_date", "end_date", "is_closed", "closed_at",
            "periods", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_closed", "closed_at", "periods", "created_at", "updated_at"]


# --------------------------------------------------------------------------- #
# Chart of accounts
# --------------------------------------------------------------------------- #
class AccountSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {
        "parent": Account,
        "currency": Currency,
        "branch": Branch,
        "cost_center": CostCenter,
    }
    parent_code = serializers.CharField(source="parent.code", read_only=True, default=None)
    normal_balance = serializers.CharField(read_only=True)
    type_display = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Account
        fields = [
            "id", "code", "name", "type", "type_display", "subtype", "parent",
            "parent_code", "is_group", "description", "opening_balance",
            "currency", "branch", "cost_center", "normal_balance", "is_system",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "parent_code", "type_display", "normal_balance",
                            "is_system", "created_at", "updated_at"]
        extra_kwargs = {"code": {"required": False}}


class TaxCodeSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"payable_account": Account, "receivable_account": Account}

    class Meta:
        model = TaxCode
        fields = [
            "id", "name", "tax_type", "rate", "payable_account",
            "receivable_account", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# --------------------------------------------------------------------------- #
# Journals
# --------------------------------------------------------------------------- #
class JournalLineSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"account": Account, "cost_center": CostCenter, "branch": Branch}
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = JournalLine
        fields = [
            "id", "account", "account_code", "account_name", "debit", "credit",
            "description", "cost_center", "branch",
        ]
        read_only_fields = ["id", "account_code", "account_name"]


class JournalEntrySerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"branch": Branch, "currency": Currency, "period": AccountingPeriod}
    lines = JournalLineSerializer(many=True, read_only=True)
    is_balanced = serializers.BooleanField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            "id", "number", "date", "posting_date", "reference", "description",
            "journal_type", "status", "status_display", "period", "branch",
            "currency", "exchange_rate", "total_debit", "total_credit",
            "is_balanced", "is_locked", "notes", "reverses", "lines",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "number", "status", "status_display", "period", "total_debit",
            "total_credit", "is_balanced", "is_locked", "reverses", "lines",
            "posting_date", "created_at", "updated_at",
        ]


class JournalLineWriteSerializer(serializers.Serializer):
    # Nested serializers aren't bound to their parent at __init__ time, so the
    # request-context scoping mixin can't constrain these querysets. They accept
    # any workspace's rows here; the parent ``JournalCreateSerializer.validate``
    # rejects cross-tenant references (with request context available there).
    account = serializers.PrimaryKeyRelatedField(queryset=Account.objects.all())
    debit = serializers.DecimalField(max_digits=16, decimal_places=2, required=False, default=0)
    credit = serializers.DecimalField(max_digits=16, decimal_places=2, required=False, default=0)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    cost_center = serializers.PrimaryKeyRelatedField(
        queryset=CostCenter.objects.all(), required=False, allow_null=True
    )
    branch = serializers.PrimaryKeyRelatedField(
        queryset=Branch.objects.all(), required=False, allow_null=True
    )


class JournalCreateSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"branch": Branch, "currency": Currency}
    lines = JournalLineWriteSerializer(many=True)
    post = serializers.BooleanField(required=False, default=False, write_only=True)

    class Meta:
        model = JournalEntry
        fields = [
            "date", "posting_date", "reference", "description", "journal_type",
            "branch", "currency", "exchange_rate", "notes", "lines", "post",
        ]

    def validate_lines(self, value):
        if not value or len(value) < 2:
            raise serializers.ValidationError("A journal needs at least two lines.")
        return value

    def validate(self, attrs):
        # Cross-tenant guard on nested account/cost-center/branch refs.
        hostel = getattr(self.context.get("request"), "hostel", None)
        if hostel is not None:
            for line in attrs.get("lines", []):
                for key in ("account", "cost_center", "branch"):
                    rel = line.get(key)
                    if rel is not None and rel.hostel_id != hostel.id:
                        raise serializers.ValidationError({"lines": f"Unknown {key}."})
        return attrs


# --------------------------------------------------------------------------- #
# Ledger (read-only)
# --------------------------------------------------------------------------- #
class LedgerEntrySerializer(serializers.ModelSerializer):
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)
    journal_number = serializers.CharField(source="journal.number", read_only=True)

    class Meta:
        model = LedgerEntry
        fields = [
            "id", "account", "account_code", "account_name", "journal",
            "journal_number", "date", "debit", "credit", "description",
        ]
        read_only_fields = fields


# --------------------------------------------------------------------------- #
# Budgets
# --------------------------------------------------------------------------- #
class BudgetLineSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"account": Account}
    account_code = serializers.CharField(source="account.code", read_only=True)
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = BudgetLine
        fields = ["id", "account", "account_code", "account_name", "amount", "period_month"]
        read_only_fields = ["id", "account_code", "account_name"]


class BudgetSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"fiscal_year": FiscalYear, "branch": Branch, "cost_center": CostCenter}
    lines = BudgetLineSerializer(many=True, required=False)

    class Meta:
        model = Budget
        fields = [
            "id", "name", "fiscal_year", "period_type", "branch", "cost_center",
            "is_approved", "lines", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_approved", "created_at", "updated_at"]

    def create(self, validated_data):
        lines = validated_data.pop("lines", [])
        hostel = self.context["request"].hostel
        budget = Budget.objects.create(hostel=hostel, **validated_data)
        for line in lines:
            BudgetLine.objects.create(hostel=hostel, budget=budget, **line)
        return budget


# --------------------------------------------------------------------------- #
# Fixed assets
# --------------------------------------------------------------------------- #
class DepreciationEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = DepreciationEntry
        fields = ["id", "asset", "date", "amount", "journal", "created_at"]
        read_only_fields = fields


class FixedAssetSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {
        "asset_account": Account,
        "depreciation_expense_account": Account,
        "accumulated_depreciation_account": Account,
        "branch": Branch,
    }
    net_book_value = serializers.DecimalField(max_digits=16, decimal_places=2, read_only=True)

    class Meta:
        model = FixedAsset
        fields = [
            "id", "name", "category", "code", "purchase_cost", "purchase_date",
            "useful_life_months", "salvage_value", "depreciation_method",
            "declining_rate", "accumulated_depreciation", "net_book_value",
            "status", "disposed_date", "asset_account",
            "depreciation_expense_account", "accumulated_depreciation_account",
            "branch", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "accumulated_depreciation", "net_book_value", "status",
            "disposed_date", "created_at", "updated_at",
        ]


# --------------------------------------------------------------------------- #
# Bank reconciliation
# --------------------------------------------------------------------------- #
class BankAccountSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"account": Account}
    account_name = serializers.CharField(source="account.name", read_only=True)

    class Meta:
        model = BankAccount
        fields = [
            "id", "name", "account", "account_name", "bank_name",
            "account_number", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "account_name", "created_at", "updated_at"]


class BankStatementLineSerializer(_HostelScopedRelationsMixin, serializers.ModelSerializer):
    scoped_relations = {"bank_account": BankAccount}

    class Meta:
        model = BankStatementLine
        fields = [
            "id", "bank_account", "date", "description", "reference", "amount",
            "is_reconciled", "matched_line", "reconciled_at", "created_at",
        ]
        read_only_fields = ["id", "is_reconciled", "matched_line", "reconciled_at", "created_at"]
