# Observability stack (Prompt 09)

Prometheus + Grafana + Loki + Promtail + Alertmanager + exporters, running
alongside the app stack. Optional and non-invasive — the application runs
identically without it.

## Quick start

1. Enable app metrics: set `PROMETHEUS_ENABLED=True` in `deploy/.env`
   (exposes `/metrics`, including the custom `hostel_security_*` /
   `hostel_rate_limit_*` / `hostel_auth_*` series).
2. Set `GRAFANA_PASSWORD` (and optionally `GRAFANA_PORT`, `PROM_RETENTION`,
   `LOKI_RETENTION`, alert webhook URLs) in `deploy/.env`.
3. Confirm the app network name (`docker network ls`; default
   `hostel_default`) and set `APP_NETWORK` if different.
4. Launch:

   ```bash
   docker compose \
     -f deploy/docker-compose.prod.yml \
     -f deploy/observability/docker-compose.observability.yml \
     --env-file deploy/.env up -d
   ```

5. Grafana → `http://<host>:${GRAFANA_PORT:-3009}` (behind your VPN/auth proxy).
   The **Hostel — Security & Rate Limiting** dashboard is auto-provisioned.

## What's collected

| Source | Via | Signals |
|---|---|---|
| Django backend | `/metrics` (django-prometheus + `apps.security.metrics`) | HTTP rate/latency/status, DB timings, security events, rate-limit decisions, auth events, WAF violations |
| Redis | redis_exporter | up, memory, ops, hit ratio, evictions |
| PostgreSQL | postgres_exporter | up, connections, tx, locks, replication |
| Host | node_exporter | CPU, memory, disk, network |
| Containers | cAdvisor | per-container CPU/mem/restarts |
| All logs | Promtail → Loki | JSON app logs (request_id/event/level labels), container stdout |

## Alerts

`prometheus/alerts.yml` → Alertmanager (`alertmanager/alertmanager.yml`),
severity critical/high/medium/low: Redis/Postgres/backend down, high
CPU/mem/disk, API 5xx rate + p95 latency, rate-limit spike (DDoS/flood),
auth-lockout surge (brute force/stuffing), WAF/bot surges. Wire real receivers
(email/Slack/PagerDuty) in `alertmanager.yml` — placeholders point at a webhook
sink so the config is valid out of the box.

## Distributed tracing (OpenTelemetry)

Optional, off by default. Install the OTel extras and set `OTEL_ENABLED=True` +
`OTEL_EXPORTER_OTLP_ENDPOINT` (see `backend/apps/common/otel.py`) to
auto-instrument Django + psycopg + Redis and export OTLP traces. Correlates
with logs/metrics via `X-Request-ID`.

## SSL-expiry monitoring

The custom-domain SSL expiry is already monitored in-app (Celery
`domains-revalidate`, Prompt 05). For edge-cert expiry add the Prometheus
`blackbox_exporter` with an `ssl` probe (documented in `docs/OPERATIONS.md`).
