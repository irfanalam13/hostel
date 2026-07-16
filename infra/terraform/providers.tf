# Provider configuration. All credentials come from environment variables so no
# secret is ever written to state config or committed:
#   RENDER_API_KEY            (render)
#   VERCEL_API_TOKEN          (vercel — or TF_VAR_vercel_api_token)
#   CLOUDFLARE_API_TOKEN      (cloudflare)
# In CI these are GitHub Actions secrets; locally, export them (or source a
# SOPS-decrypted env — see docs/SECRETS.md).

provider "render" {
  # RENDER_API_KEY is read from the environment.
  owner_id = var.render_owner_id
}

provider "vercel" {
  # VERCEL_API_TOKEN is read from the environment.
  team = var.vercel_team_id
}

provider "cloudflare" {
  # CLOUDFLARE_API_TOKEN is read from the environment.
}
