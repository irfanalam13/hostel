"""Central audit-logging helper.

Use ``record_event`` from views/services to capture security-relevant actions
(logins, payments, vacates, exports, backups). Failures are swallowed so audit
logging can never break a request.

Every event is linked into an append-only SHA-256 hash chain (see
``apps.auditlog.hashing`` / ``models.AuditEvent.create_chained``) so the trail
is tamper-evident. Records are immutable — never update or delete them outside
the retention/archiving path.
"""
from django.utils import timezone

from .models import AuditEvent

# HTTP method -> AuditEvent.Action for generic write logging
METHOD_ACTION = {
    "POST": AuditEvent.Action.CREATE,
    "PUT": AuditEvent.Action.UPDATE,
    "PATCH": AuditEvent.Action.UPDATE,
    "DELETE": AuditEvent.Action.DELETE,
}


def _resolve_actor(actor, request):
    if actor is not None:
        return actor
    user = getattr(request, "user", None) if request is not None else None
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    return None


def client_ip(request):
    """Best-effort real client IP.

    Behind a proxy/load-balancer the connecting address is the proxy, so prefer
    the first hop in X-Forwarded-For (set by trusted infra) and fall back to
    REMOTE_ADDR. We deliberately take only the left-most entry and don't trust
    the rest of the chain for anything security-critical.
    """
    if request is None:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()[:64] or None
    return request.META.get("REMOTE_ADDR")


def _clean_changes(changes):
    """Normalize an old/new-value diff to {"old": ..., "new": ...} or None."""
    if not changes:
        return None
    if isinstance(changes, dict) and ("old" in changes or "new" in changes):
        return {"old": changes.get("old"), "new": changes.get("new")}
    return {"new": changes}


def record_event(
    request=None,
    *,
    action,
    actor=None,
    hostel=None,
    entity_type="",
    entity_id="",
    message="",
    reason="",
    changes=None,
    result=AuditEvent.Result.SUCCESS,
    status_code=None,
    duration_ms=None,
    request_id=None,
    meta=None,
):
    """Append one immutable, hash-chained audit event.

    All arguments beyond ``action`` are optional; ``request`` (when supplied)
    auto-fills IP, user-agent, actor, tenant and the correlation ``request_id``.
    """
    try:
        resolved_actor = _resolve_actor(actor, request)
        if hostel is None and request is not None:
            hostel = getattr(request, "hostel", None)
        ip = client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")[:2000] if request is not None else ""
        # Correlation id set by RequestTimingMiddleware so audit ↔ request logs join.
        if request_id is None and request is not None:
            request_id = getattr(request, "request_id", "") or ""

        payload = {
            "action": action,
            "actor_id": getattr(resolved_actor, "pk", None),
            "hostel_id": getattr(hostel, "id", None),
            "entity_type": entity_type or "",
            "entity_id": str(entity_id or ""),
            "message": (message or "")[:255],
            "reason": (reason or "")[:255],
            "changes": _clean_changes(changes),
            "result": result or AuditEvent.Result.SUCCESS,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "request_id": (request_id or "")[:64],
            "meta": meta or {},
            "ip_address": ip,
            "user_agent": ua,
            # Capture the moment the action happened, not when the worker persists it.
            "created_at": timezone.now().isoformat(),
        }

        # The INSERT runs on a Celery worker so the request never waits on it.
        # Any enqueue failure (broker down, unserializable meta) falls back to
        # the original synchronous write.
        from django.conf import settings

        if getattr(settings, "AUDIT_LOG_ASYNC", True):
            try:
                from .tasks import persist_audit_event

                # retry=False: this runs inside the request. If the broker is
                # unreachable/misconfigured, fail immediately and fall back to
                # the synchronous write below — never retry the broker connection
                # (that would block the request for seconds and can 502 it).
                persist_audit_event.apply_async((payload,), retry=False)
                return
            except Exception:
                pass

        AuditEvent.objects.create_chained(**payload)
    except Exception:
        # Never break the caller because of audit logging.
        pass
