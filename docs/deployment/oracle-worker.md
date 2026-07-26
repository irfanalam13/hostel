# Oracle Cloud — Celery Worker Deployment

Run the Hostel background **Celery worker** (and optionally **Beat**) on a free
Oracle Cloud Ubuntu 24.04 VM, while the Django API stays on **Render** and Redis
+ Postgres stay on their managed hosts.

```
Frontend ──▶ Render (Django API) ──▶ Redis Cloud ──▶ Oracle VM
                                                       ├── Celery Worker
                                                       └── (optional) Celery Beat
```

The VM pulls tasks off the same Redis broker the Render web service publishes
to, executes them, and writes results back. It runs **no HTTP, no database, no
Redis** — those are all external.

---

## 0. Prerequisites

- An Oracle Cloud "Always Free" VM (Ubuntu 24.04, ARM Ampere or x86 — the image
  is multi-arch via `python:3.13-slim`).
- The VM's **ingress** needs nothing special (the worker only makes *outbound*
  connections). Ensure **egress** to your Redis and Postgres ports is allowed in
  the VCN security list / NSG (default egress is open).
- Redis and Postgres must be reachable from the VM's public egress. On Render,
  use the **External** database URL and enable TLS (`?sslmode=require`).

---

## 1. SSH into the VM

```bash
ssh -i ~/.ssh/oracle_vm.key ubuntu@<VM_PUBLIC_IP>
```

> Keep the `.pem`/`.key` private key OFF the repo — `.gitignore` already blocks
> `*.pem` and `*.key`.

---

## 2. Install Docker + Compose plugin

Docker Engine ships the Compose v2 plugin. On Ubuntu 24.04:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Run docker without sudo (log out/in afterwards), and start on boot.
sudo usermod -aG docker "$USER"
sudo systemctl enable --now docker
```

Verify:

```bash
docker --version
docker compose version
```

---

## 3. Clone the repository

```bash
sudo mkdir -p /opt/hostel && sudo chown "$USER":"$USER" /opt/hostel
git clone <YOUR_REPO_URL> /opt/hostel
cd /opt/hostel
```

> `/opt/hostel` is the path used by the systemd unit. Use a different path only
> if you also edit `oracle/celery-worker.service`.

---

## 4. Create `.env.production`

The env file lives **next to the compose file**, at `backend/.env.production`.

```bash
cp backend/.env.production.example backend/.env.production
nano backend/.env.production
```

Fill in real values. The critical ones (must **match Render**):

| Variable | Why it must match Render |
| --- | --- |
| `DJANGO_SECRET_KEY` | signed payloads/tokens must verify on both sides |
| `DATABASE_URL` | worker reads/writes the same database (use the **external** URL) |
| `REDIS_URL` / `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | same broker the API publishes to |
| `BACKUP_ENCRYPTION_KEY` | encrypted backups must be decryptable by both |
| `EMAIL_*`, `DEFAULT_FROM_EMAIL` | tasks send the same transactional mail |

Set `CELERY_TASK_ALWAYS_EAGER=False` and `EMAIL_SEND_IN_THREAD=False` here — this
host is a real worker and must execute tasks directly.

Permissions:

```bash
chmod 600 backend/.env.production
```

### ⚠️ Required changes on the Render side (task routing)

The Render web service currently runs in **eager mode** (`CELERY_TASK_ALWAYS_EAGER`
defaults to `True` when `DEBUG=False`) — it runs every task inline and never uses
the broker, so the Oracle worker sits idle.

We deliberately **do not** offload *everything* to the free Oracle VM. Only the
heavy, infrequent work goes there; latency-sensitive and per-request tasks stay
on Render so they neither depend on the free VM being up nor add a remote-broker
round-trip (and Upstash command cost) to the hot path.

| Task | Runs on | Why |
| --- | --- | --- |
| OTP / transactional email | **Render** (local thread) | Delivery must not depend on the free VM; reliability-critical |
| Audit event writes | **Render** (inline) | Fires per mutating request — a remote publish would add latency + burn Upstash commands |
| Security event writes | **Render** (inline) | Same — per auth-event, high frequency |
| DR backups + retention | **Oracle** (broker) | Heavy, infrequent |
| AI document ingestion | **Oracle** (broker) | Heavy CPU, infrequent |
| Push-notification fan-out | **Oracle** (broker) | I/O-heavy background, non-critical |

Set these environment variables on the **Render web service**:

