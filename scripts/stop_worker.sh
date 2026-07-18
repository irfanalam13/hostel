#!/usr/bin/env bash
# =============================================================================
# stop_worker.sh — stop and remove the Celery worker containers.
#
#   ./scripts/stop_worker.sh             stop worker (and beat if running)
#   ./scripts/stop_worker.sh --keep      stop but keep containers (compose stop)
#
# Default is `compose down` (stops + removes containers; the built image and
# your .env.production are untouched).
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/backend/docker-compose.worker.yml"

if [ -t 1 ]; then C_OK='\033[1;32m'; C_OFF='\033[0m'; else C_OK=''; C_OFF=''; fi
COMPOSE=(docker compose -f "$COMPOSE_FILE" --profile beat)

if [ "${1:-}" = "--keep" ]; then
  "${COMPOSE[@]}" stop
else
  "${COMPOSE[@]}" down --remove-orphans
fi

printf "${C_OK}[stop %s] OK worker stopped${C_OFF}\n" "$(date +%H:%M:%S)"
