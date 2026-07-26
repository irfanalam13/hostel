from django.urls import path
from rest_framework.routers import DefaultRouter
from .manage_views import (
    DangerZoneView,
    TeamMemberView,
    TeamView,
    WorkspaceActivityView,
    WorkspaceOverviewView,
    WorkspaceRenameView,
    WorkspaceSettingsExportView,
    WorkspaceSettingsNamespaceView,
)
from .views import (
    HostelViewSet,
    PlanViewSet,
    SubscriptionViewSet,
    TestimonialViewSet,
    WorkspaceViewSet,
)

router = DefaultRouter()
router.register(r"plans", PlanViewSet, basename="plans")
router.register(r"testimonials", TestimonialViewSet, basename="testimonials")
router.register(r"hostels", HostelViewSet, basename="hostels")
router.register(r"workspaces", WorkspaceViewSet, basename="workspaces")
router.register(r"subscriptions", SubscriptionViewSet, basename="subscriptions")

# Workspace Management console (Prompt 04) — operates on request.hostel.
urlpatterns = [
    path("manage/overview/", WorkspaceOverviewView.as_view(), name="workspace_overview"),
    path("manage/settings/<str:namespace>/", WorkspaceSettingsNamespaceView.as_view(),
         name="workspace_settings_namespace"),
    path("manage/rename/", WorkspaceRenameView.as_view(), name="workspace_rename"),
    path("manage/activity/", WorkspaceActivityView.as_view(), name="workspace_activity"),
    path("manage/team/", TeamView.as_view(), name="workspace_team"),
    path("manage/team/<int:user_id>/", TeamMemberView.as_view(), name="workspace_team_member"),
    path("manage/danger/<str:action>/", DangerZoneView.as_view(), name="workspace_danger"),
    path("manage/export/", WorkspaceSettingsExportView.as_view(), name="workspace_export"),
]

urlpatterns += router.urls