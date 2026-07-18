#!/usr/bin/env bash
# =============================================================================
# update_worker.sh — pull latest code/images, rebuild, and roll the worker.
#
#   git pull  ->  docker compose pull  ->  docker compose build  ->  up -d
#
# Lighter than deploy_worker.sh (no explicit stop / prune). Use for routine
# code updates once the worker is already running.
# Pass --with-beat to include the optional Beat scheduler.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/backend/docker-compose.worker.yml"

if [ -t 1 ]; then C_INFO='\033[1;34m'; C_OK='\033[1;32m'; C_OFF='\033[0m'; else C_INFO=''; C_OK=''; C_OFF=''; fi
log() { printf "${C_INFO}[update %s]${C_OFF} %s\n" "$(date +%H:%M:%S)" "$*"; }

PROFILE_ARGS=()
[ "${1:-}" = "--with-beat" ] && PROFILE_ARGS=(--profile beat)
COMPOSE=(docker compose -f "$COMPOSE_FILE" "${PROFILE_ARGS[@]}")

log "git pull"
git -C "$REPO_ROOT" pull --ff-only

# `pull` only affects services with an `image:` and no local build (none here,
# the worker is built locally) — harmless, kept for parity with the runbook.
log "docker compose pull"
"${COMPOSE[@]}" pull --ignore-buildable 2>/dev/null || "${COMPOSE[@]}" pull || true

log "docker compose build"
"${COMPOSE[@]}" build

log "docker compose up -d"
"${COMPOSE[@]}" up -d --wait --wait-timeout 120

printf "${C_OK}[update %s] OK worker updated${C_OFF}\n" "$(date +%H:%M:%S)"
"${COMPOSE[@]}" ps
