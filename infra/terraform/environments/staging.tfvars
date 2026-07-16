# Staging (auto-deploys on push to develop — see CD_STRATEGY.md).
environment        = "staging"
git_branch         = "develop"
render_auto_deploy = true
render_region      = "singapore"
render_plan        = "starter"

# Fill in from your accounts (non-secret ids):
render_owner_id          = "REPLACE_render_owner_id"
vercel_team_id           = "REPLACE_vercel_team_id"
vercel_production_branch = "develop"
cloudflare_zone_id       = "REPLACE_cloudflare_zone_id"

base_domain  = "staging.myhostel.com"
api_base_url = "https://hostel-backend-staging.onrender.com/api"

# Secrets (django_secret_key, ml_shared_secret) come from TF_VAR_* env vars.
