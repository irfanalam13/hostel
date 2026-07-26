from rest_framework.routers import DefaultRouter

from .views import FaqViewSet, LeadViewSet, LegalDocumentViewSet, SitePageViewSet

router = DefaultRouter()
router.register(r"faqs", FaqViewSet, basename="faqs")
router.register(r"legal", LegalDocumentViewSet, basename="legal")
router.register(r"pages", SitePageViewSet, basename="pages")
router.register(r"leads", LeadViewSet, basename="leads")

urlpatterns = router.urls
