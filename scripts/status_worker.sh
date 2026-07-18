#!/usr/bin/env bash
# =============================================================================
# status_worker.sh — health snapshot of the Celery worker.
#
# Shows: compose service status, container uptime, a live resource snapshot
# (CPU / memory), and a broker ping so you know the worker can reach Redis.
#
#   ./scripts/status_worker.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/backend/docker-compose.worker.yml"

if [ -t 1 ]; then C_HDR='\033[1;36m'; C_OFF='\033[0m'; else C_HDR=''; C_OFF=''; fi
hdr() { printf "\n${C_HDR}==> %s${C_OFF}\n" "$*"; }

COMPOSE=(docker compose -f "$COMPOSE_FILE" --profile beat)

hdr "Compose services"
"${COMPOSE[@]}" ps

# Resolve the running container IDs for this project so `ps`/`stats` are scoped.
CIDS="$("${COMPOSE[@]}" ps -q 2>/dev/null || true)"

if [ -z "$CIDS" ]; then
  echo "No worker containers are running. Start with ./scripts/deploy_worker.sh"
  exit 0
fi

hdr "Container uptime"
# shellcheck disable=SC2086
docker ps --filter "id=$(echo $CIDS | tr ' ' ',')" \
  --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'

hdr "Resource usage (CPU / memory) — single snapshot"
# shellcheck disable=SC2086
docker stats --no-stream $CIDS \
  --format 'table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}'

hdr "Broker ping (worker -> Redis)"
if "${COMPOSE[@]}" exec -T worker celery -A config inspect ping -t 10 >/dev/null 2>&1; then
  echo "OK — worker replied to inspect ping (broker reachable, tasks flowing)"
else
  echo "WARN — no ping reply. Check REDIS_URL/CELERY_BROKER_URL and 'logs_worker.sh'"
fi
