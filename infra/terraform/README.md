# Infrastructure as Code (Terraform) — Phase 2, §7

Terraform is the **system of record** for the managed-PaaS infrastructure:
Render (backend, Celery worker, ML service, Postgres, Redis), Vercel (client +
admin Next.js zones), and Cloudflare (DNS + edge WAF/rate-limit). It codifies
the topology described in `docs/CD_STRATEGY.md`.

> **Status: scaffold — validate before first apply.** These files are
> structurally complete and idiomatic, but they were authored without a live
> `terraform` binary or provider credentials. Before the first apply you MUST:
> 1. `terraform init` (downloads the pinned providers) then `terraform validate`.
> 2. Reconcile resource attributes against the **exact provider schema** you pin
>    (`terraform providers schema -json`) — the Render/Cloudflare providers in
>    particular evolve their attribute shapes between minor versions.
> 3. **Import** the already-running resources (below) so the first `apply` is a
>    no-op, never a recreate. **Never let Terraform recreate the Postgres DB.**

## Layout

```
infra/terraform/
  versions.tf     terraform + provider pins + S3 remote-state backend
  providers.tf    provider auth (all via env vars — no secrets in code)
  variables.tf    typed inputs (secrets are sensitive, passed via TF_VAR_*)
  render.tf       Render services + Postgres + Redis
  vercel.tf       Vercel projects, env vars, custom domains
  cloudflare.tf   DNS records (apex/app/wildcard) + auth rate-limit ruleset
  outputs.tf      service URLs + project ids
  environments/
    staging.tfvars / production.tfvars       non-secret per-env inputs
    backend-staging.hcl / backend-production.hcl   S3 state config
```

## Credentials (never committed)

Export before running (in CI these are GitHub Actions secrets; locally, source a
SOPS-decrypted env — see `docs/SECRETS.md`):

```bash
export RENDER_API_KEY=...
export VERCEL_API_TOKEN=...
export CLOUDFLARE_API_TOKEN=...
export TF_VAR_django_secret_key=...      # only needed for apply
export TF_VAR_ml_shared_secret=...       # must match on backend + ML
```

## Usage (per environment)

```bash
cd infra/terraform

# staging
terraform init -backend-config=environments/backend-staging.hcl
terraform workspace select staging || terraform workspace new staging
terraform plan  -var-file=environments/staging.tfvars
terraform apply -var-file=environments/staging.tfvars

# production (manual promotion gate — see CD_STRATEGY.md)
terraform init -reconfigure -backend-config=environments/backend-production.hcl
terraform workspace select production || terraform workspace new production
terraform plan  -var-file=environments/production.tfvars
terraform apply -var-file=environments/production.tfvars
```

## Adopting existing resources (import, one-time)

The services already exist in the dashboards. Import each before applying, e.g.:

```bash
terraform import -var-file=environments/production.tfvars \
  render_web_service.backend <render-service-id>
terraform import -var-file=environments/production.tfvars \
  vercel_project.client <vercel-project-id>
terraform import -var-file=environments/production.tfvars \
  'cloudflare_dns_record.apex[0]' <zone-id>/<record-id>
```

Then `terraform plan` should report **no changes**. Resolve any diff by editing
the `.tf` to match reality (not by applying) until the plan is clean.

## CI

`.github/workflows/infra.yml` runs `fmt -check` + `validate` + `plan` on PRs that
touch `infra/**`, and gates `apply` behind the `production` GitHub Environment
(manual approval) — the same Continuous Delivery gate the app deploys use.
