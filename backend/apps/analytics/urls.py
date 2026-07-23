"""PWA analytics, mounted at /api/analytics/.

    POST /api/analytics/collect/   batch-ingest telemetry events
    GET  /api/analytics/report/    aggregated metrics (owner/manager), ?days=30
    GET  /api/analytics/trends/    rollup-backed trends, ?days=90&granularity=day|week|month
"""
from django.urls import path

from .views import CollectView, ReportView, TrendsView

urlpatterns = [
    path("collect/", CollectView.as_view(), name="analytics-collect"),
    path("report/", ReportView.as_view(), name="analytics-report"),
    path("trends/", TrendsView.as_view(), name="analytics-trends"),
]
