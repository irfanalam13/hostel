from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    InquiryViewSet,
    MediaViewSet,
    OverviewView,
    PublicInquiryView,
    PublicWebsiteView,
    PublishView,
    SectionViewSet,
    UnpublishView,
    VersionRestoreView,
    VersionsView,
    WebsiteSettingsView,
)

router = DefaultRouter()
router.register(r"sections", SectionViewSet, basename="website_sections")
router.register(r"inquiries", InquiryViewSet, basename="website_inquiries")
router.register(r"media", MediaViewSet, basename="website_media")

urlpatterns = [
    # Public (anonymous, tenant-resolved by the middleware)
    path("public/", PublicWebsiteView.as_view(), name="website_public"),
    path("public/inquiries/", PublicInquiryView.as_view(), name="website_public_inquiry"),

    # Builder (authenticated, RBAC website.*)
    path("settings/", WebsiteSettingsView.as_view(), name="website_settings"),
    path("overview/", OverviewView.as_view(), name="website_overview"),
    path("publish/", PublishView.as_view(), name="website_publish"),
    path("unpublish/", UnpublishView.as_view(), name="website_unpublish"),
    path("versions/", VersionsView.as_view(), name="website_versions"),
    path("versions/<int:number>/restore/", VersionRestoreView.as_view(),
         name="website_version_restore"),
]

urlpatterns += router.urls
