#!/bin/sh
# =============================================================================
# Container entrypoint for the Django backend.
# Optionally applies database migrations, then hands off to the container's
# command (Gunicorn by default; Celery worker/beat in their own services).
#
#   RUN_MIGRATIONS=1   apply `migrate --noinput` before starting (default: 0)
#   COLLECT_STATIC=1   re-run collectstatic at boot (default: 0; done at build)
# =============================================================================
set -e

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    echo "[entrypoint] Applying database migrations..."
    python manage.py migrate --noinput
fi

if [ "${COLLECT_STATIC:-0}" = "1" ]; then
    echo "[entrypoint] Collecting static files..."
    python manage.py collectstatic --noinput
fi

echo "[entrypoint] Starting: $*"
exec "$@"
