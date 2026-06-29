"""Notification inbox + staff send/history, mounted at /api/notifications/.

    GET  /api/notifications/                 inbox (this user, active hostel)
    GET  /api/notifications/unread_count/    { unread: N }
    POST /api/notifications/{recipient_id}/read/
    POST /api/notifications/read_all/
    POST /api/notifications/send/            (staff) create + dispatch/schedule
    GET  /api/notifications/sent/            (staff) history with delivery stats
"""
from rest_framework.routers import DefaultRouter

from .views import NotificationViewSet

router = DefaultRouter()
router.register(r"", NotificationViewSet, basename="notifications")

urlpatterns = router.urls
