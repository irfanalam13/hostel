from django.contrib import admin

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


@admin.register(FeeCategory)
class FeeCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "hostel", "is_system", "is_active")
    list_filter = ("is_system", "is_active")
    search_fields = ("name",)


@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ("name", "hostel", "category", "amount", "recurrence", "is_active")
    list_filter = ("recurrence", "is_active")
    search_fields = ("name",)


@admin.register(FeeAssignment)
class FeeAssignmentAdmin(admin.ModelAdmin):
    list_display = ("fee_structure", "resident", "hostel", "status", "start_date")
    list_filter = ("status",)


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0


class InvoiceAdjustmentInline(admin.TabularInline):
    model = InvoiceAdjustment
    extra = 0


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "hostel", "resident", "status", "total", "paid_amount", "due_date")
    list_filter = ("status",)
    search_fields = ("number", "resident__full_name")
    inlines = [InvoiceLineInline, InvoiceAdjustmentInline]


@admin.register(PaymentRecord)
class PaymentRecordAdmin(admin.ModelAdmin):
    list_display = ("receipt_number", "hostel", "resident", "amount", "method", "status", "received_at")
    list_filter = ("status", "method")
    search_fields = ("receipt_number", "reference")


@admin.register(ExpenseCategory)
class ExpenseCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "hostel", "is_system", "is_active")
    list_filter = ("is_system", "is_active")


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("title", "hostel", "category", "amount", "status", "expense_date")
    list_filter = ("status",)
    search_fields = ("title", "vendor_name")


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ("title", "hostel", "source", "amount", "income_date")
    list_filter = ("source",)


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("refund_type", "hostel", "resident", "amount", "status", "processed_at")
    list_filter = ("status", "refund_type")


@admin.register(Discount)
class DiscountAdmin(admin.ModelAdmin):
    list_display = ("name", "hostel", "discount_type", "value", "used_count", "is_active")
    list_filter = ("discount_type", "is_active")


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ("name", "hostel", "scholarship_type", "award_type", "value", "is_active")
    list_filter = ("scholarship_type", "is_active")


@admin.register(ScholarshipAward)
class ScholarshipAwardAdmin(admin.ModelAdmin):
    list_display = ("scholarship", "resident", "hostel", "status", "valid_until")
    list_filter = ("status",)


@admin.register(LedgerTransaction)
class LedgerTransactionAdmin(admin.ModelAdmin):
    list_display = ("occurred_at", "hostel", "direction", "category", "amount", "method")
    list_filter = ("direction",)
    search_fields = ("category", "memo")


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("__str__", "hostel", "period_year", "period_month", "amount")
