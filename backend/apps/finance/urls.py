from rest_framework.routers import DefaultRouter

from .views import (
    BudgetViewSet,
    DiscountViewSet,
    ExpenseCategoryViewSet,
    ExpenseViewSet,
    FeeAssignmentViewSet,
    FeeCategoryViewSet,
    FeeStructureViewSet,
    FinanceDashboardViewSet,
    FinanceReportsViewSet,
    IncomeViewSet,
    InvoiceViewSet,
    LedgerTransactionViewSet,
    PaymentRecordViewSet,
    RefundViewSet,
    ScholarshipAwardViewSet,
    ScholarshipViewSet,
)

router = DefaultRouter()
router.register(r"fee-categories", FeeCategoryViewSet, basename="finance-fee-categories")
router.register(r"fee-structures", FeeStructureViewSet, basename="finance-fee-structures")
router.register(r"fee-assignments", FeeAssignmentViewSet, basename="finance-fee-assignments")
router.register(r"discounts", DiscountViewSet, basename="finance-discounts")
router.register(r"scholarships", ScholarshipViewSet, basename="finance-scholarships")
router.register(
    r"scholarship-awards", ScholarshipAwardViewSet, basename="finance-scholarship-awards"
)
router.register(r"invoices", InvoiceViewSet, basename="finance-invoices")
router.register(r"payments", PaymentRecordViewSet, basename="finance-payments")
router.register(r"expense-categories", ExpenseCategoryViewSet, basename="finance-expense-categories")
router.register(r"expenses", ExpenseViewSet, basename="finance-expenses")
router.register(r"income", IncomeViewSet, basename="finance-income")
router.register(r"refunds", RefundViewSet, basename="finance-refunds")
router.register(r"budgets", BudgetViewSet, basename="finance-budgets")
router.register(r"transactions", LedgerTransactionViewSet, basename="finance-transactions")
router.register(r"dashboard", FinanceDashboardViewSet, basename="finance-dashboard")
router.register(r"reports", FinanceReportsViewSet, basename="finance-reports")

urlpatterns = router.urls
