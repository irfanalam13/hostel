from rest_framework.routers import DefaultRouter
from .views import ResidentViewSet, StayViewSet

router = DefaultRouter()
router.register(r"stays", StayViewSet, basename="stays")
router.register(r"", ResidentViewSet, basename="residents")
urlpatterns = router.urls
