"""Finance Management domain models.

The enterprise finance layer on top of the canonical Track A billing domain
(``apps.billing`` / ``apps.residents``). Everything is tenant-scoped to
``tenants.Hostel`` via ``HostelScopedModel`` (UUID pk + timestamps + hostel FK)
so no financial row can ever be shared between workspaces.

Domain map:

- **Fees** — ``FeeCategory`` / ``FeeStructure`` (templates: recurrence, tax,
  late-fine rules) assigned to residents via ``FeeAssignment``.
- **Invoicing** — ``Invoice`` + ``InvoiceLine`` + ``InvoiceAdjustment``
  (discounts / scholarships / waivers), per-workspace numbering through
  ``DocumentSequence``.
- **Collection** — ``PaymentRecord`` with verification workflow and auto
  receipt numbers; only verified payments settle an invoice.
- **Money in/out** — ``Income``, ``Expense`` (+ ``ExpenseCategory``,
  approval workflow, recurrence), ``Refund`` (request → approve → process).
- **Concessions** — ``Discount`` definitions and ``Scholarship`` /
  ``ScholarshipAward`` programs.
- **Ledger** — ``LedgerTransaction``: an append-only, signed feed of every
  settled movement powering the dashboard, cash-flow and reports.
- **Budgeting** — ``Budget`` per expense category and period.

Amount invariants mirror ``apps.billing``: charges/payments are strictly
positive; computed rollups are non-negative. Signed values only ever appear on
``LedgerTransaction`` via its ``direction`` flag.
"""
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from apps.common.models import HostelScopedModel

POSITIVE_AMOUNT = [MinValueValidator(Decimal("0.01"))]
NON_NEGATIVE_AMOUNT = [MinValueValidator(Decimal("0.00"))]
PERCENT_RANGE = [MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("100.00"))]


class PaymentMethod(models.TextChoices):
    CASH = "cash", "Cash"
    BANK_TRANSFER = "bank_transfer", "Bank Transfer"
    MOBILE_BANKING = "mobile_banking", "Mobile Banking"
    QR = "qr", "QR Payment"
    CARD = "card", "Card"
    ONLINE = "online", "Online Gateway"
    UPI = "upi", "UPI"
    WALLET = "wallet", "Wallet"
    CHEQUE = "cheque", "Cheque"
    OTHER = "other", "Other"


class DocumentSequence(HostelScopedModel):
    """Per-workspace monotonic counters for human-facing document numbers
    (invoice / receipt). Rows are locked with ``select_for_update`` inside the
    issuing transaction so concurrent issuance can't mint duplicates."""

    class DocType(models.TextChoices):
        INVOICE = "invoice", "Invoice"
        RECEIPT = "receipt", "Receipt"

    doc_type = models.CharField(max_length=16, choices=DocType.choices)
    next_number = models.PositiveIntegerField(default=1)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["hostel", "doc_type"], name="uniq_sequence_per_hostel"),
        ]

    def __str__(self):
        return f"{self.doc_type} → {self.next_number}"


# --------------------------------------------------------------------------- #
# Fees
# --------------------------------------------------------------------------- #
class FeeCategory(HostelScopedModel):
    """A grouping bucket for fee structures (Hostel Fee, Mess Fee, ...).
    Workspaces get a seeded system set and can add unlimited custom ones."""

    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=64, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "fee categories"
        constraints = [
            models.UniqueConstraint(fields=["hostel", "name"], name="uniq_fee_category_per_hostel"),
        ]

    def __str__(self):
        return self.name


