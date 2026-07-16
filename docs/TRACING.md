# Distributed Tracing (OpenTelemetry)

**Phase 4, §4.** End-to-end request tracing across the stack:
**browser → Django backend → ML_hostel service**, linked into a single trace via
W3C trace-context propagation. Complements the metrics (Prometheus) and logs
(Loki) already in the observability stack.

## Design

- **Opt-in and fail-safe.** Tracing activates only when `OTEL_ENABLED=true` *and*
  the OTel packages are installed. Absent either, the bootstrap
  (`backend/config/otel.py`, `ML_hostel/app/observability.py`) is a no-op — the
  services run identically with tracing off, so there is zero prod risk from
  shipping the code disabled.
- **Auto-instrumentation.** Django (server), requests/httpx (client), and psycopg
  (DB) on the backend; FastAPI (server) and httpx (client) on the ML service.
- **Propagation is automatic.** Because the httpx client is instrumented, the
  `traceparent` header is injected on the Django→ML gateway calls and extracted
  by FastAPI, so a chat request is one connected trace.

## Enable

Backend and ML service each:

```bash
# 1. install the optional deps (kept out of the base image)
pip install -r requirements-otel.txt          # backend
pip install -r requirements-otel.txt          # ML_hostel

# 2. set env on each service
OTEL_ENABLED=true
OTEL_SERVICE_NAME=hostel-backend               # or hostel-ml
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318   # OTLP/HTTP
```

On Render, add these as env vars on each service; locally/compose, add them to
the service environment.

## Where traces go

Point `OTEL_EXPORTER_OTLP_ENDPOINT` at an OTLP/HTTP receiver — either an
OpenTelemetry Collector or **Grafana Tempo**. Adding Tempo to
`deploy/observability/docker-compose.observability.yml` and a Tempo datasource in
Grafana lets you pivot metrics → traces → logs (Loki) in one place. (Tempo is a
documented follow-up; the app side is ready now.)

## Verify

With a collector running and the env set, drive a chat request and confirm a
single trace spans `hostel-backend` and `hostel-ml`. Until a collector is wired,
enabling OTEL with no reachable endpoint simply buffers/drops spans — it does not
affect request handling.
