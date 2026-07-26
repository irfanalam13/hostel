from rest_framework.routers import DefaultRouter
from .views import BlockViewSet, FloorViewSet, RoomViewSet, BedViewSet, BedAssignmentViewSet

router = DefaultRouter()
router.register(r"blocks", BlockViewSet, basename="blocks")
router.register(r"floors", FloorViewSet, basename="floors")
router.register(r"rooms", RoomViewSet, basename="rooms")
router.register(r"beds", BedViewSet, basename="beds")
router.register(r"bed-assignments", BedAssignmentViewSet, basename="bed_assignments")
urlpatterns = router.urls