class FeeStructure(HostelScopedModel):
    """A reusable fee template: amount, recurrence, tax and late-fine rules."""

    class Recurrence(models.TextChoices):
        ONE_TIME = "one_time", "One Time"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        SEMESTER = "semester", "Semester"
        ANNUAL = "annual", "Annual"

    class LateFineType(models.TextChoices):
        NONE = "none", "No Late Fine"
        FIXED = "fixed", "Fixed Amount"
        PERCENTAGE = "percentage", "Percentage of Amount"

    name = models.CharField(max_length=160)
    category = models.ForeignKey(
        FeeCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="structures"
    )
    description = models.CharField(max_length=255, blank=True, default="")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=NON_NEGATIVE_AMOUNT)
    recurrence = models.CharField(
        max_length=16, choices=Recurrence.choices, default=Recurrence.MONTHLY
    )
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, validators=PERCENT_RANGE
    )
    allow_installments = models.BooleanField(default=False)
    # Day of month recurring dues fall on; capped at 28 so every month works.
    due_day = models.PositiveSmallIntegerField(
        default=5, validators=[MinValueValidator(1), MaxValueValidator(28)]
    )
    grace_period_days = models.PositiveSmallIntegerField(default=0)
    late_fine_type = models.CharField(
        max_length=16, choices=LateFineType.choices, default=LateFineType.NONE
    )
    late_fine_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=NON_NEGATIVE_AMOUNT
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "name"], name="uniq_fee_structure_per_hostel"),
        ]

    def __str__(self):
        return self.name


class FeeAssignment(HostelScopedModel):
    """A fee structure attached to a resident (individually or in bulk),
    optionally overriding the template amount. Waiving keeps the history."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        ENDED = "ended", "Ended"
        WAIVED = "waived", "Waived"

    fee_structure = models.ForeignKey(
        FeeStructure, on_delete=models.CASCADE, related_name="assignments"
    )
    resident = models.ForeignKey(
        "residents.Resident", on_delete=models.CASCADE, related_name="fee_assignments"
    )
    amount_override = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True, validators=NON_NEGATIVE_AMOUNT
    )
    start_date = models.DateField(default=timezone.localdate)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ACTIVE, db_index=True
    )
    waived_reason = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hostel", "resident", "status"]),
        ]

    @property
    def effective_amount(self) -> Decimal:
        if self.amount_override is not None:
            return self.amount_override
        return self.fee_structure.amount

    def __str__(self):
        return f"{self.fee_structure.name} → {self.resident.full_name}"


# --------------------------------------------------------------------------- #
# Discounts & scholarships
# --------------------------------------------------------------------------- #
class Discount(HostelScopedModel):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed Amount"

    class Reason(models.TextChoices):
        SEASONAL = "seasonal", "Seasonal"
        PROMOTIONAL = "promotional", "Promotional"
        EARLY_PAYMENT = "early_payment", "Early Payment"
        SIBLING = "sibling", "Sibling"
        MERIT = "merit", "Merit"
        STAFF = "staff", "Staff"
        CUSTOM = "custom", "Custom"

    name = models.CharField(max_length=160)
    discount_type = models.CharField(
        max_length=16, choices=DiscountType.choices, default=DiscountType.PERCENTAGE
    )
    # Percentage (0-100) when percentage-typed, otherwise a currency amount.
    value = models.DecimalField(max_digits=12, decimal_places=2, validators=POSITIVE_AMOUNT)
    reason = models.CharField(max_length=24, choices=Reason.choices, default=Reason.CUSTOM)
    description = models.CharField(max_length=255, blank=True, default="")
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    max_uses = models.PositiveIntegerField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "name"], name="uniq_discount_per_hostel"),
        ]

    def is_usable(self, on_date=None) -> bool:
        on_date = on_date or timezone.localdate()
        if not self.is_active:
            return False
        if self.valid_from and on_date < self.valid_from:
            return False
        if self.valid_until and on_date > self.valid_until:
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        return True

    def amount_for(self, base: Decimal) -> Decimal:
        if self.discount_type == self.DiscountType.PERCENTAGE:
            return (base * self.value / Decimal("100")).quantize(Decimal("0.01"))
        return min(self.value, base)

    def __str__(self):
        return self.name


class Scholarship(HostelScopedModel):
    class ScholarshipType(models.TextChoices):
        MERIT = "merit", "Merit"
        NEED_BASED = "need_based", "Need-Based"
        SPORTS = "sports", "Sports"
        GOVERNMENT = "government", "Government"
        NGO = "ngo", "NGO"
        INTERNAL = "internal", "Internal"
        CUSTOM = "custom", "Custom"

    class AwardType(models.TextChoices):
        PERCENTAGE = "percentage", "Percentage"
        FIXED = "fixed", "Fixed Amount"

    name = models.CharField(max_length=160)
    scholarship_type = models.CharField(
        max_length=24, choices=ScholarshipType.choices, default=ScholarshipType.CUSTOM
    )
    award_type = models.CharField(
        max_length=16, choices=AwardType.choices, default=AwardType.PERCENTAGE
    )
    value = models.DecimalField(max_digits=12, decimal_places=2, validators=POSITIVE_AMOUNT)
    description = models.CharField(max_length=255, blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "name"], name="uniq_scholarship_per_hostel"),
        ]

    def amount_for(self, base: Decimal) -> Decimal:
        if self.award_type == self.AwardType.PERCENTAGE:
            return (base * self.value / Decimal("100")).quantize(Decimal("0.01"))
        return min(self.value, base)

    def __str__(self):
        return self.name


class ScholarshipAward(HostelScopedModel):
    """A scholarship granted to a specific resident (approval-workflowed)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        EXPIRED = "expired", "Expired"
        REVOKED = "revoked", "Revoked"

    scholarship = models.ForeignKey(Scholarship, on_delete=models.CASCADE, related_name="awards")
    resident = models.ForeignKey(
        "residents.Resident", on_delete=models.CASCADE, related_name="scholarship_awards"
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True, default="")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hostel", "resident", "status"]),
        ]

    def __str__(self):
        return f"{self.scholarship.name} → {self.resident.full_name}"


