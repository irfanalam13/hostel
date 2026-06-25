from rest_framework.routers import DefaultRouter
from .views import AdmissionRequestViewSet, PublicAdmissionRequestViewSet

router = DefaultRouter()
router.register(r"requests", AdmissionRequestViewSet, basename="admission_requests")
router.register(r"public-requests", PublicAdmissionRequestViewSet, basename="public_admission_requests")

urlpatterns = router.urls
