#!/usr/bin/env bash
# =============================================================================
# logs_worker.sh — follow the Celery worker logs.
#
#   ./scripts/logs_worker.sh            follow the worker
#   ./scripts/logs_worker.sh beat       follow the beat scheduler
#   ./scripts/logs_worker.sh worker 200 follow, starting from the last 200 lines
#
# Equivalent to: docker compose -f backend/docker-compose.worker.yml logs -f worker
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/backend/docker-compose.worker.yml"

SERVICE="${1:-worker}"
TAIL="${2:-100}"

# Beat lives behind a profile — include it so `logs beat` resolves the service.
exec docker compose -f "$COMPOSE_FILE" --profile beat logs -f --tail "$TAIL" "$SERVICE"
