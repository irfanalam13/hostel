"""Per-request timing, tracing and structured logging.

Every API request gets:

* a request id — taken from an incoming ``X-Request-ID`` header (so a trace
  started by the frontend/proxy is continued) or generated here, echoed back
  on the response so browser DevTools ↔ server logs correlate;
* a ``Server-Timing`` response header (visible in the browser Network panel)
  breaking the wall time into app vs database;
* one structured log line per request: method, path, status, total duration,
  DB time, query count, user, tenant and response size.

Requests slower than ``SLOW_REQUEST_MS`` are logged at WARNING so a latency
regression is impossible to miss in the logs.

DB time is measured with a ``connection.execute_wrapper`` — accurate in
production, no reliance on ``DEBUG`` / ``connection.queries``.
"""
import logging
import time
import uuid

from django.conf import settings
from django.db import connection

logger = logging.getLogger("apps.requests")

# Cheap, high-volume paths that would only add log noise.
_SKIP_PREFIXES = ("/static/", "/media/", "/health/", "/metrics")


class RequestTimingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_ms = int(getattr(settings, "SLOW_REQUEST_MS", 300))

    def __call__(self, request):
        if request.method == "OPTIONS" or request.path.startswith(_SKIP_PREFIXES):
            return self.get_response(request)

        incoming = request.headers.get("X-Request-ID", "")
        # Accept only sane ids; otherwise mint a fresh one.
        request_id = incoming[:64] if incoming and incoming.isascii() else ""
        if not request_id:
            request_id = uuid.uuid4().hex[:16]
        request.request_id = request_id

        db = {"time": 0.0, "count": 0}

        def _track(execute, sql, params, many, context):
            started = time.perf_counter()
            try:
                return execute(sql, params, many, context)
            finally:
                db["time"] += time.perf_counter() - started
                db["count"] += 1

        start = time.perf_counter()
        with connection.execute_wrapper(_track):
            response = self.get_response(request)
        total_ms = (time.perf_counter() - start) * 1000
        db_ms = db["time"] * 1000

        response["X-Request-ID"] = request_id
        response["Server-Timing"] = (
            f'db;dur={db_ms:.1f}, app;dur={max(total_ms - db_ms, 0):.1f}, '
            f'total;dur={total_ms:.1f}'
        )
        # Server-Timing is only shown for cross-origin resources when the
        # origin is explicitly allowed — mirror the CORS allow-list.
        origin = request.headers.get("Origin")
        if origin and origin in getattr(settings, "CORS_ALLOWED_ORIGINS", []):
            response["Timing-Allow-Origin"] = origin

        user = getattr(request, "user", None)
        user_id = getattr(user, "pk", None) if getattr(user, "is_authenticated", False) else None
        hostel = getattr(request, "hostel", None)
        try:
            size = len(response.content) if not response.streaming else -1
        except Exception:
            size = -1

        log = logger.warning if total_ms >= self.slow_ms else logger.info
        log(
            "request_id=%s method=%s path=%s status=%s duration_ms=%.1f "
            "db_ms=%.1f db_queries=%d user=%s hostel=%s bytes=%d",
            request_id,
            request.method,
            request.path,
            getattr(response, "status_code", "?"),
            total_ms,
            db_ms,
            db["count"],
            user_id if user_id is not None else "-",
            getattr(hostel, "slug", None) or getattr(hostel, "code", None) or "-",
            size,
        )
        return response
