#!/usr/bin/env bash
# =============================================================================
# FIRST-TIME Let's Encrypt issuance on the VPS. Run once per domain.
#
#   cd deploy && ./certbot/init-letsencrypt.sh            # real (production) cert
#   cd deploy && STAGING=1 ./certbot/init-letsencrypt.sh  # LE staging (rate-limit-safe dry run)
#
# Reads DOMAIN + CERTBOT_EMAIL from deploy/.env. Solves the chicken-and-egg
# (nginx can't start without a cert, certbot can't validate without nginx
# serving :80) by first dropping a throwaway self-signed cert so nginx boots,
# then replacing it with the real one via the http-01 webroot challenge.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # -> deploy/
cd "$SCRIPT_DIR"

set -a; . ./.env; set +a
: "${DOMAIN:?set DOMAIN in deploy/.env}"
: "${CERTBOT_EMAIL:?set CERTBOT_EMAIL in deploy/.env}"

COMPOSE=(docker compose -f docker-compose.prod.yml -f certbot/docker-compose.certbot.yml --env-file .env)
CERTS_DIR="./nginx/certs"
mkdir -p "$CERTS_DIR"

log() { echo "[init-le] $*"; }

# --- 1. Throwaway self-signed cert so nginx can start and serve the challenge.
if [ ! -s "$CERTS_DIR/fullchain.pem" ]; then
  log "no cert present — generating a temporary self-signed cert for ${DOMAIN}"
  docker run --rm -v "$(pwd)/$CERTS_DIR":/c alpine:3.20 sh -c \
    "apk add --no-cache openssl >/dev/null && \
     openssl req -x509 -newkey rsa:2048 -nodes -days 1 \
       -keyout /c/privkey.pem -out /c/fullchain.pem -subj '/CN=${DOMAIN}'"
fi

# --- 2. Start the stack (nginx now boots and serves /.well-known on :80). -----
log "starting stack"
"${COMPOSE[@]}" up -d --wait web frontend nginx

# --- 3. Request the real certificate via the webroot challenge. ---------------
STAGING_FLAG=""
[ "${STAGING:-0}" = "1" ] && { STAGING_FLAG="--staging"; log "using LE STAGING environment"; }

log "requesting certificate for ${DOMAIN}"
"${COMPOSE[@]}" run --rm certbot certonly \
  --webroot -w /var/www/certbot \
  -d "${DOMAIN}" \
  --email "${CERTBOT_EMAIL}" \
  --agree-tos --no-eff-email --non-interactive \
  --keep-until-expiring \
  --deploy-hook /deploy-hook.sh \
  $STAGING_FLAG

# --- 4. Reload nginx to pick up the real cert (zero downtime). ----------------
log "reloading nginx"
"${COMPOSE[@]}" exec nginx nginx -s reload

log "done. Verify:  curl -sI https://${DOMAIN} | grep -i strict-transport"
log "Add renewal to cron (see certbot/renew.sh):"
log "  0 3 * * *  cd $SCRIPT_DIR && ./certbot/renew.sh >> /var/log/certbot-renew.log 2>&1"
