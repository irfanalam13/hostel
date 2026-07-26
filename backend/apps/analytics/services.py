"""Analytics ingestion + reporting.

parse_user_agent() classifies device/browser without any third-party dependency.
build_report() turns raw events into the ten tracked PWA metrics over a window.
"""
from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import AnalyticsEvent, Browser, DeviceType, EventType


# --------------------------------------------------------------------------- #
# User-Agent classification
# --------------------------------------------------------------------------- #
def parse_user_agent(ua: str) -> tuple[str, str, str]:
    """Return (device_type, browser, platform) from a User-Agent string."""
    ua = ua or ""
    low = ua.lower()

    # Device
    if "ipad" in low or ("tablet" in low and "mobile" not in low):
        device = DeviceType.TABLET
    elif "mobi" in low or "iphone" in low or "android" in low and "mobile" in low:
        device = DeviceType.MOBILE
    elif not ua:
        device = DeviceType.UNKNOWN
    else:
        device = DeviceType.DESKTOP

    # Browser (order matters: Edge/Opera/Samsung masquerade as Chrome)
    if "edg/" in low or "edga/" in low or "edgios/" in low:
        browser = Browser.EDGE
    elif "opr/" in low or "opera" in low:
        browser = Browser.OPERA
    elif "samsungbrowser" in low:
        browser = Browser.SAMSUNG
    elif "firefox/" in low or "fxios" in low:
        browser = Browser.FIREFOX
    elif "chrome/" in low or "crios" in low or "chromium" in low:
        browser = Browser.CHROME
    elif "safari/" in low and "version/" in low:
        browser = Browser.SAFARI
    else:
        browser = Browser.OTHER

    # Platform
    if "windows" in low:
        platform = "Windows"
    elif "android" in low:
        platform = "Android"
    elif "iphone" in low or "ipad" in low or "ipod" in low:
        platform = "iOS"
    elif "mac os" in low or "macintosh" in low:
        platform = "macOS"
    elif "linux" in low:
        platform = "Linux"
    else:
        platform = ""

    return device, browser, platform


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def _safe_rate(numerator: float, denominator: float) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def build_report(hostel, days: int = 30) -> dict:
    since = timezone.now() - timedelta(days=days)
    qs = AnalyticsEvent.objects.filter(hostel=hostel, created_at__gte=since)

    # Counts per event type.
    counts = {
        row["event_type"]: row["n"]
        for row in qs.values("event_type").annotate(n=Count("id"))
    }
    c = lambda t: counts.get(t, 0)  # noqa: E731

    # Value sums for aggregated counters.
    def vsum(event_type) -> float:
        return qs.filter(event_type=event_type).aggregate(s=Sum("value"))["s"] or 0

    cache_hits = vsum(EventType.CACHE_HIT)
    cache_misses = vsum(EventType.CACHE_MISS)
    sync_ok = vsum(EventType.SYNC_SUCCESS)
    sync_fail = vsum(EventType.SYNC_FAILURE)
    offline_seconds = vsum(EventType.OFFLINE_SESSION)

    prompts = c(EventType.INSTALL_PROMPT)
    installed = c(EventType.INSTALLED)
    update_available = c(EventType.UPDATE_AVAILABLE)
    update_applied = c(EventType.UPDATE_APPLIED)
    push_received = c(EventType.PUSH_RECEIVED)
    push_open = c(EventType.PUSH_OPEN)

    # Feature adoption (top features by usage + distinct users).
    features = list(
        qs.filter(event_type=EventType.FEATURE_USED)
        .values("name")
        .annotate(uses=Count("id"), users=Count("user", distinct=True))
        .order_by("-uses")[:12]
    )

    # Device + browser breakdowns.
    devices = {
        row["device_type"]: row["n"]
        for row in qs.values("device_type").annotate(n=Count("id"))
    }
    browsers = {
        row["browser"]: row["n"]
        for row in qs.values("browser").annotate(n=Count("id"))
    }

    # Error frequency per day (last `days`).
    errors_qs = qs.filter(event_type=EventType.ERROR)
    error_daily = {}
    for row in (
        errors_qs.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(n=Count("id"))
        .order_by("day")
    ):
        error_daily[str(row["day"])] = row["n"]

    return {
        "window_days": days,
        "total_events": sum(counts.values()),
        "install": {
            "prompts": prompts,
            "accepted": c(EventType.INSTALL_ACCEPTED),
            "dismissed": c(EventType.INSTALL_DISMISSED),
            "installed": installed,
            "rate": _safe_rate(installed, prompts),
        },
        "update": {
            "available": update_available,
            "applied": update_applied,
            "rate": _safe_rate(update_applied, update_available),
        },
        "offline_usage": {
            "sessions": c(EventType.OFFLINE_SESSION),
            "total_seconds": round(offline_seconds),
            "users": qs.filter(event_type=EventType.OFFLINE_SESSION)
            .values("user")
            .distinct()
            .count(),
        },
        "feature_adoption": features,
        "push": {
            "received": push_received,
            "opened": push_open,
            "open_rate": _safe_rate(push_open, push_received),
        },
        "cache": {
            "hits": round(cache_hits),
            "misses": round(cache_misses),
            "efficiency": _safe_rate(cache_hits, cache_hits + cache_misses),
        },
        "sync": {
            "success": round(sync_ok),
            "failure": round(sync_fail),
            "success_rate": _safe_rate(sync_ok, sync_ok + sync_fail),
        },
        "device_types": devices,
        "browsers": browsers,
        "errors": {
            "total": errors_qs.count(),
            "daily": error_daily,
        },
    }
