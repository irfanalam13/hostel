from django.utils.deprecation import MiddlewareMixin

from .services import METHOD_ACTION, record_event


class AuditLogMiddleware(MiddlewareMixin):
    """Logs generic API write actions. Auth events (login/logout/password)
    are logged explicitly in the views with richer context, so they are
    skipped here to avoid duplicates."""

    def process_response(self, request, response):
        if request.method == "OPTIONS":
            return response

        try:
            path = getattr(request, "path", "")
            if (
                path.startswith("/api/")
                and not path.startswith("/api/auth/")
                and request.method in METHOD_ACTION
            ):
                record_event(
                    request,
                    action=METHOD_ACTION[request.method],
                    entity_type=path,
                    message=f"{request.method} {path}",
                    meta={"status_code": getattr(response, "status_code", None)},
                )
        except Exception:
            # never break the response because of audit logging
            pass

        return response
