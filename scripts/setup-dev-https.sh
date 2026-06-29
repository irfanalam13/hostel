#!/usr/bin/env bash
# =============================================================================
# Issue a locally-trusted TLS certificate for https://localhost development
# (macOS / Linux / WSL). Windows users: use scripts/setup-dev-https.ps1.
#
# Uses mkcert (https://github.com/FiloSottile/mkcert) to install a local CA into
# the system + browser trust stores and issue a leaf for localhost/127.0.0.1/::1.
# Output goes to deploy/dev/certs/ where the dev nginx proxy mounts it.
#
#   bash scripts/setup-dev-https.sh
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="$REPO_ROOT/deploy/dev/certs"
mkdir -p "$CERT_DIR"

# --- 1. Ensure mkcert is installed ------------------------------------------
if ! command -v mkcert >/dev/null 2>&1; then
  echo "mkcert not found — attempting to install..."
  if command -v brew >/dev/null 2>&1; then
    brew install mkcert nss            # nss = Firefox trust support
  elif command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y libnss3-tools
    # mkcert isn't in all apt repos; grab the latest release binary.
    arch="$(dpkg --print-architecture 2>/dev/null || uname -m)"
    case "$arch" in amd64|x86_64) m=amd64;; arm64|aarch64) m=arm64;; *) m=amd64;; esac
    url="https://dl.filippo.io/mkcert/latest?for=linux/$m"
    sudo curl -fsSL "$url" -o /usr/local/bin/mkcert
    sudo chmod +x /usr/local/bin/mkcert
  else
    echo "Install mkcert manually: https://github.com/FiloSottile/mkcert#installation" >&2
    exit 1
  fi
fi

# --- 2. Install the local CA into the trust store ---------------------------
echo "Installing mkcert local CA (you may be prompted for sudo)..."
mkcert -install

# --- 3. Issue the leaf certificate ------------------------------------------
echo "Issuing certificate for localhost / 127.0.0.1 / ::1 ..."
( cd "$CERT_DIR" && mkcert -key-file localhost-key.pem -cert-file localhost.pem localhost 127.0.0.1 ::1 )

cat <<EOF

Done. Dev certificate written to:
  $CERT_DIR/localhost.pem
  $CERT_DIR/localhost-key.pem

Next:
  1. In .env set:
       NEXT_PUBLIC_API_BASE_URL=https://localhost/api
       CSRF_TRUSTED_ORIGINS=https://localhost,http://localhost:3000
  2. docker compose -f docker-compose.yml -f deploy/dev/docker-compose.https.yml up --build
  3. Open https://localhost
EOF
