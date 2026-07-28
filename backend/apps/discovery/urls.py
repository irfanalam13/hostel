from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DirectoryHostelViewSet,
    ModerationApproveView,
    ModerationPendingView,
    ModerationRejectView,
    ReviewViewSet,
)

router = DefaultRouter()
router.register(r"hostels", DirectoryHostelViewSet, basename="discovery-hostels")
router.register(r"reviews", ReviewViewSet, basename="discovery-reviews")

urlpatterns = [
    path("moderation/pending/", ModerationPendingView.as_view(), name="discovery-moderation-pending"),
    path("moderation/reviews/<uuid:pk>/approve/", ModerationApproveView.as_view(),
         name="discovery-moderation-approve"),
    path("moderation/reviews/<uuid:pk>/reject/", ModerationRejectView.as_view(),
         name="discovery-moderation-reject"),
]
urlpatterns += router.urls
