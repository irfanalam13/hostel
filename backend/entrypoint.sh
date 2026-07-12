#!/bin/sh
# =============================================================================
# Container entrypoint for the Django backend.
# Applies database migrations (so the schema exists in every environment,
# including a fresh production database), then hands off to the container's
# command (Gunicorn by default; Celery worker/beat in their own services).
#
#   RUN_MIGRATIONS=1   apply committed migrations before starting (default: 1)
#                      set to 0 on sidecar services (Celery) to avoid races
#   MAKE_MIGRATIONS=1  ALSO generate migrations from models at boot (default: 0)
#                      DEV ONLY — never enable in production. Generating
#                      migrations against a live database can create unexpected
#                      schema changes; production ships committed migrations only.
#   COLLECT_STATIC=1   re-run collectstatic at boot (default: 0; done at build)
# =============================================================================
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    # DEV convenience: regenerate migrations from models before applying. Off by
    # default so production only ever runs the migrations committed to the repo.
    if [ "${MAKE_MIGRATIONS:-0}" = "1" ]; then
        echo "[entrypoint] MAKE_MIGRATIONS=1 — generating migrations from models (dev only)..."
        python manage.py makemigrations --noinput
    fi
    echo "[entrypoint] Applying database migrations..."
    python manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-0}" = "1" ]; then
    echo "[entrypoint] Collecting static files..."
    python manage.py collectstatic --noinput
fi

echo "[entrypoint] Starting: $*"
exec "$@"
