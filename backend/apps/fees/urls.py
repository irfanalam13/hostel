from rest_framework.routers import DefaultRouter
from .views import FeePlanViewSet, StudentFeePlanViewSet, FeeLedgerViewSet

router = DefaultRouter()
router.register(r"fee-plans", FeePlanViewSet, basename="fee_plans")
router.register(r"student-fee-plans", StudentFeePlanViewSet, basename="student_fee_plans")
router.register(r"ledgers", FeeLedgerViewSet, basename="fee_ledgers")
urlpatterns = router.urls