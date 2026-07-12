from rest_framework.routers import DefaultRouter

from .views import (
    AccountViewSet,
    AccountingDashboardViewSet,
    AccountingPeriodViewSet,
    AccountingReportsViewSet,
    BankAccountViewSet,
    BankStatementLineViewSet,
    BranchViewSet,
    BudgetViewSet,
    CostCenterViewSet,
    CurrencyViewSet,
    ExchangeRateViewSet,
    FiscalYearViewSet,
    FixedAssetViewSet,
    JournalEntryViewSet,
    LedgerEntryViewSet,
    TaxCodeViewSet,
)

router = DefaultRouter()
router.register(r"branches", BranchViewSet, basename="accounting-branches")
router.register(r"cost-centers", CostCenterViewSet, basename="accounting-cost-centers")
router.register(r"currencies", CurrencyViewSet, basename="accounting-currencies")
router.register(r"exchange-rates", ExchangeRateViewSet, basename="accounting-exchange-rates")
router.register(r"fiscal-years", FiscalYearViewSet, basename="accounting-fiscal-years")
router.register(r"periods", AccountingPeriodViewSet, basename="accounting-periods")
router.register(r"accounts", AccountViewSet, basename="accounting-accounts")
router.register(r"tax-codes", TaxCodeViewSet, basename="accounting-tax-codes")
router.register(r"journals", JournalEntryViewSet, basename="accounting-journals")
router.register(r"ledger", LedgerEntryViewSet, basename="accounting-ledger")
router.register(r"budgets", BudgetViewSet, basename="accounting-budgets")
router.register(r"fixed-assets", FixedAssetViewSet, basename="accounting-fixed-assets")
router.register(r"bank-accounts", BankAccountViewSet, basename="accounting-bank-accounts")
router.register(
    r"bank-statement-lines", BankStatementLineViewSet, basename="accounting-bank-statement-lines"
)
router.register(r"reports", AccountingReportsViewSet, basename="accounting-reports")
router.register(r"dashboard", AccountingDashboardViewSet, basename="accounting-dashboard")

urlpatterns = router.urls
