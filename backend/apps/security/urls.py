"""Super-Admin security ops routes — mounted at /api/platform/security/."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .admin_api import (
    IPRuleViewSet,
    KillSwitchView,
    ReputationClearView,
    ResolvedConfigView,
    SecurityEventListView,
    SecurityReportView,
    SecuritySettingViewSet,
    SecuritySummaryView,
    TopOffendersView,
)

router = DefaultRouter()
router.register("ip-rules", IPRuleViewSet, basename="security-ip-rule")
router.register("settings", SecuritySettingViewSet, basename="security-setting")

urlpatterns = [
    path("summary/", SecuritySummaryView.as_view(), name="security-summary"),
    path("events/", SecurityEventListView.as_view(), name="security-events"),
    path("offenders/", TopOffendersView.as_view(), name="security-offenders"),
    path("config/", ResolvedConfigView.as_view(), name="security-config"),
    path("reputation/clear/", ReputationClearView.as_view(), name="security-reputation-clear"),
    path("report/", SecurityReportView.as_view(), name="security-report"),
    path("kill-switch/", KillSwitchView.as_view(), name="security-kill-switch"),
    *router.urls,
]
