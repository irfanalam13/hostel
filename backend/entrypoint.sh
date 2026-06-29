#!/bin/sh
# =============================================================================
# Container entrypoint for the Django backend.
# Applies database migrations (so the schema exists in every environment,
# including a fresh production database), then hands off to the container's
# command (Gunicorn by default; Celery worker/beat in their own services).
#
#   RUN_MIGRATIONS=1   apply migrations before starting (default: 1)
#                      set to 0 on sidecar services (Celery) to avoid races
#   COLLECT_STATIC=1   re-run collectstatic at boot (default: 0; done at build)
# =============================================================================
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
    # Generate any missing migrations from the committed models, then apply them.
    # makemigrations is normally a no-op (migrations are committed to the repo),
    # but guarantees the schema is in sync even on a brand-new database.
    echo "[entrypoint] Making migrations (no-op if already committed)..."
    python manage.py makemigrations --noinput
    echo "[entrypoint] Applying database migrations..."
    python manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-0}" = "1" ]; then
    echo "[entrypoint] Collecting static files..."
    python manage.py collectstatic --noinput
fi

echo "[entrypoint] Starting: $*"
exec "$@"
