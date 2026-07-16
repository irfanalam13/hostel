# Secrets Management & Rotation Runbook

**Phase 1, §9.** How secrets are stored, encrypted, scanned, and rotated.

## Model

| Layer | Where | What |
| --- | --- | --- |
| **Runtime (system of record)** | Render / Vercel dashboard env vars (`sync: false`) | The live values production reads. |
| **Repo (encrypted)** | `secrets/*.enc.env`, `*.sops.yaml` via SOPS + age | Reviewable, version-controlled, encrypted-at-rest copies + IaC inputs. |
| **CI** | GitHub Actions secrets | `GITHUB_TOKEN` (ambient), `SOPS_AGE_KEY`, deploy creds. |
| **Local dev** | `.env` / `.env.local` (git-ignored) | Never committed. Age private key at `~/.config/sops/age/keys.txt`. |

Guardrails: gitleaks runs both as a **local pre-commit hook** (`.pre-commit-config.yaml`)
and in **CI** (`security.yml`); `.gitignore` blocks `.env`, `.env.*`, and age
private keys; the `sops-encryption` pre-commit hook rejects plaintext under
`secrets/`.

## One-time setup

```bash
# 1. Generate your age key (PUBLIC key is printed; keep the file private)
age-keygen -o ~/.config/sops/age/keys.txt

# 2. Put the printed `age1...` PUBLIC key into .sops.yaml (replace the placeholder)

# 3. Add the PRIVATE key to CI so pipelines can decrypt:
#    GitHub → Settings → Secrets → Actions → new secret SOPS_AGE_KEY = <contents of keys.txt>

# 4. Enable the local hooks
pip install pre-commit && pre-commit install
pre-commit run --all-files
```

## Secret inventory (authoritative list: `.env.example` / `ML_hostel/.env.example`)

| Secret | Used by | Store | Rotation notes |
| --- | --- | --- | --- |
| `DJANGO_SECRET_KEY` | backend | Render | Rotating invalidates sessions/signed tokens — expect logouts. |
| `ML_SHARED_SECRET` | backend **and** `hostel-ml` | Render (both) | **Must be identical on both services.** Rotate both in one window (see below). |
| `ML_GEMINI_API_KEY` | `hostel-ml` | Render | Rotate in Google AI console, then update Render. |
| `POSTGRES_PASSWORD` / `DATABASE_URL` | backend, Celery | Render managed PG | Rotate via DB provider; update all consumers. |
| `REDIS_URL` | backend, Celery | Render | Rotate credential, update consumers. |
| `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` | backend (Brevo SMTP) | Render | Regenerate SMTP key in Brevo; mind authorized-IP allowlist. |
| `VAPID_PRIVATE_KEY` / `VAPID_SUBJECT` | backend (web push) | Render | Rotating invalidates existing push subscriptions — clients re-subscribe. Public key `NEXT_PUBLIC_VAPID_PUBLIC_KEY` is not secret. |
| `BACKUP_ENCRYPTION_KEY` | `apps/backups` | Render | **Do not lose** — old backups become undecryptable. Keep an escrow copy. |
| `SENTRY_DSN` | backend/frontend | Render/Vercel | Low sensitivity; rotate via Sentry if leaked. |
| `SOPS_AGE_KEY` | CI | GitHub Actions secret | Rotate = new age key + re-encrypt `secrets/**` + update `.sops.yaml`. |
| `GHCR_USERNAME` / `GHCR_TOKEN` | deploy workflows | GitHub Actions secret | Only for the (inactive) VPS path; scope PAT to `read:packages`. |
| `*_SSH_KEY` / `*_SSH_HOST` | VPS deploy (inactive) | GitHub Environments | N/A while PaaS is canonical. |

## Rotation — general procedure

1. Generate the new value at the provider.
2. Update the **runtime** store (Render/Vercel) first.
3. Update the encrypted repo copy: `sops secrets/<env>.enc.env` → edit → save.
4. Redeploy the affected service (Continuous Delivery promotion — see `CD_STRATEGY.md`).
5. Verify `/health/` endpoints; revoke the old value at the provider.
6. Note the rotation date in the change log / PR.

### Special case — `ML_SHARED_SECRET` (dual-service, zero-downtime-sensitive)
The backend mints and the ML service verifies the same HS256 secret
(`apps/assistant/tokens.py` ↔ `ML_hostel/app/security.py`). A mismatch breaks
every AI request. Rotate in a short window: set the new value on **both** Render
services, then trigger both deploys close together. In-flight context tokens
(TTL = `ML_TOKEN_TTL`) minted under the old secret fail until re-issued — keep the
window short or drain first.

## Known items to action now

- 🔴 **Rotate the Gemini API key** that was shared in chat earlier (already flagged
  in `ML_hostel/render.yaml`). Treat it as compromised.
- 🟠 **`.env.local` was not covered by the old `*.env` ignore rule** — fixed in
  `.gitignore` (`.env.*`). Confirm it was never committed:
  `git log --all --full-history -- .env.local` (should be empty).
- 🟠 Scope the GHCR PAT and any deploy tokens to least privilege.

_Related: `.sops.yaml`, `secrets/README.md`, `.pre-commit-config.yaml`,
`.gitleaks.toml`, `docs/CD_STRATEGY.md`._
