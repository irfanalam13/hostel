"""PWA analytics, mounted at /api/analytics/.

    POST /api/analytics/collect/   batch-ingest telemetry events
    GET  /api/analytics/report/    aggregated metrics (owner/manager), ?days=30
"""
from django.urls import path

from .views import CollectView, ReportView

urlpatterns = [
    path("collect/", CollectView.as_view(), name="analytics-collect"),
    path("report/", ReportView.as_view(), name="analytics-report"),
]
