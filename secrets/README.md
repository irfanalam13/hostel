# `secrets/` — SOPS-encrypted material only

Everything here is committed **encrypted** with SOPS + age (see `../.sops.yaml`).
Never put a plaintext secret in this directory — the pre-commit `sops-encryption`
hook and the CI gitleaks scan will reject it.

## Conventions
- Encrypted env files: `*.enc.env`  (e.g. `staging.enc.env`, `prod.enc.env`)
- Encrypted manifests/tfvars: `*.sops.yaml`, `*.sops.json`

## Workflow
```bash
# create/edit (opens decrypted in $EDITOR, re-encrypts on save)
sops secrets/staging.enc.env

# one-shot encrypt an existing plaintext file, in place
sops --encrypt --in-place secrets/staging.enc.env

# read it back
sops --decrypt secrets/staging.enc.env
```

The **runtime** system of record is still the Render/Vercel dashboard. These
files are for reproducible, reviewable, encrypted-at-rest copies and for the
Phase 2 IaC secret inputs. Full rotation runbook: [`../docs/SECRETS.md`](../docs/SECRETS.md).
