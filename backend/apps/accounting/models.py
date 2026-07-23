"""Enterprise double-entry accounting domain models.

Modeled on ERP accounting cores (NetSuite / Business Central / Odoo) but scoped
to a hostel workspace. Everything is tenant-isolated via ``HostelScopedModel``.

The invariant the whole module protects: **the books always balance.** Money
only enters the ledger through a *posted* ``JournalEntry`` whose debit and
credit lines are equal, so every derived statement (trial balance, P&L, balance
sheet) balances by construction. Posted entries are immutable — corrections are
made with reversing entries, never edits.

Account balances are computed purely from posted ``LedgerEntry`` rows (signed
debit-positive). Opening balances are themselves entered as a balanced opening
journal (see ``services.post_opening_balances``), so nothing can silently
unbalance the ledger.
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.models import HostelScopedModel

NON_NEGATIVE = [MinValueValidator(Decimal("0.00"))]


class NumberSequence(HostelScopedModel):
    """Per-workspace monotonic counter for human-facing document numbers
    (journal vouchers). Locked with ``select_for_update`` inside the issuing
    transaction so concurrent creation can't mint duplicates."""

    key = models.CharField(max_length=32)  # e.g. "journal"
    next_number = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["hostel", "key"], name="uniq_acct_sequence_per_hostel"),
        ]

    def __str__(self):
        return f"{self.key} → {self.next_number}"


class AccountType(models.TextChoices):
    ASSET = "asset", "Asset"
    LIABILITY = "liability", "Liability"
    EQUITY = "equity", "Equity"
    INCOME = "income", "Income"
    EXPENSE = "expense", "Expense"


# Debit-normal types carry positive balances on the debit side; credit-normal
# on the credit side. Drives statement presentation and normal-balance display.
DEBIT_NORMAL_TYPES = {AccountType.ASSET, AccountType.EXPENSE}
CREDIT_NORMAL_TYPES = {AccountType.LIABILITY, AccountType.EQUITY, AccountType.INCOME}

# Balance-sheet vs income-statement classification.
BALANCE_SHEET_TYPES = {AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY}
INCOME_STATEMENT_TYPES = {AccountType.INCOME, AccountType.EXPENSE}


# --------------------------------------------------------------------------- #
# Organizational dimensions
# --------------------------------------------------------------------------- #
class Branch(HostelScopedModel):
    """A physical branch of a workspace for multi-branch accounting. Journals
    and accounts may be tagged with a branch for branch-level statements."""

    name = models.CharField(max_length=160)
    code = models.CharField(max_length=32, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "branches"
        constraints = [
            models.UniqueConstraint(fields=["hostel", "name"], name="uniq_branch_per_hostel"),
        ]

    def __str__(self):
        return self.name


class CostCenter(HostelScopedModel):
    """A cost/profit center for allocating income and expense (Administration,
    Kitchen, Laundry, …)."""

    name = models.CharField(max_length=160)
    code = models.CharField(max_length=32, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "name"], name="uniq_cost_center_per_hostel"),
        ]

    def __str__(self):
        return self.name


class Currency(HostelScopedModel):
    """A currency a workspace transacts in. Exactly one is the base currency;
    all statements are expressed in it."""

    code = models.CharField(max_length=8)  # ISO 4217, e.g. NPR / USD
    name = models.CharField(max_length=80, blank=True, default="")
    symbol = models.CharField(max_length=8, blank=True, default="")
    is_base = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-is_base", "code"]
        verbose_name_plural = "currencies"
        constraints = [
            models.UniqueConstraint(fields=["hostel", "code"], name="uniq_currency_per_hostel"),
        ]

    def __str__(self):
        return self.code


class ExchangeRate(HostelScopedModel):
    """Rate of one unit of ``currency`` in the workspace's base currency, on a
    given date. The most recent rate on/before a transaction date applies."""

    currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name="rates")
    rate_to_base = models.DecimalField(max_digits=18, decimal_places=8, validators=NON_NEGATIVE)
    as_of = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ["-as_of"]
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "currency", "as_of"], name="uniq_rate_per_currency_date"
            ),
        ]

    def __str__(self):
        return f"{self.currency.code} @ {self.rate_to_base} ({self.as_of})"


