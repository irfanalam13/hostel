from rest_framework.routers import DefaultRouter
from .views import PaymentViewSet, ReceiptViewSet

router = DefaultRouter()
router.register(r"payments", PaymentViewSet, basename="payments")
router.register(r"receipts", ReceiptViewSet, basename="receipts")
urlpatterns = router.urls