"""Authenticated ops status feed (mounted at /api/ops/)."""
from django.urls import path

from .views import OpsStatusView

urlpatterns = [
    path("status/", OpsStatusView.as_view(), name="ops_status"),
]
