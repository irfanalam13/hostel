"""Structured security event pipeline.

Every security decision produces:

1. one structured JSON log line on the ``apps.security.events`` logger —
   request id, tenant, user, ip, ua, country/ASN (when Cloudflare provides
   them), decision, threat score. Ships to any log aggregator as-is.
2. optionally an immutable ``SecurityEvent`` row — written by a Celery
   worker (mirroring AUDIT_LOG_ASYNC) with an inline fallback, so the hot
   path never waits on the INSERT and a broker outage never loses the event.

Both sinks are individually configurable (``events.log`` /
``events.persist`` / ``events.persist_async``) and hot-reloadable.
"""
import json
import logging

from .conf import get_config

event_logger = logging.getLogger("apps.security.events")
logger = logging.getLogger("apps.security")


def _request_context(request) -> dict:
    if request is None:
        return {}
    user = getattr(request, "user", None)
    tenant = getattr(request, "tenant", None)
    return {
        "request_id": getattr(request, "request_id", ""),
        "method": getattr(request, "method", ""),
        "path": getattr(request, "path", "")[:255],
        "user_agent": request.META.get("HTTP_USER_AGENT", "")[:255],
        "ip": getattr(request, "client_ip", request.META.get("REMOTE_ADDR", "")),
        # Cloudflare enrichment headers (present only behind CF).
        "country": request.META.get("HTTP_CF_IPCOUNTRY", "")[:8],
        "asn": request.META.get("HTTP_CF_ASN", "")[:16],
        "tenant_id": getattr(tenant, "pk", None),
        "tenant": getattr(tenant, "slug", "") or "",
        "user_id": getattr(user, "pk", None)
        if getattr(user, "is_authenticated", False) else None,
    }


def record(event_type: str, action: str, request=None, threat_score: int = 0,
           dedupe: str | None = None, dedupe_ttl: int = 60, **detail) -> None:
    """Emit one security event. Never raises — a broken event pipeline must
    not break request handling.

    ``dedupe``: optional key; identical events within ``dedupe_ttl`` seconds
    are suppressed (keeps a scripted flood from writing one row per request —
    the rate limiter, not the event log, absorbs the volume).
    """
    try:
        if dedupe:
            from django.core.cache import cache

            try:
                if not cache.add(f"sec:evt:dedupe:{event_type}:{dedupe}", 1,
                                 timeout=dedupe_ttl):
                    return
            except Exception:
                pass  # cache outage — emit rather than drop

        config = get_config()
        events_conf = config.get("events") or {}
        payload = {
            "event": event_type,
            "action": action,
            "threat_score": threat_score,
            **_request_context(request),
            "detail": detail or {},
        }

        # Prometheus: count every event (single choke point). No-op when
        # prometheus_client isn't installed.
        try:
            from . import metrics

            metrics.emit(event_type, action, detail)
        except Exception:
            pass

        if events_conf.get("log", True):
            event_logger.info(json.dumps(payload, default=str, separators=(",", ":")))

        if events_conf.get("persist", True):
            _persist(payload, bool(events_conf.get("persist_async", True)))
    except Exception:  # pragma: no cover — belt and braces
        logger.warning("security event emission failed", exc_info=True)


def _persist(payload: dict, use_async: bool) -> None:
    if use_async:
        try:
            from .tasks import persist_security_event

            # retry=False: this runs inside the request. If the broker is
            # unreachable/misconfigured, fail immediately and fall through to the
            # inline write — never retry the broker connection, which would block
            # the request for seconds (and can 502 it).
            persist_security_event.apply_async((payload,), retry=False)
            return
        except Exception:
            pass  # broker down — fall through to the inline write
    persist_now(payload)


def persist_now(payload: dict) -> None:
    try:
        from .models import SecurityEvent

        SecurityEvent.objects.create(
            event_type=payload.get("event", "")[:32],
            action=payload.get("action", "")[:16],
            ip=payload.get("ip", "")[:64],
            method=payload.get("method", "")[:10],
            path=payload.get("path", "")[:255],
            user_agent=payload.get("user_agent", "")[:255],
            request_id=payload.get("request_id", "")[:64],
            country=payload.get("country", "")[:8],
            asn=payload.get("asn", "")[:16],
            threat_score=int(payload.get("threat_score") or 0),
            tenant_id=payload.get("tenant_id"),
            user_id=payload.get("user_id"),
            detail=payload.get("detail") or {},
        )
    except Exception:
        logger.warning("security event persistence failed", exc_info=True)
