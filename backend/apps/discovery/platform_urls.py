from django.urls import path

from .views import PlatformFlaggedQueueView, PlatformReviewRemoveView, PlatformReviewUnflagView

urlpatterns = [
    path("flagged/", PlatformFlaggedQueueView.as_view(), name="discovery-platform-flagged"),
    path("reviews/<uuid:pk>/unflag/", PlatformReviewUnflagView.as_view(), name="discovery-platform-unflag"),
    path("reviews/<uuid:pk>/remove/", PlatformReviewRemoveView.as_view(), name="discovery-platform-remove"),
]
