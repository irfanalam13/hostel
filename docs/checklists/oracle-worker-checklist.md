# Oracle Celery Worker — Production Checklist

Work top to bottom. Full walkthrough: [`docs/deployment/oracle-worker.md`](../deployment/oracle-worker.md).

## Host prerequisites

- [ ] Oracle Ubuntu 24.04 VM provisioned; SSH access works
- [ ] VCN egress allows outbound to the Redis and Postgres ports
- [ ] **Docker installed** — `docker --version`
- [ ] **Docker Compose installed** — `docker compose version` (v2 plugin)
- [ ] Docker enabled on boot — `systemctl is-enabled docker` → `enabled`
- [ ] Current user in the `docker` group (re-logged in) — `docker ps` works without `sudo`
- [ ] **Git installed** — `git --version`

## Code & configuration

- [ ] **Repository cloned** to `/opt/hostel` (or your path)
- [ ] `backend/.env.production` created from the example
- [ ] **Environment configured** — all `replace-me` / `USER:PASSWORD` placeholders filled
- [ ] `DJANGO_SECRET_KEY` **matches Render**
- [ ] `BACKUP_ENCRYPTION_KEY` **matches Render**
- [ ] `DATABASE_URL` uses the **external** DB host + `sslmode=require`
- [ ] `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` **match Render**
- [ ] `CELERY_TASK_ALWAYS_EAGER=False` and `EMAIL_SEND_IN_THREAD=False` on this host
- [ ] `chmod 600 backend/.env.production`
- [ ] Scripts executable — `chmod +x scripts/*.sh`

## Render side (producer / task routing)

- [ ] Render shares the same `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` as this VM
- [ ] `CELERY_TASK_ALWAYS_EAGER=False` (offload heavy tasks to Oracle)
- [ ] `EMAIL_TASKS_STAY_LOCAL=True` + `EMAIL_SEND_IN_THREAD=True` (OTP stays on Render)
- [ ] `AUDIT_LOG_ASYNC=False` (audit writes inline on Render)
- [ ] `SECURITY_EVENTS_PERSIST_ASYNC=False` (security writes inline on Render)
- [ ] Confirm only backups / AI ingestion / push fan-out reach the Oracle worker
      (watch `./scripts/logs_worker.sh` — you should NOT see per-request audit tasks)

## Deploy

- [ ] `./scripts/deploy_worker.sh` completed without errors
- [ ] **Worker running** — `./scripts/status_worker.sh` shows the container `Up`
- [ ] **Redis connected** — status broker ping reports **OK**
- [ ] **Database reachable** — no `OperationalError` in `./scripts/logs_worker.sh`
- [ ] **Tasks executing** — a triggered task shows `received` / `succeeded` in logs
- [ ] **Logs clean** — no repeating tracebacks or reconnect loops

## Resilience

- [ ] **Auto-restart enabled** — Docker restart policy (docker enabled on boot),
      **or** the systemd unit installed & `enabled`
- [ ] Reboot test: `sudo reboot`, then confirm the worker comes back up
- [ ] Resource caps sane for the VM — `WORKER_MEM_LIMIT`, `--concurrency=1`
- [ ] (If used) **exactly one** Beat instance runs across the whole deployment

## Optional

- [ ] `SENTRY_DSN` set so worker errors are captured
- [ ] Beat enabled here (`--with-beat`) only if not scheduled elsewhere
