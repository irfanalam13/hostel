#!/usr/bin/env bash
# DR game-day: a guided, timed recovery exercise (Phase 5, §6).
#
# Simulates data loss for ONE hostel on a STAGING environment and recovers it
# from a backup, measuring RTO. Destructive by design — it refuses to run unless
# DR_GAMEDAY_ENV=staging and --confirm <HOSTEL_CODE> are both given.
#
# Usage (inside the backend container / venv, against STAGING):
#   DR_GAMEDAY_ENV=staging bash deploy/scripts/dr_gameday.sh H-ABC123 --confirm H-ABC123
#
# Steps: fresh backup → verify → simulate loss (dry-run restore first) →
# destructive restore from the backup → integrity verify. Times the recovery.
set -euo pipefail

HOSTEL="${1:-}"
CONFIRM_FLAG="${2:-}"
CONFIRM_VAL="${3:-}"

die() { echo "::error::$*" >&2; exit 1; }

[ -n "$HOSTEL" ] || die "Usage: dr_gameday.sh <HOSTEL_CODE> --confirm <HOSTEL_CODE>"
[ "${DR_GAMEDAY_ENV:-}" = "staging" ] || die "Refusing to run: set DR_GAMEDAY_ENV=staging (never run on production)."
[ "$CONFIRM_FLAG" = "--confirm" ] && [ "$CONFIRM_VAL" = "$HOSTEL" ] || die "Pass --confirm $HOSTEL to authorise the destructive exercise."

mgr() { python manage.py "$@"; }

echo "== DR game-day for ${HOSTEL} (staging) =="

echo "-- 1. Take a fresh, verified backup"
mgr dr_backup --hostel "$HOSTEL"

echo "-- 2. Verify stored backups for the hostel"
mgr dr_verify --hostel "$HOSTEL"

echo "-- 3. Dry-run the restore (plan only, no writes)"
mgr dr_restore --hostel "$HOSTEL" --dry-run

echo "-- 4. DESTRUCTIVE restore from the latest backup (times recovery)"
START=$(date +%s)
mgr dr_restore --hostel "$HOSTEL" --force --confirm "$HOSTEL"
END=$(date +%s)
RTO=$((END - START))

echo "-- 5. Post-recovery integrity verify"
mgr dr_verify --hostel "$HOSTEL"

echo "== Game-day complete: recovery took ${RTO}s (RTO). Record it in the runbook. =="
