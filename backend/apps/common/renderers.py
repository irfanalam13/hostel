"""Standard API response envelope.

Every DRF JSON response is wrapped in a consistent shape::

    {"success": bool, "message": str, "data": <payload>, "meta": {...}}

* Paginated list responses ({count, next, previous, results}) move ``results``
  into ``data`` and the pagination cursors into ``meta.pagination`` so clients
  get a plain list back and pagination info stays available.
* Error responses (HTTP >= 400) keep the original DRF error body under
  ``errors`` and surface a human-readable string under ``message``.

The ``/api/auth/`` namespace is deliberately left untouched: those endpoints
implement the cookie/JWT handshake (login/refresh/logout) and their exact wire
format must not change. drf-spectacular's schema/docs views and binary
downloads (CSV/files via ``HttpResponse``) never reach this renderer.
"""
from rest_framework.renderers import JSONRenderer

# Keys DRF's PageNumberPagination emits for a paginated list.
_PAGINATION_KEYS = {"count", "next", "previous", "results"}
# Keys our own envelope already carries (guards against double-wrapping).
_ENVELOPE_KEYS = {"success", "data", "meta"}


class StandardJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        renderer_context = renderer_context or {}
        request = renderer_context.get("request")
        response = renderer_context.get("response")

        if not self._should_wrap(data, request):
            return super().render(data, accepted_media_type, renderer_context)

        status_code = getattr(response, "status_code", 200)
        envelope = self._build_envelope(data, status_code)
        return super().render(envelope, accepted_media_type, renderer_context)

    @staticmethod
    def _should_wrap(data, request):
        # Empty bodies (e.g. 204 No Content) stay empty.
        if data is None:
            return False
        # Leave the auth handshake namespace exactly as-is.
        path = getattr(request, "path", "") or ""
        if path.startswith("/api/auth/"):
            return False
        # Never double-wrap.
        if isinstance(data, dict) and _ENVELOPE_KEYS <= set(data.keys()):
            return False
        return True

    def _build_envelope(self, data, status_code):
        if status_code >= 400:
            return {
                "success": False,
                "message": self._error_message(data),
                "data": None,
                "errors": data,
                "meta": {},
            }

        if isinstance(data, dict) and _PAGINATION_KEYS <= set(data.keys()):
            return {
                "success": True,
                "message": "",
                "data": data.get("results"),
                "meta": {
                    "pagination": {
                        "count": data.get("count"),
                        "next": data.get("next"),
                        "previous": data.get("previous"),
                    }
                },
            }

        return {"success": True, "message": "", "data": data, "meta": {}}

    @staticmethod
    def _error_message(data):
        """Best-effort human message from a DRF error body."""
        if isinstance(data, dict):
            detail = data.get("detail")
            if isinstance(detail, str):
                return detail
            for value in data.values():
                if isinstance(value, (list, tuple)) and value:
                    return str(value[0])
                if isinstance(value, str):
                    return value
        if isinstance(data, list) and data:
            return str(data[0])
        return "Request failed."
