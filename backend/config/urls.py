from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common import health

urlpatterns = [
    path("admin/", admin.site.urls),

    # ❤️ Health checks (unauthenticated, for load balancers / uptime monitors)
    path("health/", health.health, name="health"),
    path("health/database/", health.health_database, name="health-database"),
    path("health/cache/", health.health_cache, name="health-cache"),
    path("health/celery/", health.health_celery, name="health-celery"),

    # 📄 API Schema & Docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),

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
    path("api/audit/", include("apps.auditlog.urls")),
    path("api/backups/", include("apps.backups.urls")),
    path("api/exports/", include("apps.exports.urls")),

    # 🛟 Admin disaster-recovery API (admin-only)
    path("api/admin/", include("apps.backups.admin_urls")),
]

# Media
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


