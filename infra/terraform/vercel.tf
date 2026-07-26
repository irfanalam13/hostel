# =============================================================================
# Vercel — client (marketing) + admin Next.js zones
# =============================================================================
# ⚠️  RECONCILE + IMPORT: the two Vercel projects already exist. Import them
#     (README) before the first apply. `git_repository` binds the project to the
#     GitHub repo; per CD_STRATEGY.md production is reached via manual
#     "Promote to Production", so we do NOT set main as an auto-deploy trigger
#     beyond Vercel's default preview builds.

locals {
  # NEXT_PUBLIC_* values are build-time and safe to expose in the bundle.
  frontend_public_env = {
    NEXT_PUBLIC_API_BASE_URL       = var.api_base_url
    NEXT_PUBLIC_TENANT_BASE_DOMAIN = var.base_domain
  }
}

resource "vercel_project" "client" {
  name           = "hostel-client-${var.environment}"
  framework      = "nextjs"
  root_directory = "frontend/apps/client"

  git_repository = {
    type              = "github"
    repo              = "irfanalam13/hostel"
    production_branch = var.vercel_production_branch
  }
}

resource "vercel_project" "admin" {
  name           = "hostel-admin-${var.environment}"
  framework      = "nextjs"
  root_directory = "frontend/apps/admin"

  git_repository = {
    type              = "github"
    repo              = "irfanalam13/hostel"
    production_branch = var.vercel_production_branch
  }
}

# Public build-time env vars for both projects × both target sets.
resource "vercel_project_environment_variable" "client_public" {
  for_each   = local.frontend_public_env
  project_id = vercel_project.client.id
  key        = each.key
  value      = each.value
  target     = ["production", "preview"]
}

resource "vercel_project_environment_variable" "admin_public" {
  for_each   = local.frontend_public_env
  project_id = vercel_project.admin.id
  key        = each.key
  value      = each.value
  target     = ["production", "preview"]
}

# Custom domains (production only). Staging uses the default *.vercel.app URLs.
resource "vercel_project_domain" "client_apex" {
  count      = var.environment == "production" ? 1 : 0
  project_id = vercel_project.client.id
  domain     = var.base_domain
}

resource "vercel_project_domain" "admin_sub" {
  count      = var.environment == "production" ? 1 : 0
  project_id = vercel_project.admin.id
  domain     = "app.${var.base_domain}"
}
