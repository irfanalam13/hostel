"""Super-Admin platform API routes — mounted at ``/api/platform/``."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .platform_account_views import PlatformAccountsView
from .platform_hostel_views import (
    PlatformHostelDetailView,
    PlatformHostelRoomsView,
    PlatformHostelStaffView,
    PlatformHostelStudentDuesView,
    PlatformHostelStudentsView,
)
from .platform_views import (
    AnalyticsView,
    FeatureCategoryViewSet,
    FeatureDependencyViewSet,
    FeatureOverrideViewSet,
    FeatureViewSet,
    LimitDefinitionViewSet,
    LimitOverrideViewSet,
    PlanViewSet,
    PlatformHostelsOverviewView,
    PlatformSubscriptionsView,
    SubscriptionHistoryView,
)

app_name = "platform"

router = DefaultRouter()
router.register("plans", PlanViewSet, basename="platform-plan")
router.register("features", FeatureViewSet, basename="platform-feature")
router.register("feature-categories", FeatureCategoryViewSet, basename="platform-feature-category")
router.register("feature-dependencies", FeatureDependencyViewSet, basename="platform-feature-dependency")
router.register("limit-definitions", LimitDefinitionViewSet, basename="platform-limit-definition")
router.register("feature-overrides", FeatureOverrideViewSet, basename="platform-feature-override")
router.register("limit-overrides", LimitOverrideViewSet, basename="platform-limit-override")

urlpatterns = [
    path("accounts/", PlatformAccountsView.as_view(), name="platform-accounts"),
    path("analytics/", AnalyticsView.as_view(), name="platform-analytics"),
    path("hostels/overview/", PlatformHostelsOverviewView.as_view(), name="platform-hostels-overview"),
    path("hostels/<uuid:id>/", PlatformHostelDetailView.as_view(), name="platform-hostel-detail"),
    path("hostels/<uuid:id>/students/", PlatformHostelStudentsView.as_view(), name="platform-hostel-students"),
    path(
        "hostels/<uuid:id>/students/<uuid:student_id>/dues/",
        PlatformHostelStudentDuesView.as_view(),
        name="platform-hostel-student-dues",
    ),
    path("hostels/<uuid:id>/staff/", PlatformHostelStaffView.as_view(), name="platform-hostel-staff"),
    path("hostels/<uuid:id>/rooms/", PlatformHostelRoomsView.as_view(), name="platform-hostel-rooms"),
    path("subscriptions/", PlatformSubscriptionsView.as_view(), name="platform-subscriptions"),
    path(
        "subscriptions/<uuid:hostel_id>/history/",
        SubscriptionHistoryView.as_view(),
        name="platform-subscription-history",
    ),
    *router.urls,
]
