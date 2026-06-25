# Deployment Guide — Hostel SaaS

Production-grade deployment using Docker Compose. The whole stack — Django API,
PostgreSQL, Redis, Celery worker, Celery beat, and the Next.js frontend — comes
up from a single `docker compose up`.

> **Scope note:** This is Phase 8 infrastructure. It changes how the app is
> *built, configured, and run* — it does not change any business logic, API
> behaviour, or the canonical Track A (residents/billing) domain.

---

## 1. Architecture

| Service         | Image / Build        | Port (host) | Purpose                              |
|-----------------|----------------------|-------------|--------------------------------------|
| `frontend`      | `./frontend`         | `3000`      | Next.js standalone server            |
| `web`           | `./backend`          | `8000`      | Django + Gunicorn (REST API + admin) |
| `celery_worker` | `./backend`          | —           | Background task execution            |
| `celery_beat`   | `./backend`          | —           | Periodic task scheduler              |
| `postgres`      | `postgres:16-alpine` | —           | Primary datastore (named volume)     |
| `redis`         | `redis:7-alpine`     | —           | Celery broker / result backend       |

`web`, `celery_worker`, and `celery_beat` all run the **same backend image**
with different commands. Static files are served by WhiteNoise from inside
Gunicorn, so no separate nginx container is required.

---

## 2. Prerequisites

- Docker Engine 24+ and the Docker Compose plugin (`docker compose`, not the
  legacy `docker-compose`).
- A host with at least 2 GB RAM.
- DNS / TLS termination (a reverse proxy such as nginx, Caddy, or a cloud load
  balancer) in front of the stack for real production. Point health checks at
  `https://<host>/health/`.

---

## 3. Initial deployment

```bash
# 1. Clone
git clone <your-repo-url> hostel && cd hostel

# 2. Create the environment file and fill in real secrets
cp .env.example .env
#   - DEBUG=False
#   - DJANGO_SECRET_KEY=$(python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())")
#   - POSTGRES_PASSWORD / DATABASE_URL (keep these in sync)
#   - ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, CSRF_TRUSTED_ORIGINS for your domain
#   - NEXT_PUBLIC_API_BASE_URL = the PUBLIC URL the browser uses to reach the API

# 3. Build and start the whole stack
docker compose up -d --build

# 4. The `web` service applies migrations automatically on start
#    (RUN_MIGRATIONS=1). Watch it come up:
docker compose logs -f web

# 5. Create the first admin user
docker compose exec web python manage.py createsuperuser

# 6. Verify health
curl -fsS http://localhost:8000/health/
curl -fsS http://localhost:8000/health/database/
curl -fsS http://localhost:8000/health/cache/
curl -fsS http://localhost:8000/health/celery/
```

Frontend: <http://localhost:3000> · API/docs: <http://localhost:8000/api/docs/> ·
Admin: <http://localhost:8000/admin/>

---

## 4. Updating the application

```bash
git pull
docker compose build                 # rebuild images with new code
docker compose up -d                  # recreate changed containers (rolling)
docker compose logs -f web            # confirm migrations + boot
```

Migrations run automatically when the `web` container starts. To apply them
without a full restart:

```bash
docker compose exec web python manage.py migrate --noinput
```

---

## 5. Rollback

Images are cheap to pin. Tag releases so you can roll back fast.

```bash
# If you tag images per release (recommended):
#   docker compose build && docker tag hostel-backend:latest hostel-backend:v1.4.2
# Roll back code:
git checkout <previous-tag>
docker compose up -d --build

# Roll back the database (only if a migration must be reversed):
docker compose exec web python manage.py migrate <app_label> <previous_migration>

# Full data restore from a PostgreSQL dump (see §7):
cat backup.sql | docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

> Always take a database backup **before** deploying a release that contains
> migrations (§7). Reversing data-destructive migrations is not always possible.

---

## 6. Environment setup (dev / staging / prod)

The variable **names** are identical across environments — only values differ.
See `.env.example` for the full annotated list.

| Variable                | Development            | Staging / Production            |
|-------------------------|------------------------|----------------------------------|
| `DEBUG`                 | `True`                 | `False`                          |
| `DJANGO_SECRET_KEY`     | dev placeholder ok     | strong, unique, secret           |
| `ALLOWED_HOSTS`         | `localhost,127.0.0.1`  | real hostnames                   |
| `CORS_ALLOWED_ORIGINS`  | `http://localhost:3000`| real HTTPS origins (no `*`)      |
| Email backend           | console (auto)         | SMTP via `EMAIL_*`               |
| TLS / secure cookies    | off                    | auto-enabled when `DEBUG=False`  |

