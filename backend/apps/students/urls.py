from rest_framework.routers import DefaultRouter
from .views import StudentViewSet, StudentDocumentViewSet

router = DefaultRouter()
router.register(r"students", StudentViewSet, basename="students")
router.register(r"student-documents", StudentDocumentViewSet, basename="student_docs")
urlpatterns = router.urls