# --------------------------------------------------------------------------- #
# Fiscal calendar
# --------------------------------------------------------------------------- #
class FiscalYear(HostelScopedModel):
    name = models.CharField(max_length=40)  # e.g. "FY 2025/26"
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-start_date"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "name"], name="uniq_fiscal_year_per_hostel"),
        ]

    def __str__(self):
        return self.name


class AccountingPeriod(HostelScopedModel):
    """A sub-period (usually a month) of a fiscal year. Posting is only allowed
    into an open period; closing a period locks it against further postings."""

    fiscal_year = models.ForeignKey(
        FiscalYear, on_delete=models.CASCADE, related_name="periods"
    )
    name = models.CharField(max_length=40)  # e.g. "2025-07"
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(default=False)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["start_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "fiscal_year", "name"], name="uniq_period_per_year"
            ),
        ]

    def __str__(self):
        return self.name


# --------------------------------------------------------------------------- #
# Chart of accounts
# --------------------------------------------------------------------------- #
class Account(HostelScopedModel):
    """A chart-of-accounts node. Group accounts (``is_group``) roll up their
    children and can't be posted to directly; leaf accounts carry the postings.
    ``code`` is unique per workspace and auto-assigned when omitted."""

    code = models.CharField(max_length=32)
    name = models.CharField(max_length=160)
    type = models.CharField(max_length=16, choices=AccountType.choices, db_index=True)
    subtype = models.CharField(max_length=64, blank=True, default="")
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children"
    )
    is_group = models.BooleanField(default=False)
    description = models.CharField(max_length=255, blank=True, default="")
    # Reference value used by ``post_opening_balances`` to build the opening
    # journal (signed, debit-positive). Never added to live balances directly.
    opening_balance = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    currency = models.ForeignKey(
        Currency, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="accounts"
    )
    cost_center = models.ForeignKey(
        CostCenter, on_delete=models.SET_NULL, null=True, blank=True, related_name="accounts"
    )
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "code"], name="uniq_account_code_per_hostel"),
        ]
        indexes = [
            models.Index(fields=["hostel", "type", "is_active"]),
        ]

    @property
    def normal_balance(self) -> str:
        return "debit" if self.type in DEBIT_NORMAL_TYPES else "credit"

    @property
    def is_debit_normal(self) -> bool:
        return self.type in DEBIT_NORMAL_TYPES

    def __str__(self):
        return f"{self.code} · {self.name}"


class TaxCode(HostelScopedModel):
    class TaxType(models.TextChoices):
        VAT = "vat", "VAT"
        GST = "gst", "GST"
        SALES = "sales", "Sales Tax"
        SERVICE = "service", "Service Tax"
        WITHHOLDING = "withholding", "Withholding Tax"
        INCOME = "income", "Income Tax"
        LOCAL = "local", "Local Tax"
        CUSTOM = "custom", "Custom"

    name = models.CharField(max_length=120)
    tax_type = models.CharField(max_length=16, choices=TaxType.choices, default=TaxType.VAT)
    rate = models.DecimalField(max_digits=6, decimal_places=3, validators=NON_NEGATIVE)
    # The liability/asset accounts tax collected/paid posts to.
    payable_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    receivable_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "name"], name="uniq_tax_code_per_hostel"),
        ]

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