# --------------------------------------------------------------------------- #
# Invoicing
# --------------------------------------------------------------------------- #
class Invoice(HostelScopedModel):
    """A tax-ready resident invoice. Money fields are rollups recomputed by
    ``services.recalc_invoice`` from lines / adjustments / verified payments —
    never written directly by API clients."""

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        PARTIAL = "partial", "Partially Paid"
        PAID = "paid", "Paid"
        OVERDUE = "overdue", "Overdue"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    number = models.CharField(max_length=32)
    resident = models.ForeignKey(
        "residents.Resident", on_delete=models.PROTECT, related_name="finance_invoices"
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    issue_date = models.DateField(default=timezone.localdate)
    due_date = models.DateField(null=True, blank=True)
    currency = models.CharField(max_length=8, default="NPR")

    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=NON_NEGATIVE_AMOUNT
    )
    tax_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=NON_NEGATIVE_AMOUNT
    )
    discount_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=NON_NEGATIVE_AMOUNT
    )
    scholarship_total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=NON_NEGATIVE_AMOUNT
    )
    total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=NON_NEGATIVE_AMOUNT
    )
    paid_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=NON_NEGATIVE_AMOUNT
    )

    notes = models.TextField(blank=True, default="")
    terms = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-issue_date", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["hostel", "number"], name="uniq_invoice_number_per_hostel"),
        ]
        indexes = [
            models.Index(fields=["hostel", "status"]),
            models.Index(fields=["hostel", "resident"]),
            models.Index(fields=["hostel", "due_date"]),
        ]

    @property
    def balance(self) -> Decimal:
        remaining = self.total - self.paid_amount
        return remaining if remaining > 0 else Decimal("0.00")

    def __str__(self):
        return self.number


class InvoiceLine(HostelScopedModel):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    fee_structure = models.ForeignKey(
        FeeStructure, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(
        max_digits=8, decimal_places=2, default=1, validators=POSITIVE_AMOUNT
    )
    unit_price = models.DecimalField(
        max_digits=12, decimal_places=2, validators=NON_NEGATIVE_AMOUNT
    )
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, validators=PERCENT_RANGE
    )
    # quantity * unit_price and its tax, frozen at computation time.
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=NON_NEGATIVE_AMOUNT
    )
    tax_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=NON_NEGATIVE_AMOUNT
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.description} ({self.invoice.number})"


class InvoiceAdjustment(HostelScopedModel):
    """A subtractive concession on an invoice: a discount, a scholarship award
    or an ad-hoc waiver. Amount is stored positive and subtracted in totals."""

    class Kind(models.TextChoices):
        DISCOUNT = "discount", "Discount"
        SCHOLARSHIP = "scholarship", "Scholarship"
        WAIVER = "waiver", "Waiver"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="adjustments")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    discount = models.ForeignKey(
        Discount, on_delete=models.SET_NULL, null=True, blank=True, related_name="applications"
    )
    scholarship_award = models.ForeignKey(
        ScholarshipAward, on_delete=models.SET_NULL, null=True, blank=True, related_name="applications"
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=POSITIVE_AMOUNT)
    note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.kind} −{self.amount} ({self.invoice.number})"


