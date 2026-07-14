"""Super-Admin operations-governance routes (mounted at /api/platform/ops/)."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .admin_api import (
    AnnouncementViewSet,
    FeatureFlagOverrideViewSet,
    FeatureFlagViewSet,
    HostelLookupView,
    IncidentViewSet,
    MaintenanceWindowViewSet,
    UserLookupView,
)

router = DefaultRouter()
router.register(r"announcements", AnnouncementViewSet, basename="ops_announcement")
router.register(r"maintenance", MaintenanceWindowViewSet, basename="ops_maintenance")
router.register(r"incidents", IncidentViewSet, basename="ops_incident")
router.register(r"feature-flags", FeatureFlagViewSet, basename="ops_feature_flag")
router.register(r"overrides", FeatureFlagOverrideViewSet, basename="ops_flag_override")

urlpatterns = router.urls + [
    path("lookup/hostels/", HostelLookupView.as_view(), name="ops_lookup_hostels"),
    path("lookup/users/", UserLookupView.as_view(), name="ops_lookup_users"),
]
