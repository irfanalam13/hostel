#!/usr/bin/env bash
# =============================================================================
# Health-gated rollout for the Hostel SaaS on a single Docker host.
#
#   deploy.sh <backend_image> <client_image> <admin_image>
#
# The client (marketing) image runs the compose `frontend` service and the
# admin zone image runs the `admin` service (FRONTEND_IMAGE / ADMIN_IMAGE in
# .env).
#
# Steps: record current images (for rollback) -> registry login -> pull new
# images -> safety backup (pg_dump) -> apply migrations -> recreate services
# waiting for healthchecks -> verify health endpoints. If anything fails AFTER
# the running containers were touched, it auto-rolls back to the previous images
# and exits non-zero so CI marks the deploy failed.
#
# Required env (typically from deploy/.env or the CI SSH session):
#   GHCR_USER, GHCR_TOKEN   registry credentials (read:packages)
#   POSTGRES_USER/DB        used by the safety pg_dump
# =============================================================================
set -euo pipefail

BACKEND_IMAGE_NEW="${1:?usage: deploy.sh <backend_image> <client_image> <admin_image>}"
FRONTEND_IMAGE_NEW="${2:?usage: deploy.sh <backend_image> <client_image> <admin_image>}"
ADMIN_IMAGE_NEW="${3:?usage: deploy.sh <backend_image> <client_image> <admin_image>}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ENV_FILE="$SCRIPT_DIR/.env"
COMPOSE=(docker compose -f docker-compose.prod.yml --env-file "$ENV_FILE")
ROLLBACK_STATE="$SCRIPT_DIR/.rollback-state"
BACKUP_DIR="$SCRIPT_DIR/backups"
TS="$(date +%Y%m%d-%H%M%S)"

log() { echo "[deploy $(date +%H:%M:%S)] $*"; }

# Read the currently-deployed image refs so we can roll back to them.
current_image() { grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2- || true; }
BACKEND_IMAGE_OLD="$(current_image BACKEND_IMAGE)"
FRONTEND_IMAGE_OLD="$(current_image FRONTEND_IMAGE)"
ADMIN_IMAGE_OLD="$(current_image ADMIN_IMAGE)"

rolled_back=0
rollback() {
  [ "$rolled_back" = "1" ] && return
  rolled_back=1
  if [ -z "$BACKEND_IMAGE_OLD" ] || [ -z "$FRONTEND_IMAGE_OLD" ] || [ -z "$ADMIN_IMAGE_OLD" ]; then
    log "!! no previous images recorded — cannot auto-rollback"; return
  fi
  log "!! rolling back to ${BACKEND_IMAGE_OLD} / ${FRONTEND_IMAGE_OLD} / ${ADMIN_IMAGE_OLD}"
  set_image BACKEND_IMAGE "$BACKEND_IMAGE_OLD"
  set_image FRONTEND_IMAGE "$FRONTEND_IMAGE_OLD"
  set_image ADMIN_IMAGE "$ADMIN_IMAGE_OLD"
  "${COMPOSE[@]}" up -d --wait --wait-timeout 180 || log "!! rollback rollout reported errors"
}

set_image() { # set_image VAR value  — upsert a KEY=value line in .env
  local key="$1" val="$2"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >> "$ENV_FILE"
  fi
}

# ---- 1. Registry login ------------------------------------------------------
log "logging in to ghcr.io"
echo "${GHCR_TOKEN:?set GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USER:?set GHCR_USER}" --password-stdin

# ---- 2. Pull new images (before touching anything running) ------------------
log "pulling ${BACKEND_IMAGE_NEW}"
docker pull "$BACKEND_IMAGE_NEW"
log "pulling ${FRONTEND_IMAGE_NEW}"
docker pull "$FRONTEND_IMAGE_NEW"
log "pulling ${ADMIN_IMAGE_NEW}"
docker pull "$ADMIN_IMAGE_NEW"

# ---- 3. Safety backup (pg_dump) --------------------------------------------
mkdir -p "$BACKUP_DIR"
log "backing up database -> backups/db-${TS}.sql.gz"
"${COMPOSE[@]}" exec -T postgres pg_dump -U "${POSTGRES_USER:-hostel}" "${POSTGRES_DB:-hostel}" \
  | gzip > "$BACKUP_DIR/db-${TS}.sql.gz"
# Keep the 10 most recent safety dumps.
ls -1t "$BACKUP_DIR"/db-*.sql.gz 2>/dev/null | tail -n +11 | xargs -r rm -f

# Save rollback state now that we know the previous images are still running.
printf 'BACKEND_IMAGE=%s\nFRONTEND_IMAGE=%s\nADMIN_IMAGE=%s\n' "$BACKEND_IMAGE_OLD" "$FRONTEND_IMAGE_OLD" "$ADMIN_IMAGE_OLD" > "$ROLLBACK_STATE"

# ---- 4. From here a failure means we must roll back -------------------------
trap 'rc=$?; if [ $rc -ne 0 ]; then log "FAILED (rc=$rc)"; rollback; fi; exit $rc' EXIT

set_image BACKEND_IMAGE "$BACKEND_IMAGE_NEW"
set_image FRONTEND_IMAGE "$FRONTEND_IMAGE_NEW"
set_image ADMIN_IMAGE "$ADMIN_IMAGE_NEW"

# ---- 5. Migration safety: review the plan, then apply -----------------------
log "migration plan:"
"${COMPOSE[@]}" run --rm web python manage.py migrate --plan
log "applying migrations"
"${COMPOSE[@]}" run --rm web python manage.py migrate --noinput

# ---- 6. Health-gated rollout ------------------------------------------------
log "recreating services (waiting for healthchecks)"
"${COMPOSE[@]}" up -d --wait --wait-timeout 300

# ---- 7. Explicit health verification ---------------------------------------
log "verifying health endpoints"
for path in /health/ /health/database/ /health/cache/ /health/celery/; do
  code="$("${COMPOSE[@]}" exec -T web sh -c "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000${path}")"
  [ "$code" = "200" ] || { log "health ${path} -> ${code}"; exit 1; }
  log "ok ${path}"
done

# ---- 8. Success: clean up the trap + dangling images ------------------------
trap - EXIT
docker image prune -f >/dev/null 2>&1 || true
log "deploy OK: ${BACKEND_IMAGE_NEW} / ${FRONTEND_IMAGE_NEW} / ${ADMIN_IMAGE_NEW}"
