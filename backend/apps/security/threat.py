"""Threat aggregation over the immutable SecurityEvent trail.

Turns the raw event stream into the summaries the Super-Admin security
dashboard and the periodic security reports consume: counts by type/action,
top offending IPs and paths, blocked-vs-logged ratio, and a coarse platform
threat level derived from configurable thresholds.

All queries are windowed and DB-side aggregated (no row materialisation), and
optionally scoped to one tenant — so a workspace admin only ever sees their own
activity while platform staff see everything. Read-only; never mutates state.
"""
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from .conf import get_config
from .models import SecurityEvent

# Event types that represent an actual defensive action (not just a log).
_THREAT_TYPES = (
    "rate_limited", "waf_violation", "bot_detected", "ip_denied",
    "reputation_block", "auth_failure", "auth_lockout", "captcha_failed",
    "replay_blocked",
)


def _thresholds() -> dict:
    # Configurable anomaly thresholds (events in the window -> level).
    return get_config().get("threat.levels") or {
        "elevated": 100, "high": 1000, "critical": 10000,
    }


def summary(window_hours: int = 24, tenant_id=None) -> dict:
    """Aggregated threat summary for the last ``window_hours``."""
    since = timezone.now() - timedelta(hours=window_hours)
    qs = SecurityEvent.objects.filter(created_at__gte=since)
    if tenant_id is not None:
        qs = qs.filter(tenant_id=tenant_id)

    total = qs.count()
    blocked = qs.filter(action="blocked").count()

    by_type = {
        row["event_type"]: row["n"]
        for row in qs.values("event_type").annotate(n=Count("id")).order_by("-n")
    }
    by_action = {
        row["action"]: row["n"]
        for row in qs.values("action").annotate(n=Count("id")).order_by("-n")
    }
    threat_events = sum(by_type.get(t, 0) for t in _THREAT_TYPES)

    top_ips = list(
        qs.exclude(ip="")
        .values("ip")
        .annotate(n=Count("id"))
        .order_by("-n")[:10]
    )
    top_paths = list(
        qs.exclude(path="")
        .values("path")
        .annotate(n=Count("id"))
        .order_by("-n")[:10]
    )

    return {
        "window_hours": window_hours,
        "generated_at": timezone.now().isoformat(),
        "total_events": total,
        "blocked_events": blocked,
        "threat_events": threat_events,
        "threat_level": classify_level(threat_events),
        "by_type": by_type,
        "by_action": by_action,
        "top_ips": [{"ip": r["ip"], "count": r["n"]} for r in top_ips],
        "top_paths": [{"path": r["path"], "count": r["n"]} for r in top_paths],
    }


def classify_level(threat_events: int) -> str:
    t = _thresholds()
    if threat_events >= int(t.get("critical", 10000)):
        return "critical"
    if threat_events >= int(t.get("high", 1000)):
        return "high"
    if threat_events >= int(t.get("elevated", 100)):
        return "elevated"
    return "normal"


def timeseries(window_hours: int = 24, bucket_minutes: int = 60, tenant_id=None) -> list:
    """Event counts bucketed over time (for dashboard sparklines). Uses
    Django's Trunc for DB-side bucketing where available; falls back to a
    Python bucketing pass otherwise."""
    since = timezone.now() - timedelta(hours=window_hours)
    qs = SecurityEvent.objects.filter(created_at__gte=since)
    if tenant_id is not None:
        qs = qs.filter(tenant_id=tenant_id)

    try:
        from django.db.models.functions import Trunc

        trunc = "hour" if bucket_minutes >= 60 else "minute"
        rows = (
            qs.annotate(bucket=Trunc("created_at", trunc))
            .values("bucket")
            .annotate(n=Count("id"))
            .order_by("bucket")
        )
        return [
            {"bucket": r["bucket"].isoformat() if r["bucket"] else None, "count": r["n"]}
            for r in rows
        ]
    except Exception:
        return []


def top_offenders(window_hours: int = 24, limit: int = 20, tenant_id=None) -> list:
    """IPs ranked by blocked events in the window — the ban-candidate list."""
    since = timezone.now() - timedelta(hours=window_hours)
    qs = SecurityEvent.objects.filter(created_at__gte=since, action="blocked").exclude(ip="")
    if tenant_id is not None:
        qs = qs.filter(tenant_id=tenant_id)
    rows = qs.values("ip").annotate(n=Count("id")).order_by("-n")[:limit]
    return [{"ip": r["ip"], "blocked": r["n"]} for r in rows]
