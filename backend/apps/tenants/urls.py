from rest_framework.routers import DefaultRouter
from .views import HostelViewSet, PlanViewSet, SubscriptionViewSet

router = DefaultRouter()
router.register(r"plans", PlanViewSet, basename="plans")
router.register(r"hostels", HostelViewSet, basename="hostels")
router.register(r"subscriptions", SubscriptionViewSet, basename="subscriptions")

urlpatterns = router.urls