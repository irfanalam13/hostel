#!/usr/bin/env bash
# =============================================================================
# Idempotent Let's Encrypt renewal — safe to run daily from cron. certbot only
# renews certs inside their 30-day-before-expiry window; otherwise it's a no-op.
# The --deploy-hook copies a renewed cert into ./nginx/certs and we then reload
# nginx (a reload is graceful: existing connections finish on the old workers).
#
#   crontab -e
#   0 3 * * *  cd /home/USER/hostel/deploy && ./certbot/renew.sh >> /var/log/certbot-renew.log 2>&1
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # -> deploy/
cd "$SCRIPT_DIR"

COMPOSE=(docker compose -f docker-compose.prod.yml -f certbot/docker-compose.certbot.yml --env-file .env)

echo "[renew $(date -Is)] checking renewal"
"${COMPOSE[@]}" run --rm certbot renew \
  --webroot -w /var/www/certbot \
  --deploy-hook /deploy-hook.sh

# Reload regardless (cheap, graceful); a no-renewal run leaves the cert unchanged.
"${COMPOSE[@]}" exec -T nginx nginx -s reload
echo "[renew $(date -Is)] nginx reloaded"
