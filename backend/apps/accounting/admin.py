from django.contrib import admin

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


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "hostel", "type", "is_group", "is_active")
    list_filter = ("type", "is_group", "is_active")
    search_fields = ("code", "name")


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 0


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("number", "hostel", "date", "status", "total_debit", "total_credit", "journal_type")
    list_filter = ("status", "journal_type")
    search_fields = ("number", "reference", "description")
    inlines = [JournalLineInline]


@admin.register(LedgerEntry)
class LedgerEntryAdmin(admin.ModelAdmin):
    list_display = ("date", "hostel", "account", "debit", "credit", "journal")
    search_fields = ("account__code", "description")


@admin.register(FiscalYear)
class FiscalYearAdmin(admin.ModelAdmin):
    list_display = ("name", "hostel", "start_date", "end_date", "is_closed")
    list_filter = ("is_closed",)


@admin.register(AccountingPeriod)
class AccountingPeriodAdmin(admin.ModelAdmin):
    list_display = ("name", "hostel", "fiscal_year", "start_date", "end_date", "is_closed")
    list_filter = ("is_closed",)


class BudgetLineInline(admin.TabularInline):
    model = BudgetLine
    extra = 0


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("name", "hostel", "fiscal_year", "period_type", "is_approved")
    inlines = [BudgetLineInline]


@admin.register(FixedAsset)
class FixedAssetAdmin(admin.ModelAdmin):
    list_display = ("name", "hostel", "purchase_cost", "accumulated_depreciation", "status")
    list_filter = ("status", "depreciation_method")


@admin.register(TaxCode)
class TaxCodeAdmin(admin.ModelAdmin):
    list_display = ("name", "hostel", "tax_type", "rate", "is_active")


admin.site.register(Branch)
admin.site.register(CostCenter)
admin.site.register(Currency)
admin.site.register(ExchangeRate)
admin.site.register(DepreciationEntry)
admin.site.register(BankAccount)
admin.site.register(BankStatementLine)
