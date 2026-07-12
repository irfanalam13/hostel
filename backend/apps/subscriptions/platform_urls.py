"""Super-Admin platform API routes — mounted at ``/api/platform/``."""
from django.urls import path
from rest_framework.routers import DefaultRouter

from .platform_views import (
    AnalyticsView,
    FeatureCategoryViewSet,
    FeatureDependencyViewSet,
    FeatureOverrideViewSet,
    FeatureViewSet,
    LimitDefinitionViewSet,
    LimitOverrideViewSet,
    PlanViewSet,
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
    path("analytics/", AnalyticsView.as_view(), name="platform-analytics"),
    path("subscriptions/", PlatformSubscriptionsView.as_view(), name="platform-subscriptions"),
    path(
        "subscriptions/<uuid:hostel_id>/history/",
        SubscriptionHistoryView.as_view(),
        name="platform-subscription-history",
    ),
    *router.urls,
]
