"""Admin disaster-recovery routes, mounted under /api/admin/."""

from django.urls import path

from .admin_api import (
    AdminRestoreView,
    BackupValidateView,
    DRModeView,
    DRStatusView,
)

urlpatterns = [
    path("restore/", AdminRestoreView.as_view(), name="admin-restore"),
    path("dr/status/", DRStatusView.as_view(), name="admin-dr-status"),
    path("dr/mode/", DRModeView.as_view(), name="admin-dr-mode"),
    path("backups/<uuid:pk>/validate/", BackupValidateView.as_view(), name="admin-backup-validate"),
]
