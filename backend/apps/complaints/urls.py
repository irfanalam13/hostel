from rest_framework.routers import DefaultRouter
from .views import ComplaintAttachmentViewSet, ComplaintCommentViewSet, ComplaintViewSet

router = DefaultRouter()
router.register(r"tickets", ComplaintViewSet, basename="complaints")
router.register(r"comments", ComplaintCommentViewSet, basename="complaint_comments")
router.register(r"attachments", ComplaintAttachmentViewSet, basename="complaint_attachments")

urlpatterns = router.urls
