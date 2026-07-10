#!/usr/bin/env bash
# =============================================================================
# Manual rollback to the previously-deployed images recorded by deploy.sh in
# deploy/.rollback-state. Use when a regression is found AFTER a deploy that
# nonetheless passed health checks.
#
#   ./rollback.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

ENV_FILE="$SCRIPT_DIR/.env"
STATE="$SCRIPT_DIR/.rollback-state"
COMPOSE=(docker compose -f docker-compose.prod.yml --env-file "$ENV_FILE")

[ -f "$STATE" ] || { echo "no rollback state at $STATE"; exit 1; }
# shellcheck disable=SC1090
. "$STATE"
: "${BACKEND_IMAGE:?no BACKEND_IMAGE in state}" "${FRONTEND_IMAGE:?no FRONTEND_IMAGE in state}"
# ADMIN_IMAGE may be absent in state files written before the client/admin
# zone split — tolerate that and only revert it when recorded.
ADMIN_IMAGE="${ADMIN_IMAGE:-}"

echo "[rollback] reverting to ${BACKEND_IMAGE} / ${FRONTEND_IMAGE}${ADMIN_IMAGE:+ / ${ADMIN_IMAGE}}"
sed -i "s|^BACKEND_IMAGE=.*|BACKEND_IMAGE=${BACKEND_IMAGE}|"  "$ENV_FILE"
sed -i "s|^FRONTEND_IMAGE=.*|FRONTEND_IMAGE=${FRONTEND_IMAGE}|" "$ENV_FILE"
[ -z "$ADMIN_IMAGE" ] || sed -i "s|^ADMIN_IMAGE=.*|ADMIN_IMAGE=${ADMIN_IMAGE}|" "$ENV_FILE"

docker pull "$BACKEND_IMAGE" && docker pull "$FRONTEND_IMAGE"
[ -z "$ADMIN_IMAGE" ] || docker pull "$ADMIN_IMAGE"
"${COMPOSE[@]}" up -d --wait --wait-timeout 300
echo "[rollback] done"
