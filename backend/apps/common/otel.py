"""Optional OpenTelemetry instrumentation (traces + metrics).

Disabled by default and entirely guarded: if ``OTEL_ENABLED`` is off, or the
``opentelemetry-*`` packages aren't installed, ``configure()`` is a silent
no-op — the app runs identically. When enabled it auto-instruments Django,
psycopg and Redis and exports OTLP to the configured collector, so the whole
request path (gateway → middleware → auth → rate limiter → DB → response) is
traced with latency at every stage.

Enable (production) by installing the extras and setting env:

    pip install opentelemetry-distro opentelemetry-exporter-otlp \
        opentelemetry-instrumentation-django \
        opentelemetry-instrumentation-psycopg \
        opentelemetry-instrumentation-redis
    OTEL_ENABLED=True
    OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
    OTEL_SERVICE_NAME=hostel-backend

Traces correlate with logs/metrics via the same request id
(RequestTimingMiddleware sets X-Request-ID).
"""
import logging
import os

logger = logging.getLogger("apps.common")

_configured = False


def configure() -> bool:
    """Initialise OTel if enabled + available. Returns True when active.
    Called once from AppConfig.ready(); safe to call more than once."""
    global _configured
    if _configured:
        return True

    if os.environ.get("OTEL_ENABLED", "").strip().lower() not in ("1", "true", "yes", "on"):
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception:
        logger.warning(
            "OTEL_ENABLED is set but opentelemetry packages are missing; "
            "tracing disabled. See apps/common/otel.py for the install list."
        )
        return False

    try:
        service = os.environ.get("OTEL_SERVICE_NAME", "hostel-backend")
        provider = TracerProvider(resource=Resource.create({"service.name": service}))
        provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(provider)

        # Best-effort auto-instrumentation — each is independently guarded so a
        # missing optional instrumentor never blocks the others.
        for module_path, cls_name in (
            ("opentelemetry.instrumentation.django", "DjangoInstrumentor"),
            ("opentelemetry.instrumentation.psycopg", "PsycopgInstrumentor"),
            ("opentelemetry.instrumentation.redis", "RedisInstrumentor"),
        ):
            try:
                mod = __import__(module_path, fromlist=[cls_name])
                getattr(mod, cls_name)().instrument()
            except Exception:
                logger.debug("OTel instrumentor %s unavailable", cls_name)

        _configured = True
        logger.info("OpenTelemetry tracing enabled (service=%s)", service)
        return True
    except Exception:
        logger.warning("OpenTelemetry initialisation failed; tracing disabled.",
                       exc_info=True)
        return False
