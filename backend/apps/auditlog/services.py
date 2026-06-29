"""Central audit-logging helper.

Use ``record_event`` from views/services to capture security-relevant actions
(logins, payments, vacates, exports, backups). Failures are swallowed so audit
logging can never break a request.
"""
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


def record_event(
    request=None,
    *,
    action,
    actor=None,
    hostel=None,
    entity_type="",
    entity_id="",
    message="",
    meta=None,
):
    try:
        resolved_actor = _resolve_actor(actor, request)
        if hostel is None and request is not None:
            hostel = getattr(request, "hostel", None)
        ip = client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")[:2000] if request is not None else ""

        AuditEvent.objects.create(
            action=action,
            actor=resolved_actor,
            hostel_id=getattr(hostel, "id", None),
            entity_type=entity_type or "",
            entity_id=str(entity_id or ""),
            message=(message or "")[:255],
            meta=meta or {},
            ip_address=ip,
            user_agent=ua,
        )
    except Exception:
        # Never break the caller because of audit logging.
        pass
