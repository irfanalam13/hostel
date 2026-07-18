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
    /health/storage/   readiness — write/read/delete a probe file on the
                                   default media storage (volume or S3/MinIO)
    /health/queue/     readiness — Celery queue depth (backlog warning)

None of these expose secrets, hostnames or credentials — components report
only ok/error plus a short generic detail string.
"""

from django.conf import settings
from django.db import connections
from django.db.utils import OperationalError
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_safe


def _json(payload, *, healthy):
    return JsonResponse(payload, status=200 if healthy else 503)


@csrf_exempt
@never_cache
@require_safe
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
def health_email_egress(request):
    """TEMPORARY diagnostic: can this host reach the configured SMTP relay?

    Reports the configured EMAIL_HOST/PORT (not secrets — no username/password)
    and TCP-connect results to the configured port plus the common Brevo ports,
    so we can tell a port misconfig (e.g. 25) from an egress block from a DNS
    problem. Remove once the OTP-delivery cause is confirmed.
    """
    import socket

    host = getattr(settings, "EMAIL_HOST", "") or "smtp-relay.brevo.com"
    configured_port = int(getattr(settings, "EMAIL_PORT", 587) or 587)

    def probe(port):
        try:
            infos = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
        except Exception as exc:
            return {"dns": "FAIL", "error": type(exc).__name__, "detail": str(exc)}
        fam, _, _, _, sa = infos[0]
        family = "IPv6" if fam == socket.AF_INET6 else "IPv4"
        s = socket.socket(fam, socket.SOCK_STREAM)
        s.settimeout(6)
        try:
            s.connect(sa)
            return {"connect": "OK", "ip": sa[0], "family": family}
        except Exception as exc:
            return {"connect": "FAIL", "ip": sa[0], "family": family,
                    "error": type(exc).__name__}
        finally:
            s.close()

    ports = sorted({configured_port, 587, 465, 2525, 25})
    return _json(
        {
            "status": "ok",
            "component": "email-egress",
            "email_host": host,
            "email_port": configured_port,
            "use_tls": getattr(settings, "EMAIL_USE_TLS", None),
            "use_ssl": getattr(settings, "EMAIL_USE_SSL", None),
            "email_timeout": getattr(settings, "EMAIL_TIMEOUT", None),
            "backend": getattr(settings, "EMAIL_BACKEND", ""),
            "probes": {str(p): probe(p) for p in ports},
        },
        healthy=True,
    )


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


@csrf_exempt
@never_cache
@require_GET
def health_storage(request):
    """Readiness probe for the default media storage (filesystem volume or
    S3/MinIO/R2): write, read back and delete a tiny probe object."""
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage

    probe_name = "health/.storage-probe"
    try:
        saved = default_storage.save(probe_name, ContentFile(b"ok"))
        try:
            with default_storage.open(saved, "rb") as handle:
                content = handle.read()
        finally:
            default_storage.delete(saved)
        if content != b"ok":
            raise RuntimeError("probe readback mismatch")
    except Exception:
        # Generic detail only — storage errors can embed endpoints/credentials.
        return _json(
            {"status": "error", "component": "storage",
             "detail": "storage write/read probe failed"},
            healthy=False,
        )
    return _json({"status": "ok", "component": "storage"}, healthy=True)


@csrf_exempt
@never_cache
@require_GET
def health_queue(request):
    """Readiness probe for the Celery queue: reports backlog depth. Unhealthy
    only when the broker is unreachable; a deep-but-reachable queue returns
    200 with the depth so monitoring can alert on trend, not flap the LB."""
    redis_url = getattr(settings, "CELERY_BROKER_URL", "") or getattr(
        settings, "REDIS_URL", ""
    )
    try:
        import redis

        client = redis.Redis.from_url(
            redis_url, socket_connect_timeout=2, socket_timeout=2
        )
        depth = int(client.llen("celery"))  # default Celery queue key
    except Exception:
        return _json(
            {"status": "error", "component": "queue",
             "detail": "broker unreachable"},
            healthy=False,
        )
    return _json(
        {"status": "ok", "component": "queue", "depth": depth},
        healthy=True,
    )
