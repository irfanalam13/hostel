#!/usr/bin/env bash
# =============================================================================
# Apply branch protection to `main` and `develop` via the GitHub API (gh CLI).
# Roadmap Prompt 09. Idempotent — safe to re-run after changing CI job names.
#
#   gh auth login           # once, with a token that has 'repo' admin scope
#   ./scripts/setup-branch-protection.sh [owner/repo]
#
# Without an argument it targets the current repo (gh infers it).
# =============================================================================
set -euo pipefail

REPO="${1:-$(gh repo view --json nameWithOwner -q .nameWithOwner)}"
echo "Configuring branch protection for ${REPO}"

# Required status checks — must match the check-run NAMES produced by the
# workflows (matrix jobs include the matrix value). Adjust if you rename jobs.
read -r -d '' CONTEXTS <<'JSON' || true
[
  "Lint (backend)",
  "Lint (frontend)",
  "Test + migrations (backend)",
  "Test (frontend)",
  "Build backend image",
  "Build frontend image",
  "Django deployment checks (DEBUG=False)",
  "Stack boot + health (docker compose)",
  "Secret scan (gitleaks)",
  "Python deps (pip-audit)",
  "Node deps (npm audit)",
  "Trivy (filesystem)",
  "Conventional Commits"
]
JSON

protect() {
  local branch="$1" approvals="$2" enforce_admins="$3"
  echo "  -> ${branch} (approvals=${approvals}, enforce_admins=${enforce_admins})"
  jq -n \
    --argjson contexts "$CONTEXTS" \
    --argjson approvals "$approvals" \
    --argjson admins "$enforce_admins" \
    '{
      required_status_checks: { strict: true, contexts: $contexts },
      enforce_admins: $admins,
      required_pull_request_reviews: {
        required_approving_review_count: $approvals,
        require_code_owner_reviews: true,
        dismiss_stale_reviews: true,
        require_last_push_approval: true
      },
      required_linear_history: true,
      allow_force_pushes: false,
      allow_deletions: false,
      required_conversation_resolution: true,
      restrictions: null
    }' \
  | gh api -X PUT "repos/${REPO}/branches/${branch}/protection" \
      -H "Accept: application/vnd.github+json" --input -  >/dev/null
}

# main: strictest — 2 approvals, rules apply to admins too.
protect main 2 true
# develop: integration branch — 1 approval.
protect develop 1 false

echo "Done. Direct pushes to main/develop are now blocked; PRs + green CI required."
