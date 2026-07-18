#!/usr/bin/env bash
# =============================================================================
# deploy_worker.sh — build & (re)deploy the Oracle Celery worker from scratch.
#
# Idempotent full rollout:
#   1. pull the latest code (git)
#   2. build the worker image
#   3. stop the previous worker
#   4. start the new worker (detached, with restart policy)
#   5. prune dangling images
#   6. show running containers
#
# Exits non-zero on the first failure. Run from anywhere:  ./scripts/deploy_worker.sh
# Pass --with-beat to also start the optional Celery Beat scheduler.
# =============================================================================
set -euo pipefail

# ---- Resolve paths (works regardless of cwd) --------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/backend/docker-compose.worker.yml"
ENV_FILE="$REPO_ROOT/backend/.env.production"

# ---- Colored logging --------------------------------------------------------
if [ -t 1 ]; then
  C_INFO='\033[1;34m'; C_OK='\033[1;32m'; C_WARN='\033[1;33m'; C_ERR='\033[1;31m'; C_OFF='\033[0m'
else
  C_INFO=''; C_OK=''; C_WARN=''; C_ERR=''; C_OFF=''
fi
log()  { printf "${C_INFO}[deploy %s]${C_OFF} %s\n" "$(date +%H:%M:%S)" "$*"; }
ok()   { printf "${C_OK}[deploy %s] OK %s${C_OFF}\n" "$(date +%H:%M:%S)" "$*"; }
warn() { printf "${C_WARN}[deploy %s] ! %s${C_OFF}\n" "$(date +%H:%M:%S)" "$*"; }
die()  { printf "${C_ERR}[deploy %s] x %s${C_OFF}\n" "$(date +%H:%M:%S)" "$*" >&2; exit 1; }

# ---- Compose profile (optionally include beat) ------------------------------
PROFILE_ARGS=()
if [ "${1:-}" = "--with-beat" ]; then
  PROFILE_ARGS=(--profile beat)
  log "Beat scheduler ENABLED for this deploy"
fi
COMPOSE=(docker compose -f "$COMPOSE_FILE" "${PROFILE_ARGS[@]}")

# ---- Preflight --------------------------------------------------------------
command -v docker >/dev/null 2>&1 || die "docker is not installed"
docker compose version >/dev/null 2>&1 || die "docker compose v2 plugin is not available"
[ -f "$COMPOSE_FILE" ] || die "compose file not found: $COMPOSE_FILE"
[ -f "$ENV_FILE" ] || die "missing $ENV_FILE — copy backend/.env.production.example and fill it in"

# ---- 1. Pull latest code ----------------------------------------------------
if git -C "$REPO_ROOT" rev-parse --git-dir >/dev/null 2>&1; then
  log "pulling latest code (git)"
  git -C "$REPO_ROOT" pull --ff-only || die "git pull failed"
else
  warn "not a git checkout — skipping git pull"
fi

# ---- 2. Build the worker image ----------------------------------------------
log "building worker image"
"${COMPOSE[@]}" build || die "image build failed"

# ---- 3. Stop the previous worker --------------------------------------------
log "stopping previous worker (if any)"
"${COMPOSE[@]}" down --remove-orphans || warn "nothing to stop"

# ---- 4. Start the new worker ------------------------------------------------
log "starting worker (detached, waiting for health)"
"${COMPOSE[@]}" up -d --wait --wait-timeout 120 || die "worker failed to become healthy"

# ---- 5. Prune dangling images -----------------------------------------------
log "pruning dangling images"
docker image prune -f >/dev/null 2>&1 || true

# ---- 6. Show running containers ---------------------------------------------
"${COMPOSE[@]}" ps
ok "worker deployed"