The backend **fails fast on boot** when `DEBUG=False` and any of
`DJANGO_SECRET_KEY`, `ALLOWED_HOSTS`, or `CORS_ALLOWED_ORIGINS` is missing or
insecure — misconfiguration surfaces immediately, not as silent 400s.

---

## 7. Database migration & backup process

```bash
# Apply migrations
docker compose exec web python manage.py migrate --noinput

# Inspect the plan without applying
docker compose exec web python manage.py migrate --plan

# Generate new migrations after a model change (dev)
docker compose exec web python manage.py makemigrations

# Backup (logical dump)
docker compose exec -T postgres pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > backup_$(date +%F).sql

# Restore
cat backup_2026-06-14.sql | docker compose exec -T postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

PostgreSQL data lives in the `postgres_data` named volume and survives
`docker compose down`. It is only deleted by `docker compose down -v`.

---

## 8. Celery deployment

The worker and beat scheduler run as dedicated services off the same image:

```bash
docker compose up -d celery_worker celery_beat
docker compose logs -f celery_worker
```

- **Worker** — executes queued tasks (`celery -A config worker`).
- **Beat** — enqueues scheduled tasks such as backups (`celery -A config beat`).
- Both read `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` from `.env` and connect
  to the `redis` service.
- Scale workers horizontally: `docker compose up -d --scale celery_worker=3`
  (do **not** scale `celery_beat` beyond 1 — duplicate schedulers double-fire).
- Liveness: `docker compose exec celery_worker celery -A config inspect ping`.

---

## 9. Redis deployment

Redis runs with append-only persistence (`--appendonly yes`) and its data is
stored in the `redis_data` named volume.

```bash
docker compose exec redis redis-cli ping        # -> PONG
docker compose exec redis redis-cli info server
```

For production, consider a managed Redis or enabling `requirepass`; if you do,
update `REDIS_URL` / `CELERY_BROKER_URL` to `redis://:PASSWORD@redis:6379/0`.

---

## 10. Operational commands

```bash
# Start the whole stack (detached)
docker compose up -d

# Stop and remove containers (volumes/data preserved)
docker compose down

# Stop and ALSO delete volumes (DESTROYS the database) — use with care
docker compose down -v

# Logs (all services / one service / follow)
docker compose logs
docker compose logs web
docker compose logs -f --tail=100 celery_worker

# Restart a service
docker compose restart web

# Shell into the backend container
docker compose exec web bash

# Open a psql session
docker compose exec postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

# Django management shell
docker compose exec web python manage.py shell

# Show running services + health
docker compose ps
```

---

## 11. Health checks (for load balancers & uptime monitors)

All endpoints are unauthenticated, return structured JSON, and respond `200`
when healthy / `503` when their dependency is down.

| Endpoint            | Checks                                   |
|---------------------|------------------------------------------|
| `GET /health/`      | Process is alive (liveness, no deps)     |
| `GET /health/database/` | `SELECT 1` against PostgreSQL        |
| `GET /health/cache/`    | `PING` against Redis                 |
| `GET /health/celery/`   | A live Celery worker replied to ping |

Use `/health/` for load-balancer liveness and the dependency endpoints for
readiness / uptime dashboards.

---

## 12. Security notes

- Containers run as **non-root** users (`app` in the backend, `node` in the
  frontend).
- Secrets are **never baked into images** — they are injected at runtime via
  `.env` / `env_file`. `.env` is git-ignored; only `.env.example` is committed.
- `DEBUG=False` in staging/production, with HSTS, secure cookies, SSL redirect,
  and a strict CSP enabled automatically.
- `.dockerignore` keeps the SQLite dev DB, `.env`, logs, and the local venv out
  of build contexts.
- CI scans every PR for committed secrets (gitleaks) and dependency
  vulnerabilities (pip-audit / npm audit).
