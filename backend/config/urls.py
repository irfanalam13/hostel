from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from apps.common import health, views as common_views


urlpatterns = [
    # 🏠 Root status / landing page (proves the backend is up; links to docs)
    path("", common_views.index, name="index"),

    path("admin/", admin.site.urls),

    # ❤️ Health checks (unauthenticated, for load balancers / uptime monitors)
    path("health/", health.health, name="health"),
    path("health/database/", health.health_database, name="health-database"),
    path("health/cache/", health.health_cache, name="health-cache"),
    path("health/celery/", health.health_celery, name="health-celery"),
    path("health/storage/", health.health_storage, name="health-storage"),
    path("health/queue/", health.health_queue, name="health-queue"),

    # 📄 API Schema & Docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),

    # 🔐 Auth (ALL auth inside accounts app — cookie-based JWT)
    path("api/auth/", include("apps.accounts.urls")),

    # 🏢 Core Modules
    path("api/tenants/", include("apps.tenants.urls")),
    path("api/rooms/", include("apps.rooms.urls")),
    path("api/admissions/", include("apps.admissions.urls")),
    path("api/students/", include("apps.students.urls")),
    path("api/fees/", include("apps.fees.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
    path("api/reports/", include("apps.reports.urls")),
    path("api/hostel/", include("apps.hostel.urls")),
    path("api/residents/", include("apps.residents.urls")),
    path("api/billing/", include("apps.billing.urls")),
    path("api/attendance/", include("apps.attendance.urls")),
    path("api/operations/", include("apps.operations.urls")),
    path("api/complaints/", include("apps.complaints.urls")),
    path("api/notices/", include("apps.notices.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/push/", include("apps.notifications.push_urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/audit/", include("apps.auditlog.urls")),
    path("api/backups/", include("apps.backups.urls")),
    path("api/exports/", include("apps.exports.urls")),
    path("api/marketing/", include("apps.marketing.urls")),
    path("api/website/", include("apps.website.urls")),
    path("api/domains/", include("apps.domains.urls")),
    path("api/subscriptions/", include("apps.subscriptions.urls")),
    path("api/platform/", include("apps.subscriptions.platform_urls")),
    # 🛡️ Super-Admin security operations (dashboard, rules, kill switch)
    path("api/platform/security/", include("apps.security.urls")),
    # 🛠️ Super-Admin operations governance (announcements, maintenance, incidents, flags)
    path("api/platform/ops/", include("apps.platformops.urls")),
    # Authenticated ops status feed (banners / maintenance / incidents / flags)
    path("api/ops/", include("apps.platformops.status_urls")),
    path("api/staff/", include("apps.staff.urls")),
    path("api/finance/", include("apps.finance.urls")),
    path("api/accounting/", include("apps.accounting.urls")),
    path("api/inventory/", include("apps.inventory.urls")),
    # 🤖 AI assistant gateway (BFF for the ML_hostel microservice)
    path("api/ai/", include("apps.assistant.urls")),
    # 📚 AI knowledge base (RAG documents)
    path("api/ai/knowledge/", include("apps.aiknowledge.urls")),

    # 🛟 Admin disaster-recovery API (admin-only)
    path("api/admin/", include("apps.backups.admin_urls")),
]

# 📊 Prometheus metrics at /metrics (only when PROMETHEUS_ENABLED=True).
# Restrict exposure at the proxy layer — these are for the internal scraper.
if getattr(settings, "PROMETHEUS_ENABLED", False):
    urlpatterns += [path("", include("django_prometheus.urls"))]

# Media
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


