"""System / PWA status dashboard.

Two endpoints:

* ``POST /api/dashboard/heartbeat/``      every client pings this so presence,
                                          installed-state and SW/app versions
                                          stay current. Any hostel member.
* ``GET  /api/dashboard/system-status/``  tenant-wide status aggregates for the
                                          dashboard. Super admin only.

"Online" is derived from ``UserPresence.last_seen`` within ``ONLINE_WINDOW``, so
no background job is required.
"""
import threading
import time
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import UserHostel
from apps.common.permissions import HasHostelContext, IsSuperUser
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


# ---------------------------------------------------------------------------
# API health summary for the status panel.
#
# The naive version pinged Celery workers *synchronously* on every request
# (``control.ping`` is a broadcast over the broker that blocks for its full
# timeout — ~1s — whenever it is called). That made ``/system-status/`` a ~1s
# endpoint even though its DB work is <25ms (Phase 10: the frontend must never
# wait for Celery).
#
# Fix: stale-while-revalidate. The request always returns the last cached
# snapshot instantly; when the snapshot ages past ``_HEALTH_FRESH_TTL`` a
# refresh runs in a daemon thread so no user request ever blocks on a probe.
# ---------------------------------------------------------------------------
_HEALTH_CACHE_KEY = "dashboard:system_health"
# How long a snapshot is considered fresh before a background refresh is kicked.
_HEALTH_FRESH_TTL = getattr(settings, "SYSTEM_HEALTH_TTL", 15)
# Keep the last-known snapshot in cache well past freshness so a probe failure
# or restart still serves something instead of blocking.
_HEALTH_HARD_TTL = 300
# Bounded probe timeouts — the probe runs off the request path, but a hung
# dependency must still not pin a worker thread forever.
_PROBE_TIMEOUT = getattr(settings, "SYSTEM_HEALTH_PROBE_TIMEOUT", 0.5)

_health_refresh_lock = threading.Lock()
_health_refreshing = False


def _probe_health() -> dict:
    """Actively probe db + cache + celery. Runs OFF the request hot path."""
    db_ok = True
    try:
        with connections["default"].cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception:  # noqa: BLE001
        db_ok = False

    cache_ok = True
    try:
        import redis

        redis.Redis.from_url(
            getattr(settings, "REDIS_URL", "") or getattr(settings, "CELERY_BROKER_URL", ""),
            socket_connect_timeout=_PROBE_TIMEOUT,
            socket_timeout=_PROBE_TIMEOUT,
        ).ping()
    except Exception:  # noqa: BLE001
        cache_ok = False

    celery_ok = False
    try:
        from config.celery import app as celery_app

        replies = celery_app.control.ping(timeout=_PROBE_TIMEOUT)
        celery_ok = bool(replies)
    except Exception:  # noqa: BLE001
        celery_ok = False

    overall = "ok" if (db_ok and cache_ok) else "degraded"
    return {
        "status": overall,
        "database": db_ok,
        "cache": cache_ok,
        "celery": celery_ok,
        "checked_at": time.time(),
    }


def _refresh_health_async() -> None:
    """Kick a single background refresh of the health snapshot (no-op if one is
    already running in this process)."""
    global _health_refreshing
    with _health_refresh_lock:
        if _health_refreshing:
            return
        _health_refreshing = True

    def _run():
        global _health_refreshing
        try:
            snap = _probe_health()
            cache.set(_HEALTH_CACHE_KEY, snap, _HEALTH_HARD_TTL)
        finally:
            with _health_refresh_lock:
                _health_refreshing = False

    threading.Thread(target=_run, daemon=True, name="system-health-refresh").start()


def _health() -> dict:
    """Return the cached health snapshot instantly; refresh in the background
    when it is missing or stale. NO request ever blocks on a Celery/Redis probe:

    * cache miss (cold process / expired) → return an optimistic "checking"
      snapshot and kick a background refresh; the next request gets real data
      (a few ms of probe run off the request path);
    * fresh → return it as-is;
    * stale → return it and kick a background refresh.
    """
    snapshot = cache.get(_HEALTH_CACHE_KEY)
    if snapshot is None:
        # Seed a placeholder so concurrent requests don't each kick a refresh,
        # then trigger the single background probe.
        placeholder = {
            "status": "checking",
            "database": None,
            "cache": None,
            "celery": None,
            "checked_at": time.time(),
        }
        cache.set(_HEALTH_CACHE_KEY, placeholder, _HEALTH_HARD_TTL)
        _refresh_health_async()
        return placeholder

    if time.time() - snapshot.get("checked_at", 0) > _HEALTH_FRESH_TTL:
        _refresh_health_async()
    return snapshot


class SystemStatusView(APIView):
    """Tenant-wide system + PWA status for the dashboard (super admin only).

    Infrastructure health (db/cache/celery), push-subscriber counts and sync-job
    backlogs are platform-operator signals, not hostel business, so this is
    restricted to super admins and surfaced only on the platform dashboard."""

    permission_classes = [HasHostelContext, IsSuperUser]

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
