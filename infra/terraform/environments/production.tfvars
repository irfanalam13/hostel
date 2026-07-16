# Production (MANUAL promotion gate — render_auto_deploy = false; promote via
# Render "Manual Deploy" + Vercel "Promote to Production"). See CD_STRATEGY.md.
environment        = "production"
git_branch         = "main"
render_auto_deploy = false
render_region      = "singapore"
render_plan        = "standard"

render_owner_id          = "REPLACE_render_owner_id"
vercel_team_id           = "REPLACE_vercel_team_id"
vercel_production_branch = "main"
cloudflare_zone_id       = "REPLACE_cloudflare_zone_id"

base_domain  = "myhostel.com"
api_base_url = "https://hostel-backend-production.onrender.com/api"

# Secrets (django_secret_key, ml_shared_secret) come from TF_VAR_* env vars.
