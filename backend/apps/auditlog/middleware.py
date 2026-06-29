from django.utils.deprecation import MiddlewareMixin

from .models import AuditEvent
from .services import METHOD_ACTION, record_event


class AuditLogMiddleware(MiddlewareMixin):
    """Logs generic API write actions plus security-relevant denials.

    Auth events (login/logout/password) are logged explicitly in the views with
    richer context, so they're skipped here to avoid duplicates. We additionally
    record 401/403 responses on non-auth API paths as ACCESS_DENIED events so
    probing / privilege-escalation attempts leave an audit trail.
    """

    def process_response(self, request, response):
        if request.method == "OPTIONS":
            return response

        try:
            path = getattr(request, "path", "")
            if not path.startswith("/api/") or path.startswith("/api/auth/"):
                return response

            status = getattr(response, "status_code", None)

            # Security: log denied access on any method (probing, broken access
            # control attempts) — even safe GETs, which the write-logging skips.
            if status in (401, 403):
                record_event(
                    request,
                    action=AuditEvent.Action.ACCESS_DENIED,
                    entity_type=path,
                    message=f"{status} {request.method} {path}",
                    meta={"status_code": status},
                )
            elif request.method in METHOD_ACTION:
                record_event(
                    request,
                    action=METHOD_ACTION[request.method],
                    entity_type=path,
                    message=f"{request.method} {path}",
                    meta={"status_code": status},
                )
        except Exception:
            # never break the response because of audit logging
            pass

        return response
