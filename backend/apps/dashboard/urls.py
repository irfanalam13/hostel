from django.urls import path

from .system_views import HeartbeatView, SystemStatusView
from .views import OwnerDashboardView

urlpatterns = [
    path("owner/", OwnerDashboardView.as_view()),
    path("heartbeat/", HeartbeatView.as_view(), name="dashboard-heartbeat"),
    path("system-status/", SystemStatusView.as_view(), name="dashboard-system-status"),
]
