# =============================================================================
# Cloudflare — DNS + edge WAF/rate-limit for the workspace base domain
# =============================================================================
# ⚠️  Provider v5 renamed `cloudflare_record` → `cloudflare_dns_record` and
#     changed ruleset shapes vs v4. This targets ~> 5.0. Import existing DNS
#     records before apply. Production only — staging rides *.vercel.app.

# Apex → Vercel (client/marketing zone).
resource "cloudflare_dns_record" "apex" {
  count   = var.environment == "production" ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = var.base_domain
  type    = "CNAME"
  content = "cname.vercel-dns.com"
  ttl     = 1 # 1 = automatic (required when proxied)
  proxied = true
}

# app.<domain> → Vercel (admin zone).
resource "cloudflare_dns_record" "app" {
  count   = var.environment == "production" ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = "app"
  type    = "CNAME"
  content = "cname.vercel-dns.com"
  ttl     = 1
  proxied = true
}

# Wildcard tenant subdomains (<slug>.<domain>) → client zone (workspace routing
# happens in-app via the X-Workspace header — see the frontend edge proxy).
resource "cloudflare_dns_record" "wildcard" {
  count   = var.environment == "production" ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = "*"
  type    = "CNAME"
  content = "cname.vercel-dns.com"
  ttl     = 1
  proxied = true
}

# --- TLS / transport hardening (§5) -----------------------------------------
# v5 exposes each zone setting as its own resource. Reconcile setting IDs with
# the pinned provider before apply.
resource "cloudflare_zone_setting" "min_tls" {
  count      = var.environment == "production" ? 1 : 0
  zone_id    = var.cloudflare_zone_id
  setting_id = "min_tls_version"
  value      = "1.3"
}

resource "cloudflare_zone_setting" "always_https" {
  count      = var.environment == "production" ? 1 : 0
  zone_id    = var.cloudflare_zone_id
  setting_id = "always_use_https"
  value      = "on"
}

resource "cloudflare_zone_setting" "tls_strict" {
  count      = var.environment == "production" ? 1 : 0
  zone_id    = var.cloudflare_zone_id
  setting_id = "ssl"
  value      = "strict" # full end-to-end verification to the origin
}

# HSTS at the edge (2y, includeSubDomains, preload) — mirrors the nginx snippet
# so the canonical Cloudflare path enforces the same transport policy.
resource "cloudflare_zone_setting" "hsts" {
  count      = var.environment == "production" ? 1 : 0
  zone_id    = var.cloudflare_zone_id
  setting_id = "security_header"
  value = jsonencode({
    strict_transport_security = {
      enabled            = true
      max_age            = 63072000
      include_subdomains = true
      preload            = true
      nosniff            = true
    }
  })
}

# --- Managed WAF (§5) --------------------------------------------------------
# Deploy Cloudflare's Managed Ruleset + OWASP Core Ruleset at the firewall-
# managed phase. These sit in front of the app-layer WAF (apps.security).
resource "cloudflare_ruleset" "waf_managed" {
  count   = var.environment == "production" ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = "hostel-waf-managed"
  kind    = "zone"
  phase   = "http_request_firewall_managed"

  rules = [
    {
      action      = "execute"
      description = "Cloudflare Managed Ruleset"
      expression  = "true"
      action_parameters = {
        id = "efb7b8c949ac4650a09736fc376e9aee" # Cloudflare Managed Ruleset
      }
    },
    {
      action      = "execute"
      description = "OWASP Core Ruleset"
      expression  = "true"
      action_parameters = {
        id = "4814384a9e5d4991b9815dcfc25d2f1f" # Cloudflare OWASP Core Ruleset
      }
    },
  ]
}

# Edge rate-limit for the auth endpoints — a coarse first line in front of the
# app-layer throttles (apps.security). Tune to match those limits.
resource "cloudflare_ruleset" "rate_limit" {
  count   = var.environment == "production" ? 1 : 0
  zone_id = var.cloudflare_zone_id
  name    = "hostel-auth-ratelimit"
  kind    = "zone"
  phase   = "http_ratelimit"

  rules = [{
    action      = "block"
    description = "Throttle auth endpoints at the edge"
    expression  = "(http.request.uri.path contains \"/api/auth/\")"
    ratelimit = {
      characteristics     = ["ip.src", "cf.colo.id"]
      period              = 60
      requests_per_period = 60
      mitigation_timeout  = 60
    }
  }]
}
