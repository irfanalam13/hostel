from rest_framework.routers import DefaultRouter
from .views import RoomViewSet, BedViewSet

router = DefaultRouter()
router.register(r"rooms", RoomViewSet, basename="rooms")
router.register(r"beds", BedViewSet, basename="beds")

urlpatterns = router.urls