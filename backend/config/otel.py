"""OpenTelemetry tracing bootstrap (Phase 4, §4). Opt-in and fail-safe.

Enabled only when ``OTEL_ENABLED=true`` AND the opentelemetry packages are
installed (``pip install -r requirements-otel.txt``). If either is missing every
call here is a no-op, so the app runs identically with tracing off — nothing to
break in prod if the extra deps aren't shipped.

When on, it auto-instruments Django (server spans), outbound requests/httpx
(client spans + W3C ``traceparent`` propagation to the ML service), and psycopg
(DB spans), exporting via OTLP to the endpoint in ``OTEL_EXPORTER_OTLP_ENDPOINT``
(e.g. a Grafana Tempo / OpenTelemetry Collector). Trace context propagates
automatically, so a browser→Django→ML_hostel request is one linked trace.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("config.otel")

_initialised = False


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def init_tracing() -> None:
    """Instrument the process if OTEL is enabled and the libs are present."""
    global _initialised
    if _initialised or not _truthy(os.getenv("OTEL_ENABLED")):
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.django import DjangoInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception:  # packages not installed -> stay a no-op
        logger.info("OTEL_ENABLED but opentelemetry packages missing; tracing disabled.")
        return

    resource = Resource.create({SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "hostel-backend")})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))  # endpoint from env
    trace.set_tracer_provider(provider)

    DjangoInstrumentor().instrument()
    # Client-side instrumentation is best-effort — each may be absent.
    for module, cls in (
        ("opentelemetry.instrumentation.requests", "RequestsInstrumentor"),
        ("opentelemetry.instrumentation.httpx", "HTTPXClientInstrumentor"),
        ("opentelemetry.instrumentation.psycopg", "PsycopgInstrumentor"),
    ):
        try:
            mod = __import__(module, fromlist=[cls])
            getattr(mod, cls)().instrument()
        except Exception:
            logger.debug("optional instrumentation %s unavailable", module)

    _initialised = True
    logger.info("OpenTelemetry tracing initialised (exporting via OTLP).")
