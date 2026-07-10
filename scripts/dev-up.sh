#!/usr/bin/env bash
# =============================================================================
# dev-up.sh — start the whole Hostel stack in one command
#
#   ./scripts/dev-up.sh              DEV: hot-reload stack (docker-compose.override.yml)
#   ./scripts/dev-up.sh --prod       production-style stack (no reload, baked code)
#   ./scripts/dev-up.sh --down       stop and remove all containers
#   ./scripts/dev-up.sh --no-logs    start in the background without tailing logs
#   ./scripts/dev-up.sh --no-build   start without rebuilding images
#
# Runs postgres, redis, web (Django), celery_worker, celery_beat, frontend.
# In DEV (default) source is bind-mounted and servers auto-reload — no rebuild
# needed after code edits. In --prod, code is baked in, so rebuild after changes.
# =============================================================================
set -euo pipefail

# Always run from the repo root (parent of this script's folder).
cd "$(dirname "$0")/.."

PROD=0
DOWN=0
NO_LOGS=0
NO_BUILD=0
for arg in "$@"; do
    case "$arg" in
        --prod)     PROD=1 ;;
        --down)     DOWN=1 ;;
        --no-logs)  NO_LOGS=1 ;;
        --no-build) NO_BUILD=1 ;;
        *) echo "Unknown option: $arg" >&2; exit 2 ;;
    esac
done

# --prod pins to the base file only, so the dev override is NOT auto-merged.
compose_files=()
[ "$PROD" -eq 1 ] && compose_files=(-f docker-compose.yml)

if [ "$DOWN" -eq 1 ]; then
    echo "Stopping all services..."
    exec docker compose "${compose_files[@]}" down
fi

if [ ! -f .env ]; then
    echo "WARNING: .env not found — copy .env.example to .env first." >&2
    exit 1
fi

[ "$PROD" -eq 1 ] && mode="PROD (baked code, no reload)" || mode="DEV (hot reload)"
up_args=(compose "${compose_files[@]}" up -d)
[ "$NO_BUILD" -eq 0 ] && up_args+=(--build)

echo "Starting all services [$mode]: postgres, redis, web, celery_worker, celery_beat, frontend..."
docker "${up_args[@]}"

docker compose "${compose_files[@]}" ps

echo
echo "Frontend (client zone): http://localhost:${FRONTEND_PORT:-3000}"
echo "Admin zone (direct):    http://localhost:${ADMIN_PORT:-3001}"
echo "Backend:  http://localhost:${WEB_PORT:-8000}"

if [ "$NO_LOGS" -eq 0 ]; then
    echo
    echo "Following logs (Ctrl-C to stop tailing; containers keep running)..."
    exec docker compose "${compose_files[@]}" logs -f
fi
