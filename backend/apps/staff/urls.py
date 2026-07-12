from rest_framework.routers import DefaultRouter

from .views import (
    DepartmentViewSet,
    DesignationViewSet,
    RoleViewSet,
    StaffDocumentViewSet,
    StaffViewSet,
)

router = DefaultRouter()
router.register(r"roles", RoleViewSet, basename="staff-roles")
router.register(r"departments", DepartmentViewSet, basename="staff-departments")
router.register(r"designations", DesignationViewSet, basename="staff-designations")
router.register(r"documents", StaffDocumentViewSet, basename="staff-documents")
# Empty prefix last so the specific collections above take precedence.
router.register(r"", StaffViewSet, basename="staff")

urlpatterns = router.urls
