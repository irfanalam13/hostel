"""OpenTelemetry tracing for the ML service (Phase 4, §4). Opt-in, fail-safe.

Enabled only when ``OTEL_ENABLED=true`` and the opentelemetry packages are
installed (``pip install -r requirements-otel.txt``); otherwise a no-op. When on,
it instruments FastAPI (server spans) and httpx (client spans to the Django
gateway), extracting the incoming W3C ``traceparent`` so a browser→Django→ML
request is a single linked trace, and exports via OTLP.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("app.observability")


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in ("1", "true", "yes", "on")


def init_tracing(app) -> None:
    if not _truthy(os.getenv("OTEL_ENABLED")):
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import SERVICE_NAME, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception:
        logger.info("OTEL_ENABLED but opentelemetry packages missing; tracing disabled.")
        return

    resource = Resource.create({SERVICE_NAME: os.getenv("OTEL_SERVICE_NAME", "hostel-ml")})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
    except Exception:
        logger.debug("httpx instrumentation unavailable")

    logger.info("OpenTelemetry tracing initialised for ML service.")
