from rest_framework.routers import DefaultRouter
from .views import EntryExitLogViewSet, LeaveRequestViewSet, VisitorLogViewSet

router = DefaultRouter()
router.register(r"entry-exit", EntryExitLogViewSet, basename="entry_exit")
router.register(r"leave-requests", LeaveRequestViewSet, basename="leave_requests")
router.register(r"visitor-logs", VisitorLogViewSet, basename="visitor_logs")

urlpatterns = router.urls
