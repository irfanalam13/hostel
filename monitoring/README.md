# Monitoring & Observability

Roadmap Prompt 08. Prometheus + Alertmanager + Grafana + exporters, scraping the
Django app and the host/containers/datastores.

## Run

```bash
# 1. App must expose /metrics — set in the app's .env:
PROMETHEUS_ENABLED=True
# 2. Bring the app up (creates the hostel_default network), then:
docker compose -f monitoring/docker-compose.monitoring.yml up -d
```

If your compose project name isn't `hostel`, set the app network name:
`MONITORING_APP_NETWORK=<project>_default docker compose -f … up -d`.

## What's collected

| Source | Exporter / path | Examples |
| --- | --- | --- |
| Django | `web:8000/metrics` (django-prometheus) | request rate, latency histogram, 5xx |
| Host | node-exporter | CPU, memory, disk, network |
| Containers | cadvisor | per-service CPU/mem/IO |
| PostgreSQL | postgres-exporter | `pg_up`, connections, tx |
| Redis | redis-exporter | `redis_up`, memory, ops |
| Uptime | blackbox-exporter | `/health/*`, frontend `/` probes |

## UIs (bound to localhost — tunnel via SSH)

- Prometheus → `http://127.0.0.1:9090`
- Alertmanager → `http://127.0.0.1:9093`
- Grafana → `http://127.0.0.1:3001` (admin/admin by default — change via
  `GRAFANA_ADMIN_PASSWORD`). The **Hostel SaaS — Overview** dashboard is
  auto-provisioned.

## Alerts

`prometheus/alerts.yml` ships rules for target/health/DB/Redis down, high 5xx
rate, high p95 latency, and CPU/memory/disk pressure. Wire a real receiver
(Slack/email/PagerDuty) in `alertmanager/alertmanager.yml`.

## Security

`/metrics` is **internal-only** — scraped over the docker network and explicitly
404'd by the production Nginx. The monitoring UIs bind to `127.0.0.1`; reach them
via `ssh -L`. Never expose them publicly without auth.

## Error tracking & logs

- **Errors**: set `SENTRY_DSN` (already wired in `settings.py`).
- **Logs**: JSON/console + rotating file (`LOG_TO_FILE=True` in prod); ship to a
  central store (Loki/ELK) with a log driver or promtail if desired.
