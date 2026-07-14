from rest_framework.routers import DefaultRouter

from .views import KnowledgeDocumentViewSet

router = DefaultRouter()
router.register(r"documents", KnowledgeDocumentViewSet, basename="ai-knowledge-documents")

urlpatterns = router.urls
