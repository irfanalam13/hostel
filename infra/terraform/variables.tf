# Input variables. Non-secret values are set per environment in
# environments/<env>.tfvars; secrets are passed as TF_VAR_* env vars (CI secrets
# / SOPS), never committed.

variable "environment" {
  description = "Deployment environment name (staging | production)."
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "environment must be 'staging' or 'production'."
  }
}

# --- Source repo ------------------------------------------------------------
variable "repo_url" {
  description = "GitHub repository URL the PaaS builds from."
  type        = string
  default     = "https://github.com/irfanalam13/hostel"
}

variable "git_branch" {
  description = "Branch each service tracks (e.g. develop for staging, main for production)."
  type        = string
}

# --- Render -----------------------------------------------------------------
variable "render_owner_id" {
  description = "Render owner/team id that owns the services."
  type        = string
}

variable "render_region" {
  description = "Render region (e.g. singapore, oregon, frankfurt)."
  type        = string
  default     = "singapore"
}

variable "render_plan" {
  description = "Render instance plan for web services (starter keeps them warm)."
  type        = string
  default     = "starter"
}

variable "render_auto_deploy" {
  description = <<-EOT
    Whether Render auto-deploys on push. Per CD_STRATEGY.md this is TRUE for
    staging and FALSE for production (manual promotion gate).
  EOT
  type        = bool
}

# --- Vercel -----------------------------------------------------------------
variable "vercel_team_id" {
  description = "Vercel team/scope id."
  type        = string
}

variable "vercel_production_branch" {
  description = "Branch Vercel treats as production for the projects."
  type        = string
  default     = "main"
}

# --- Domains / Cloudflare ---------------------------------------------------
variable "cloudflare_zone_id" {
  description = "Cloudflare zone id for the workspace base domain."
  type        = string
}

variable "base_domain" {
  description = "Workspace base domain (e.g. myhostel.com); wildcard tenant subdomains hang off it."
  type        = string
}

variable "api_base_url" {
  description = "Public API base URL baked into the frontend bundles."
  type        = string
}

# --- Secrets (passed via TF_VAR_*, never committed) -------------------------
variable "ml_shared_secret" {
  description = "HS256 secret shared by backend + ML service. Set via TF_VAR_ml_shared_secret."
  type        = string
  sensitive   = true
  default     = "" # supplied at apply time; empty default lets `plan` run in CI without it
}

variable "django_secret_key" {
  description = "Django SECRET_KEY. Set via TF_VAR_django_secret_key."
  type        = string
  sensitive   = true
  default     = ""
}
