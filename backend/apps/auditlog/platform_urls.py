"""Super-Admin audit trail routes — mounted at ``/api/platform/audit/``."""
from rest_framework.routers import DefaultRouter

from .platform_views import PlatformAuditEventViewSet

app_name = "platform_audit"

router = DefaultRouter()
router.register("events", PlatformAuditEventViewSet, basename="platform-audit-event")

urlpatterns = router.urls
