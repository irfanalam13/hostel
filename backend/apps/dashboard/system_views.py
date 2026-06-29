"""System / PWA status dashboard.

Two endpoints:

* ``POST /api/dashboard/heartbeat/``      every client pings this so presence,
                                          installed-state and SW/app versions
                                          stay current. Any hostel member.
* ``GET  /api/dashboard/system-status/``  tenant-wide status aggregates for the
                                          dashboard. Owner/manager only.

"Online" is derived from ``UserPresence.last_seen`` within ``ONLINE_WINDOW``, so
no background job is required.
"""
from datetime import timedelta

from django.conf import settings
from django.db import connections
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserHostel
from apps.common.permissions import HasHostelContext, IsOwnerOrManager
from apps.notifications.models import (
    DeliveryStatus,
    Notification,
    NotificationDelivery,
    NotificationStatus,
    PushSubscription,
)
from apps.notifications.services import push_enabled

from .models import UserPresence

# A client is considered "online" if it has pinged within this window.
ONLINE_WINDOW = timedelta(seconds=120)


class HeartbeatView(APIView):
    """Record the calling client's presence + PWA state."""

    permission_classes = [IsAuthenticated, HasHostelContext]

    def post(self, request):
        data = request.data or {}
        UserPresence.objects.update_or_create(
            user=request.user,
            hostel=request.hostel,
            defaults={
                "is_installed": bool(data.get("installed", False)),
                "sw_version": str(data.get("sw_version", ""))[:40],
                "app_version": str(data.get("app_version", ""))[:40],
                "user_agent": request.META.get("HTTP_USER_AGENT", "")[:300],
                # last_seen is auto_now → refreshed on every save.
            },
        )
        return Response({"ok": True})


def _health() -> dict:
    """Cheap readiness summary for the status panel (db + cache + celery)."""
    # Database
    db_ok = True
    try:
        with connections["default"].cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception:  # noqa: BLE001
        db_ok = False

    # Redis cache / broker
    cache_ok = True
    try:
        import redis

        redis.Redis.from_url(
            getattr(settings, "REDIS_URL", "") or getattr(settings, "CELERY_BROKER_URL", ""),
            socket_connect_timeout=1,
            socket_timeout=1,
        ).ping()
    except Exception:  # noqa: BLE001
        cache_ok = False

    # Celery workers
    celery_ok = False
    try:
        from config.celery import app as celery_app

        replies = celery_app.control.ping(timeout=1.0)
        celery_ok = bool(replies)
    except Exception:  # noqa: BLE001
        celery_ok = False

    overall = "ok" if (db_ok and cache_ok) else "degraded"
    return {
        "status": overall,
        "database": db_ok,
        "cache": cache_ok,
        "celery": celery_ok,
    }


class SystemStatusView(APIView):
    """Tenant-wide system + PWA status for the dashboard."""

    permission_classes = [HasHostelContext, IsOwnerOrManager]

    def get(self, request):
        hostel = request.hostel
        now = timezone.now()
        cutoff = now - ONLINE_WINDOW

        members = UserHostel.objects.filter(hostel=hostel, is_active=True).count()
        online_qs = UserPresence.objects.filter(hostel=hostel, last_seen__gte=cutoff)
        online = online_qs.count()
        installed_active = online_qs.filter(is_installed=True).count()
        offline = max(members - online, 0)

        push_subscribers = PushSubscription.objects.filter(hostel=hostel, is_active=True).count()

        deliveries = NotificationDelivery.objects.filter(recipient__notification__hostel=hostel)
        pending_sync = deliveries.filter(status=DeliveryStatus.PENDING).count()
        failed_sync = deliveries.filter(status=DeliveryStatus.FAILED).count()
        scheduled = Notification.objects.filter(
            hostel=hostel, status=NotificationStatus.SCHEDULED
        ).count()
        sending = Notification.objects.filter(
            hostel=hostel, status=NotificationStatus.SENDING
        ).count()

        return Response(
            {
                "users": {
                    "members": members,
                    "online": online,
                    "offline": offline,
                    "installed_active": installed_active,
                },
                "pwa": {
                    "push_subscribers": push_subscribers,
                    "notifications_configured": push_enabled(),
                    "app_version": getattr(settings, "APP_VERSION", "unknown"),
                },
                "sync": {
                    "pending": pending_sync,
                    "failed": failed_sync,
                },
                "background_tasks": {
                    "scheduled_notifications": scheduled,
                    "sending_notifications": sending,
                    "pending_deliveries": pending_sync,
                    "total": scheduled + sending + pending_sync,
                },
                "api_health": _health(),
                "server_time": now.isoformat(),
            }
        )
