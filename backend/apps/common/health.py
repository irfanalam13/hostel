"""Health-check endpoints for load balancers and uptime monitoring.

These are intentionally plain Django views (not DRF) so they bypass the
authentication, throttling and response-envelope machinery. Each returns a
small, structured JSON document and an HTTP status that a load balancer can act
on: 200 when healthy, 503 when a dependency is down.

Endpoints
    /health/           liveness  — process is up, no dependencies touched
    /health/database/  readiness — `SELECT 1` against the default DB
    /health/cache/     readiness — PING against Redis
    /health/celery/    readiness — ping live Celery workers
"""

from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET


def _json(payload, *, healthy):
    return JsonResponse(payload, status=200 if healthy else 503)


@csrf_exempt
@never_cache
@require_GET
def health(request):
    """Liveness probe — cheap, touches no external dependency."""
    return _json({"status": "ok"}, healthy=True)


@csrf_exempt
@never_cache
@require_GET
def health_database(request):
    """Readiness probe for the primary database."""
    try:
        connection = connections["default"]
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except OperationalError as exc:
        return _json(
            {"status": "error", "component": "database", "detail": str(exc)},
            healthy=False,
        )
    except Exception as exc:  # pragma: no cover - defensive
        return _json(
            {"status": "error", "component": "database", "detail": str(exc)},
            healthy=False,
        )
    return _json({"status": "ok", "component": "database"}, healthy=True)


@csrf_exempt
@never_cache
@require_GET
def health_cache(request):
    """Readiness probe for Redis (cache / Celery broker backend)."""
    redis_url = getattr(settings, "REDIS_URL", None) or getattr(
        settings, "CELERY_BROKER_URL", ""
    )
    try:
        import redis  # redis-py ships as a dependency of celery

        client = redis.Redis.from_url(
            redis_url, socket_connect_timeout=2, socket_timeout=2
        )
        client.ping()
    except Exception as exc:
        return _json(
            {"status": "error", "component": "cache", "detail": str(exc)},
            healthy=False,
        )
    return _json({"status": "ok", "component": "cache"}, healthy=True)


@csrf_exempt
@never_cache
@require_GET
def health_celery(request):
    """Readiness probe for Celery workers (broadcast ping)."""
    try:
        from config.celery import app as celery_app

        replies = celery_app.control.ping(timeout=2.0)
    except Exception as exc:
        return _json(
            {"status": "error", "component": "celery", "detail": str(exc)},
            healthy=False,
        )

    workers = [name for reply in (replies or []) for name in reply]
    if not workers:
        return _json(
            {"status": "error", "component": "celery", "detail": "no workers responded"},
            healthy=False,
        )
    return _json(
        {"status": "ok", "component": "celery", "workers": workers},
        healthy=True,
    )
