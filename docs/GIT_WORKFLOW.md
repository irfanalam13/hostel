# Git Workflow & Branch Protection

Roadmap Prompt 09 — a professional, protected GitFlow-style workflow.

## Branches

| Branch | Purpose | Deploys to | Protected |
| --- | --- | --- | --- |
| `main` | Production-ready, released code. Always green. | Production (on `v*` tag) | ✅ strict |
| `develop` | Integration branch for the next release. | Staging (auto) | ✅ |
| `feature/*` | New work, branched off `develop`. | — | — |
| `release/*` | Stabilize a release; only fixes + version bumps. | Staging | — |
| `hotfix/*` | Urgent production fix, branched off `main`. | Production via tag | — |

### Flow

```
feature/x ─┐
           ├─PR─▶ develop ──▶ release/1.4 ──PR──▶ main ──tag v1.4.0──▶ Production
hotfix/y ──┴────────────────────────────────────▶ main ──tag v1.4.1──▶ Production
                                                   └─back-merge─▶ develop
```

- Branch `feature/*` and `release/*` off `develop`; `hotfix/*` off `main`.
- Merge to `develop` (auto-deploys to **staging**) → verify → open `release/*` →
  PR into `main`.
- Tag `main` with `vX.Y.Z` to trigger the **production** deploy (manual approval).
- Always back-merge `main` into `develop` after a hotfix.

## Rules (enforced by branch protection)

- **No direct pushes** to `main` or `develop` — changes land via PR only.
- **Required approvals**: `main` = 2 (incl. code owners), `develop` = 1.
- **Required green CI**: lint, tests, production validation, security, and
  Conventional-Commits checks must pass (strict — branch must be up to date).
- **Linear history**, **no force-push**, **no branch deletion**.
- **Conversation resolution** required before merge.
- **Stale reviews dismissed** on new pushes; last push must be approved.
- Signed commits — optional; enable in Settings → Branches if your team uses
  commit signing (`git config commit.gpgsign true`).

## Conventional Commits

PR titles and commits follow [Conventional Commits](https://www.conventionalcommits.org/)
(`feat`, `fix`, `docs`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`,
`revert`, `style`). Enforced by `.github/workflows/commit-lint.yml` using
`.commitlintrc.yml`. This keeps history machine-readable and enables automated
changelog/version tooling later.

## Applying protection

Branch protection is configured as code:

```bash
gh auth login                       # token with repo admin scope
./scripts/setup-branch-protection.sh
```

Re-run after renaming any CI job (the required check **names** must match).

## Environments (manual approval)

In **Settings → Environments**, create:

- `staging` — no reviewers (auto-deploy from `develop`).
- `production` — **required reviewers** (manual approval) and a deployment-branch
  rule limiting deploys to `v*` tags. This is what gates production in
  `deploy-production.yml`.
