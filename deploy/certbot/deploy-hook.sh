#!/bin/sh
# =============================================================================
# certbot --deploy-hook: runs ONLY after a certificate is successfully issued or
# renewed. Copies the fresh leaf + chain from certbot's lineage dir into the
# directory nginx reads (mounted at /certs == ./nginx/certs on the host).
#
# certbot sets $RENEWED_LINEAGE to /etc/letsencrypt/live/<domain> for us.
# -L dereferences certbot's symlinks so nginx gets real files, not dangling
# links into a volume it doesn't mount.
# =============================================================================
set -eu

SRC="${RENEWED_LINEAGE:?certbot did not set RENEWED_LINEAGE}"
cp -L "$SRC/fullchain.pem" /certs/fullchain.pem
cp -L "$SRC/privkey.pem"   /certs/privkey.pem
echo "deploy-hook: installed renewed cert from $SRC into /certs"
