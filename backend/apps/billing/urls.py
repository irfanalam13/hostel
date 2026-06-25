from rest_framework.routers import DefaultRouter
from .views import MonthlyDueViewSet, PaymentViewSet, DashboardViewSet

router = DefaultRouter()
router.register(r"dues", MonthlyDueViewSet, basename="dues")
router.register(r"payments", PaymentViewSet, basename="payments")
router.register(r"dashboard", DashboardViewSet, basename="dashboard")

urlpatterns = router.urls