```
# Offload heavy background tasks to the broker → Oracle worker.
CELERY_TASK_ALWAYS_EAGER=False

# Keep user-facing OTP/transactional email ON Render (runs in a daemon thread,
# never the broker) so delivery doesn't depend on the Oracle VM.
EMAIL_TASKS_STAY_LOCAL=True
EMAIL_SEND_IN_THREAD=True          # already the prod default; set explicitly

# Keep per-request audit + security event writes local (inline) instead of
# publishing them to the remote broker on every request.
AUDIT_LOG_ASYNC=False
SECURITY_EVENTS_PERSIST_ASYNC=False
```

Leave `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` pointing at the **same** Redis
as the Oracle worker. No code changes are needed — routing is entirely driven by
these env vars, and every `.delay()` call site is unchanged.

> If you'd rather send *all* tasks to Oracle, set only `CELERY_TASK_ALWAYS_EAGER=False`
> and omit the other four. Then OTP/audit/security ride the broker too — simpler,
> but OTP delivery and per-request latency now depend on the free VM + remote Redis.

---

## 5. Deploy

Make the scripts executable once, then deploy:

```bash
chmod +x scripts/*.sh
./scripts/deploy_worker.sh
```

This pulls code, builds the image, (re)starts the worker detached, and waits for
its healthcheck. Add `--with-beat` to also start the scheduler:

```bash
./scripts/deploy_worker.sh --with-beat
```

> **Only one Beat** may run across the entire deployment, or every scheduled job
> fires twice. Enable it here **only** if Beat is not already running elsewhere.

---

## 6. Start on boot (choose ONE)

**Option A — Docker restart policy (simplest).** The compose services use
`restart: unless-stopped`; with `systemctl enable docker` (step 2) they come back
after a reboot automatically. Nothing else to do.

**Option B — systemd unit.** If you prefer systemd to own the lifecycle:

```bash
sudo cp oracle/celery-worker.service /etc/systemd/system/celery-worker.service
# edit WorkingDirectory if your clone is not /opt/hostel
sudo systemctl daemon-reload
sudo systemctl enable --now celery-worker.service
sudo systemctl status celery-worker.service
```

Don't run both the deploy script's `up -d` *and* the systemd unit at the same
time — pick one supervisor.

---

## Day-2 operations

| Action | Command |
| --- | --- |
| Update to latest code | `./scripts/update_worker.sh` |
| Follow logs | `./scripts/logs_worker.sh` |
| Follow beat logs | `./scripts/logs_worker.sh beat` |
| Restart | `./scripts/restart_worker.sh` |
| Stop | `./scripts/stop_worker.sh` |
| Health / resources | `./scripts/status_worker.sh` |

---

## Verify tasks are flowing

1. On the VM: `./scripts/status_worker.sh` → the broker ping should say **OK**.
2. Trigger a task from the app (e.g. request a signup OTP, or run a manual
   backup from the DR admin) with Render in non-eager mode.
3. Watch it execute: `./scripts/logs_worker.sh` shows a
   `Task ... received` / `succeeded` line.

Or inspect from inside the container directly:

```bash
docker compose -f backend/docker-compose.worker.yml exec worker \
  celery -A config inspect active
docker compose -f backend/docker-compose.worker.yml exec worker \
  celery -A config inspect registered
```

---

## Troubleshooting

**Worker never becomes healthy / `inspect ping` fails.**
Almost always the broker is unreachable. Check `CELERY_BROKER_URL` in
`backend/.env.production`, confirm the VM's egress allows the Redis port, and try
`rediss://` (TLS) if the provider requires it. `./scripts/logs_worker.sh` shows
the connection error.

**Tasks are published on Render but nothing runs here.**
Render is still in eager mode. Set `CELERY_TASK_ALWAYS_EAGER=False` on Render and
confirm both sides share the exact same `CELERY_BROKER_URL`.

**`django.db.utils.OperationalError` in the worker logs.**
The database isn't reachable from Oracle. Use the **external** `DATABASE_URL`
(not the Render-internal host) and append `?sslmode=require`.

**Signature/decrypt errors on tasks.**
`DJANGO_SECRET_KEY` or `BACKUP_ENCRYPTION_KEY` differ from Render. They must be
byte-identical.

**Scheduled jobs run twice.**
Two Beat instances are active. Run Beat in exactly one place.

**Out-of-memory kills on the free VM.**
Lower `WORKER_MEM_LIMIT` / `CELERY_WORKER_MAX_MEMORY_PER_CHILD` and keep
`--concurrency=1` (the default here).

**`permission denied` talking to Docker.**
You haven't re-logged-in since `usermod -aG docker`. Log out and back in, or run
`newgrp docker`.