# --------------------------------------------------------------------------- #
# Collection
# --------------------------------------------------------------------------- #
def payment_proof_path(instance, filename):
    return f"finance/payments/{instance.hostel_id}/{filename}"


class PaymentRecord(HostelScopedModel):
    """A collected payment. Supports the full lifecycle (pending →
    verified / failed / cancelled / refunded); only *verified* payments count
    toward an invoice's ``paid_amount`` and the ledger."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Verification"
        VERIFIED = "verified", "Verified"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"
        REFUNDED = "refunded", "Refunded"

    receipt_number = models.CharField(max_length=32, blank=True, default="")
    invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments"
    )
    resident = models.ForeignKey(
        "residents.Resident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finance_payments",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=POSITIVE_AMOUNT)
    method = models.CharField(
        max_length=24, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.VERIFIED, db_index=True
    )
    reference = models.CharField(max_length=120, blank=True, default="")
    note = models.CharField(max_length=255, blank=True, default="")
    proof = models.FileField(upload_to=payment_proof_path, null=True, blank=True)
    received_at = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["hostel", "status"]),
            models.Index(fields=["hostel", "received_at"]),
            models.Index(fields=["hostel", "resident"]),
        ]

    def __str__(self):
        return f"{self.receipt_number or self.id} — {self.amount}"


# --------------------------------------------------------------------------- #
# Expenses / income
# --------------------------------------------------------------------------- #
class ExpenseCategory(HostelScopedModel):
    name = models.CharField(max_length=120)
    code = models.SlugField(max_length=64, blank=True, default="")
    description = models.CharField(max_length=255, blank=True, default="")
    is_system = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "expense categories"
        constraints = [
            models.UniqueConstraint(fields=["hostel", "name"], name="uniq_expense_category_per_hostel"),
        ]

    def __str__(self):
        return self.name


def expense_bill_path(instance, filename):
    return f"finance/expenses/{instance.hostel_id}/{filename}"


class Expense(HostelScopedModel):
    """A hostel expense with an approval workflow: pending → approved → paid
    (or rejected). Only *paid* expenses hit the ledger."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PAID = "paid", "Paid"

    class Recurrence(models.TextChoices):
        NONE = "none", "One Time"
        MONTHLY = "monthly", "Monthly"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUAL = "annual", "Annual"

    category = models.ForeignKey(
        ExpenseCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="expenses"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=POSITIVE_AMOUNT)
    tax_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=NON_NEGATIVE_AMOUNT
    )
    expense_date = models.DateField(default=timezone.localdate)
    payment_method = models.CharField(
        max_length=24, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    vendor_name = models.CharField(max_length=160, blank=True, default="")
    vendor_contact = models.CharField(max_length=120, blank=True, default="")
    reference = models.CharField(max_length=120, blank=True, default="")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    recurrence = models.CharField(
        max_length=16, choices=Recurrence.choices, default=Recurrence.NONE
    )
    attachment = models.FileField(upload_to=expense_bill_path, null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-expense_date", "-created_at"]
        indexes = [
            models.Index(fields=["hostel", "status"]),
            models.Index(fields=["hostel", "expense_date"]),
        ]

    def __str__(self):
        return self.title


def income_document_path(instance, filename):
    return f"finance/income/{instance.hostel_id}/{filename}"


class Income(HostelScopedModel):
    """Non-invoice income (cafeteria, laundry, donations, ...). Fee collection
    flows through invoices/payments; this captures everything else."""

    class Source(models.TextChoices):
        STUDENT_FEES = "student_fees", "Student Fees"
        ROOM_BOOKING = "room_booking", "Room Booking"
        SECURITY_DEPOSIT = "security_deposit", "Security Deposit"
        CAFETERIA = "cafeteria", "Cafeteria"
        LAUNDRY = "laundry", "Laundry"
        TRANSPORT = "transport", "Transport"
        INTERNET = "internet", "Internet"
        EXTRA_SERVICES = "extra_services", "Extra Services"
        COMMISSION = "commission", "Commission"
        INTEREST = "interest", "Interest Income"
        DONATION = "donation", "Donation"
        OTHER = "other", "Other"

    source = models.CharField(max_length=24, choices=Source.choices, default=Source.OTHER)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=POSITIVE_AMOUNT)
    income_date = models.DateField(default=timezone.localdate)
    payment_method = models.CharField(
        max_length=24, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    reference = models.CharField(max_length=120, blank=True, default="")
    attachment = models.FileField(upload_to=income_document_path, null=True, blank=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-income_date", "-created_at"]
        indexes = [
            models.Index(fields=["hostel", "income_date"]),
            models.Index(fields=["hostel", "source"]),
        ]

    def __str__(self):
        return self.title


# --------------------------------------------------------------------------- #
# Refunds
# --------------------------------------------------------------------------- #
class Refund(HostelScopedModel):
    """Refund lifecycle: requested → approved → processed (or rejected).
    Processing posts an outward ledger transaction and, when the linked
    payment is fully refunded, flips it (and its invoice) to refunded."""

    class RefundType(models.TextChoices):
        SECURITY_DEPOSIT = "security_deposit", "Security Deposit"
        ADMISSION_CANCELLATION = "admission_cancellation", "Admission Cancellation"
        OVERPAYMENT = "overpayment", "Overpayment"
        SCHOLARSHIP_ADJUSTMENT = "scholarship_adjustment", "Scholarship Adjustment"
        DUPLICATE_PAYMENT = "duplicate_payment", "Duplicate Payment"
        WITHDRAWAL = "withdrawal", "Hostel Withdrawal"
        CUSTOM = "custom", "Custom"

    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        PROCESSED = "processed", "Processed"

    refund_type = models.CharField(
        max_length=32, choices=RefundType.choices, default=RefundType.CUSTOM
    )
    payment = models.ForeignKey(
        PaymentRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name="refunds"
    )
    invoice = models.ForeignKey(
        Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="refunds"
    )
    resident = models.ForeignKey(
        "residents.Resident",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="finance_refunds",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=POSITIVE_AMOUNT)
    method = models.CharField(
        max_length=24, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    reason = models.CharField(max_length=255)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.REQUESTED, db_index=True
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["hostel", "status"]),
        ]

    def __str__(self):
        return f"{self.refund_type} — {self.amount}"


# --------------------------------------------------------------------------- #
# Ledger & budgets
# --------------------------------------------------------------------------- #
class LedgerTransaction(HostelScopedModel):
    """Append-only feed of settled money movements. Posted exclusively by
    ``apps.finance.services`` when a payment verifies, an expense is paid, an
    income is recorded or a refund processes — never written via the API."""

    class Direction(models.TextChoices):
        IN = "in", "Money In"
        OUT = "out", "Money Out"

    direction = models.CharField(max_length=4, choices=Direction.choices)
    category = models.CharField(max_length=64)  # e.g. "fee_collection", "expense:Utilities"
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=POSITIVE_AMOUNT)
    method = models.CharField(
        max_length=24, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    occurred_at = models.DateTimeField(default=timezone.now)
    # Loose reference to the source row, mirroring the audit-log convention.
    entity_type = models.CharField(max_length=64)  # "finance.paymentrecord", ...
    entity_id = models.CharField(max_length=64)
    resident = models.ForeignKey(
        "residents.Resident", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    memo = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["hostel", "occurred_at"]),
            models.Index(fields=["hostel", "direction"]),
        ]

    def __str__(self):
        sign = "+" if self.direction == self.Direction.IN else "−"
        return f"{sign}{self.amount} {self.category}"


class Budget(HostelScopedModel):
    """A spend target for an expense category over a month (or the whole year
    when ``period_month`` is null). Consumption is computed from paid expenses."""

    name = models.CharField(max_length=160, blank=True, default="")
    category = models.ForeignKey(
        ExpenseCategory, on_delete=models.CASCADE, null=True, blank=True, related_name="budgets"
    )
    period_year = models.PositiveIntegerField()
    period_month = models.PositiveSmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=POSITIVE_AMOUNT)
    note = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        ordering = ["-period_year", "-period_month"]
        constraints = [
            models.UniqueConstraint(
                fields=["hostel", "category", "period_year", "period_month"],
                name="uniq_budget_per_hostel_period",
            ),
        ]

    def __str__(self):
        period = f"{self.period_year}" + (f"-{self.period_month:02d}" if self.period_month else "")
        return f"{self.name or (self.category.name if self.category else 'Overall')} {period}"
