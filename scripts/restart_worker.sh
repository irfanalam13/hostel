#!/usr/bin/env bash
# =============================================================================
# restart_worker.sh — restart the Celery worker without rebuilding.
#
#   ./scripts/restart_worker.sh          restart the worker
#   ./scripts/restart_worker.sh --all    restart worker + beat
#
# Equivalent to: docker compose -f backend/docker-compose.worker.yml restart worker
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/backend/docker-compose.worker.yml"

if [ -t 1 ]; then C_OK='\033[1;32m'; C_OFF='\033[0m'; else C_OK=''; C_OFF=''; fi

if [ "${1:-}" = "--all" ]; then
  docker compose -f "$COMPOSE_FILE" --profile beat restart
else
  docker compose -f "$COMPOSE_FILE" restart worker
fi

printf "${C_OK}[restart %s] OK done${C_OFF}\n" "$(date +%H:%M:%S)"