# --------------------------------------------------------------------------- #
# Journals
# --------------------------------------------------------------------------- #
class JournalEntry(HostelScopedModel):
    """A double-entry journal. Lifecycle:
    draft → submitted → approved → posted → (reversed). Only *posted* entries
    hit the ledger; once posted an entry is immutable and can only be reversed.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        APPROVED = "approved", "Approved"
        POSTED = "posted", "Posted"
        REVERSED = "reversed", "Reversed"

    class JournalType(models.TextChoices):
        MANUAL = "manual", "Manual"
        AUTOMATIC = "automatic", "Automatic"
        RECURRING = "recurring", "Recurring"
        ADJUSTMENT = "adjustment", "Adjustment"
        OPENING = "opening", "Opening"
        CLOSING = "closing", "Closing"
        REVERSAL = "reversal", "Reversal"
        DEPRECIATION = "depreciation", "Depreciation"

    number = models.CharField(max_length=32)
    date = models.DateField(default=timezone.localdate)
    posting_date = models.DateField(null=True, blank=True)
    reference = models.CharField(max_length=120, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    journal_type = models.CharField(
        max_length=16, choices=JournalType.choices, default=JournalType.MANUAL
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    period = models.ForeignKey(
        AccountingPeriod, on_delete=models.PROTECT, null=True, blank=True, related_name="journals"
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="journals"
    )
    currency = models.ForeignKey(
        Currency, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    exchange_rate = models.DecimalField(max_digits=18, decimal_places=8, default=1)
    # Cached line totals (equal once balanced) for fast list rendering.
    total_debit = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    total_credit = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    is_locked = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")

    # Reversal linkage.
    reverses = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="reversed_by_entries"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "number"], name="uniq_journal_number_per_hostel"),
        ]
        indexes = [
            models.Index(fields=["hostel", "status"]),
            models.Index(fields=["hostel", "date"]),
        ]

    @property
    def is_balanced(self) -> bool:
        return self.total_debit == self.total_credit and self.total_debit > 0

    def __str__(self):
        return self.number


class JournalLine(HostelScopedModel):
    """A single debit-or-credit line of a journal. Exactly one of debit/credit
    is non-zero on a well-formed line."""

    journal = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="journal_lines")
    debit = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=NON_NEGATIVE)
    credit = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=NON_NEGATIVE)
    description = models.CharField(max_length=255, blank=True, default="")
    cost_center = models.ForeignKey(
        CostCenter, on_delete=models.SET_NULL, null=True, blank=True, related_name="journal_lines"
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        side = f"Dr {self.debit}" if self.debit else f"Cr {self.credit}"
        return f"{self.account.code} {side}"


class LedgerEntry(HostelScopedModel):
    """A posted general-ledger movement. Created only when a journal posts and
    deleted only when it reverses — the immutable, queryable record every
    statement reads from."""

    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="ledger_entries")
    journal = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="ledger_entries")
    journal_line = models.ForeignKey(
        JournalLine, on_delete=models.CASCADE, null=True, blank=True, related_name="+"
    )
    date = models.DateField(db_index=True)
    debit = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=NON_NEGATIVE)
    credit = models.DecimalField(max_digits=16, decimal_places=2, default=0, validators=NON_NEGATIVE)
    description = models.CharField(max_length=255, blank=True, default="")
    cost_center = models.ForeignKey(
        CostCenter, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["date", "created_at"]
        indexes = [
            models.Index(fields=["hostel", "account", "date"]),
            models.Index(fields=["hostel", "date"]),
        ]

    def __str__(self):
        return f"{self.account.code} {self.date} Dr{self.debit}/Cr{self.credit}"


# --------------------------------------------------------------------------- #
# Budgets
# --------------------------------------------------------------------------- #
class Budget(HostelScopedModel):
    class PeriodType(models.TextChoices):
        ANNUAL = "annual", "Annual"
        QUARTERLY = "quarterly", "Quarterly"
        MONTHLY = "monthly", "Monthly"

    # Explicit hostel FK (distinct related_name) — the abstract base's
    # ``%(class)s_items`` collides with ``finance.Budget``'s reverse accessor.
    hostel = models.ForeignKey(
        "tenants.Hostel", on_delete=models.CASCADE, related_name="accounting_budgets"
    )
    name = models.CharField(max_length=160)
    fiscal_year = models.ForeignKey(
        FiscalYear, on_delete=models.CASCADE, related_name="budgets"
    )
    period_type = models.CharField(
        max_length=12, choices=PeriodType.choices, default=PeriodType.ANNUAL
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="budgets"
    )
    cost_center = models.ForeignKey(
        CostCenter, on_delete=models.SET_NULL, null=True, blank=True, related_name="budgets"
    )
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "name", "fiscal_year"], name="uniq_budget_name_per_year"
            ),
        ]

    def __str__(self):
        return self.name


class BudgetLine(HostelScopedModel):
    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="budget_lines")
    amount = models.DecimalField(max_digits=16, decimal_places=2, validators=NON_NEGATIVE)
    # 1-12 for monthly/quarterly granularity; null = whole-year figure.
    period_month = models.PositiveSmallIntegerField(null=True, blank=True)

    class Meta:
        ordering = ["account__code"]

    def __str__(self):
        return f"{self.account.code}: {self.amount}"


# --------------------------------------------------------------------------- #
# Fixed assets & depreciation
# --------------------------------------------------------------------------- #
class FixedAsset(HostelScopedModel):
    class DepreciationMethod(models.TextChoices):
        STRAIGHT_LINE = "straight_line", "Straight Line"
        DECLINING = "declining_balance", "Declining Balance"
        NONE = "none", "No Depreciation"

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DISPOSED = "disposed", "Disposed"
        FULLY_DEPRECIATED = "fully_depreciated", "Fully Depreciated"

    name = models.CharField(max_length=180)
    category = models.CharField(max_length=120, blank=True, default="")
    code = models.CharField(max_length=48, blank=True, default="")
    purchase_cost = models.DecimalField(max_digits=16, decimal_places=2, validators=NON_NEGATIVE)
    purchase_date = models.DateField(default=timezone.localdate)
    useful_life_months = models.PositiveIntegerField(default=60)
    salvage_value = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    depreciation_method = models.CharField(
        max_length=20, choices=DepreciationMethod.choices, default=DepreciationMethod.STRAIGHT_LINE
    )
    declining_rate = models.DecimalField(max_digits=6, decimal_places=3, default=0)
    accumulated_depreciation = models.DecimalField(max_digits=16, decimal_places=2, default=0)
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    disposed_date = models.DateField(null=True, blank=True)
    # COA links used when posting depreciation.
    asset_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    depreciation_expense_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    accumulated_depreciation_account = models.ForeignKey(
        Account, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name="assets"
    )

    class Meta:
        ordering = ["-purchase_date"]
        indexes = [models.Index(fields=["hostel", "status"])]

    @property
    def net_book_value(self) -> Decimal:
        return self.purchase_cost - self.accumulated_depreciation

    @property
    def depreciable_base(self) -> Decimal:
        base = self.purchase_cost - self.salvage_value
        return base if base > 0 else Decimal("0.00")

    def __str__(self):
        return self.name


class DepreciationEntry(HostelScopedModel):
    asset = models.ForeignKey(FixedAsset, on_delete=models.CASCADE, related_name="depreciations")
    date = models.DateField(default=timezone.localdate)
    amount = models.DecimalField(max_digits=16, decimal_places=2, validators=NON_NEGATIVE)
    journal = models.ForeignKey(
        JournalEntry, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-date"]

    def __str__(self):
        return f"{self.asset.name} depreciation {self.amount} ({self.date})"


# --------------------------------------------------------------------------- #
# Bank reconciliation
# --------------------------------------------------------------------------- #
class BankAccount(HostelScopedModel):
    name = models.CharField(max_length=160)
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="bank_accounts"
    )
    bank_name = models.CharField(max_length=160, blank=True, default="")
    account_number = models.CharField(max_length=64, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class BankStatementLine(HostelScopedModel):
    bank_account = models.ForeignKey(
        BankAccount, on_delete=models.CASCADE, related_name="statement_lines"
    )
    date = models.DateField()
    description = models.CharField(max_length=255, blank=True, default="")
    reference = models.CharField(max_length=120, blank=True, default="")
    # Signed: positive = money into the bank, negative = out.
    amount = models.DecimalField(max_digits=16, decimal_places=2)
    is_reconciled = models.BooleanField(default=False)
    matched_line = models.ForeignKey(
        JournalLine, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reconciled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-date"]
        indexes = [models.Index(fields=["hostel", "bank_account", "is_reconciled"])]

    def __str__(self):
        return f"{self.date} {self.amount}"
