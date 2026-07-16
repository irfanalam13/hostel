#!/usr/bin/env bash
# Roll a Render service back to its previous successfully-live deploy (Phase 3, §3).
# Used as the --rollback-cmd for metric_gate.py, or standalone.
#
# Env:
#   RENDER_API_KEY       Render API key (Bearer).
#   RENDER_SERVICE_ID    Service to roll back (e.g. srv-xxxxxxxx).
# Usage: bash deploy/scripts/rollback_render.sh
set -euo pipefail

: "${RENDER_API_KEY:?RENDER_API_KEY is required}"
: "${RENDER_SERVICE_ID:?RENDER_SERVICE_ID is required}"

API="https://api.render.com/v1/services/${RENDER_SERVICE_ID}"
AUTH=(-H "Authorization: Bearer ${RENDER_API_KEY}" -H "Accept: application/json")

# Most recent deploys, newest first.
deploys="$(curl -fsS "${AUTH[@]}" "${API}/deploys?limit=10")"

# The current live deploy is the newest 'live'; the rollback target is the one
# before it that reached 'live' (i.e. the last-known-good).
prev_id="$(python3 - "$deploys" <<'PY'
import json, sys
deploys = json.loads(sys.argv[1])
live = [d["deploy"] for d in deploys if d["deploy"]["status"] in ("live", "deactivated")]
# newest-first already; index 0 = current, index 1 = previous good
print(live[1]["id"] if len(live) > 1 else "")
PY
)"

if [ -z "$prev_id" ]; then
  echo "::error::No previous live deploy found to roll back to." >&2
  exit 1
fi

echo "Rolling ${RENDER_SERVICE_ID} back to deploy ${prev_id}"
curl -fsS -X POST "${AUTH[@]}" -H "Content-Type: application/json" \
  -d "{\"deployId\":\"${prev_id}\"}" "${API}/rollback" >/dev/null
echo "✓ Rollback requested."
