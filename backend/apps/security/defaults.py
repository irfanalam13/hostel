"""Baseline security configuration + per-environment defaults.

This is layer 0 of the config resolution chain (see ``conf.py``):

    DEFAULTS  <-  ENVIRONMENT_DEFAULTS[env]  <-  YAML file  <-  env vars
              <-  DB (SecuritySetting rows)

Nothing here is hardcoded policy — every value can be overridden per
deployment (YAML/env) or at runtime without a restart (SecuritySetting).
"""

# Official Cloudflare origin ranges (https://www.cloudflare.com/ips/). Used to
# trust CF-Connecting-IP only when the direct peer is actually Cloudflare.
# Refresh via SECURITY_CLOUDFLARE_IP_RANGES / YAML when Cloudflare updates them.
CLOUDFLARE_IPV4 = [
    "173.245.48.0/20", "103.21.244.0/22", "103.22.200.0/22", "103.31.4.0/22",
    "141.101.64.0/18", "108.162.192.0/18", "190.93.240.0/20", "188.114.96.0/20",
    "197.234.240.0/22", "198.41.128.0/17", "162.158.0.0/15", "104.16.0.0/13",
    "104.24.0.0/14", "172.64.0.0/13", "131.0.72.0/22",
]
CLOUDFLARE_IPV6 = [
    "2400:cb00::/32", "2606:4700::/32", "2803:f800::/32", "2405:b500::/32",
    "2405:8100::/32", "2a06:98c0::/29", "2c0f:f248::/32",
]

# Attack tools / scanners — always hostile, safe to hard-block by default.
BLOCKED_USER_AGENTS = [
    "sqlmap", "nikto", "nessus", "acunetix", "masscan", "zgrab", "nmap",
    "wpscan", "dirbuster", "gobuster", "hydra", "havij", "netsparker",
    "openvas", "w3af", "jorgee", "fuzz", "commix", "arachni",
]
# Generic automation — legitimate in many contexts (health checks, SDKs), so
# the default ACTION for these is log-only; enforcement is per-deployment.
SUSPICIOUS_USER_AGENTS = [
    "curl", "wget", "python-requests", "python-urllib", "aiohttp", "httpx",
    "scrapy", "go-http-client", "java/", "libwww", "okhttp", "phantomjs",
    "headlesschrome", "selenium", "puppeteer", "playwright", "mechanize",
    "node-fetch", "axios",
]
# Well-known good bots / monitors — never challenged or blocked.
ALLOWED_USER_AGENTS = [
    "googlebot", "bingbot", "duckduckbot", "slurp", "baiduspider", "yandexbot",
    "applebot", "facebookexternalhit", "twitterbot", "linkedinbot", "slackbot",
    "whatsapp", "telegrambot", "uptimerobot", "pingdom", "statuscake",
    "site24x7", "betteruptime", "gtmetrix", "lighthouse", "chrome-lighthouse",
]

DEFAULTS = {
    # Master switch + behaviour of every enforcement point:
    #   enforce  — violations are blocked (403/429)
    #   monitor  — violations are fully evaluated and logged, never blocked
    "enabled": True,
    "mode": "enforce",
    # Redis unavailable:  open — allow traffic (availability first)
    #                     closed — reject rate-limited scopes with 503
    "fail_strategy": "open",
    # Limiter backend: auto (Redis, degrade to per-process memory), redis, memory.
    "backend": "auto",

    # Proxies whose X-Forwarded-For we trust (the compose/K8s network + local).
    "trusted_proxies": [
        "127.0.0.0/8", "::1/128",
        "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "fd00::/8",
    ],
    # Never inspected / rate limited (probes, assets, metrics scraper).
    "exempt_paths": ["/health/", "/healthz", "/metrics", "/static/", "/media/"],

    "cloudflare": {
        "enabled": False,
        "connecting_ip_header": "CF-Connecting-IP",
        "ip_ranges": CLOUDFLARE_IPV4 + CLOUDFLARE_IPV6,
    },

    # DB-managed allow/deny/trust CIDRs (IPRule model) — the switch only.
    "ip_rules": {"enabled": True},

    "reputation": {
        "enabled": True,
        # Behaviour score accumulates penalties; decays via TTL.
        "suspicious_threshold": 20,
        "block_threshold": 50,
        "decay_seconds": 3600,
        "block_seconds": 3600,
        "penalties": {
            "rate_limited": 3,
            "waf_violation": 10,
            "bot_blocked": 5,
            "auth_failure": 5,       # consumed by the auth prompt (next doc)
            "enumeration": 4,
            "manual": 50,
        },
    },

    "bots": {
        "enabled": True,
        "mode": "monitor",                 # prod default flips to enforce below
        "blocked_agents": BLOCKED_USER_AGENTS,
        "suspicious_agents": SUSPICIOUS_USER_AGENTS,
        "allowed_agents": ALLOWED_USER_AGENTS,
        # Actions: allow | log | block  (challenge is delegated to Cloudflare)
        "blocked_action": "block",
        "suspicious_action": "log",
        "empty_user_agent_action": "log",
    },

    "waf": {
        "enabled": True,
        "mode": "monitor",                 # prod default flips to enforce below
        "allowed_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
        "max_path_length": 2048,
        "max_query_length": 4096,
        # Which rule groups run (path + query string inspection — bodies are
        # NOT inspected here; that is Cloudflare WAF / app-validation territory).
        "rules": {
            "path_traversal": True,
            "sql_injection": True,
            "xss": True,
            "remote_code_execution": True,
            "file_inclusion": True,
            "scanner_probes": True,
        },
    },

    # Foundation-wide limits. Endpoint-specific limits (login/OTP/...) build on
    # these scopes in the next document. window_seconds applies to
    # sliding_window / leaky_bucket(period); token_bucket uses capacity+refill.
    "rate_limits": {
        "ip_global": {
            "enabled": True, "algorithm": "sliding_window",
            "limit": 300, "window_seconds": 60,
        },
        "ip_burst": {
            "enabled": True, "algorithm": "token_bucket",
            "capacity": 60, "refill_rate": 20,            # tokens per second
        },
        "tenant_global": {
            "enabled": True, "algorithm": "sliding_window",
            "limit": 2000, "window_seconds": 60,
        },

        # ---- Authentication endpoints (Prompt 08) ---------------------- #
        # Keyed by client IP (the throttle classes set the scope). Tight,
        # credential-abuse-facing buckets — each independently configurable.
        "auth_login": {"enabled": True, "algorithm": "sliding_window",
                       "limit": 10, "window_seconds": 300},
        "auth_signup": {"enabled": True, "algorithm": "sliding_window",
                        "limit": 5, "window_seconds": 3600},
        "auth_signup_otp": {"enabled": True, "algorithm": "sliding_window",
                            "limit": 6, "window_seconds": 3600},
        "auth_otp_verify": {"enabled": True, "algorithm": "sliding_window",
                            "limit": 10, "window_seconds": 600},
        "auth_password_reset": {"enabled": True, "algorithm": "sliding_window",
                                "limit": 5, "window_seconds": 3600},
        "auth_password_change": {"enabled": True, "algorithm": "sliding_window",
                                 "limit": 10, "window_seconds": 3600},
        "auth_token_refresh": {"enabled": True, "algorithm": "token_bucket",
                               "capacity": 60, "refill_rate": 1},
        "auth_mfa_verify": {"enabled": True, "algorithm": "sliding_window",
                            "limit": 10, "window_seconds": 600},
        "auth_forgot_hostel": {"enabled": True, "algorithm": "sliding_window",
                               "limit": 5, "window_seconds": 3600},
        "auth_session_revoke": {"enabled": True, "algorithm": "sliding_window",
                                "limit": 30, "window_seconds": 300},

        # ---- Expensive / abuse-prone resource endpoints (tenant-scoped) - #
        # Consumed by the TenantScoped throttle classes; scaled by plan.
        "exports": {"enabled": True, "algorithm": "sliding_window",
                    "limit": 20, "window_seconds": 3600},
        "reports": {"enabled": True, "algorithm": "sliding_window",
                    "limit": 60, "window_seconds": 3600},
        "analytics": {"enabled": True, "algorithm": "sliding_window",
                      "limit": 120, "window_seconds": 60},
        "search": {"enabled": True, "algorithm": "token_bucket",
                   "capacity": 30, "refill_rate": 2},
        "notifications_send": {"enabled": True, "algorithm": "sliding_window",
                               "limit": 60, "window_seconds": 3600},
        "ai": {"enabled": True, "algorithm": "leaky_bucket",
               "limit": 60, "window_seconds": 60, "burst": 5},
        "payment": {"enabled": True, "algorithm": "sliding_window",
                    "limit": 120, "window_seconds": 60},
        "file_upload": {"enabled": True, "algorithm": "token_bucket",
                        "capacity": 20, "refill_rate": 1},
    },

    # Per-plan multipliers applied to tenant-scoped limits (matched against the
    # workspace's plan slug, lowercased; "default" covers unknown plans).
    "plan_multipliers": {
        "free": 1.0, "starter": 1.5, "basic": 1.5, "professional": 2.5,
        "business": 4.0, "enterprise": 8.0, "custom": 8.0, "default": 1.0,
    },

    # -------------------------------------------------------------------- #
    # Authentication protection (Prompt 08). Complements django-axes (which
    # stays the primary per-(ip,username) login lockout): this layer adds
    # progressive multi-tier lockout, CAPTCHA escalation, credential-stuffing
    # / enumeration detection and enumeration-safe auth events on top.
    # -------------------------------------------------------------------- #
    "auth": {
        "enabled": True,
        # Progressive lockout: never a fixed block. Cumulative failures within
        # failure_window_seconds map to escalating block durations. Tracked per
        # IP and per identity (username+tenant); the longer of the two applies.
        "progressive_lockout": {
            "enabled": True,
            "scope": "both",                 # ip | identity | both
            "failure_window_seconds": 3600,
            # [cumulative_failures, block_seconds]
            "tiers": [[5, 30], [10, 120], [15, 600], [20, 3600], [30, 86400]],
        },
        # CAPTCHA escalation. Off until a provider secret is configured
        # (SECURITY_CAPTCHA_SECRET); then required after N failures or when the
        # source IP is suspicious/blocked. Never required otherwise.
        "captcha": {
            "enabled": False,
            "provider": "turnstile",         # turnstile | recaptcha | hcaptcha
            "trigger_after_failures": 3,
            "trigger_on_reputation": "suspicious",   # ok | suspicious | blocked
            "fail_open": True,               # verification error -> allow (avail.)
        },
        # Credential stuffing: many DISTINCT identities tried from one IP.
        "credential_stuffing": {
            "enabled": True,
            "distinct_identities_threshold": 6,
            "window_seconds": 300,
            "reputation_penalty": 15,
        },
        # Enumeration: many DISTINCT lookup targets (emails/usernames) probed
        # from one IP against reset/forgot/signup-otp endpoints.
        "enumeration": {
            "enabled": True,
            "distinct_targets_threshold": 15,
            "window_seconds": 300,
        },
    },

    # Per-role / per-plan global API budget (RoleRateThrottle). Applied to
    # every authenticated request; anonymous traffic uses the IP limits above.
    # Writes cost more than reads via method_costs. Scaled by the plan
    # multiplier so higher plans get proportionally higher ceilings.
    "role_limits": {
        "enabled": True,
        "window_seconds": 60,
        "algorithm": "sliding_window",
        "anon": 60,
        "roles": {
            "STUDENT": 120, "PARENT": 120, "RESIDENT": 120, "READ_ONLY": 120,
            "STAFF": 240, "RECEPTIONIST": 300, "WARDEN": 300, "ACCOUNTANT": 300,
            "MANAGER": 600, "ADMIN": 1200, "OWNER": 1200, "SUPER_ADMIN": 6000,
            "default": 240,
        },
        # A single write consumes this many tokens (reads = 1).
        "method_costs": {"GET": 1, "HEAD": 1, "OPTIONS": 0,
                         "POST": 2, "PUT": 2, "PATCH": 2, "DELETE": 2},
    },

    "response": {
        "include_headers": True,           # X-RateLimit-* + Retry-After
        "retry_after_min": 1,
    },

    "events": {
        "log": True,                        # structured JSON security log
        "persist": True,                    # SecurityEvent rows (immutable)
        "persist_async": True,              # via Celery, sync fallback
        "retention_days": 90,
    },
}

# Environment overlays — merged on top of DEFAULTS by conf.py.
ENVIRONMENT_DEFAULTS = {
    "development": {
        "mode": "monitor",
        "fail_strategy": "open",
        "rate_limits": {
            "ip_global": {"limit": 2000},
            "ip_burst": {"capacity": 400, "refill_rate": 200},
            "tenant_global": {"limit": 10000},
            # Relaxed auth buckets so local iteration isn't blocked.
            "auth_login": {"limit": 100, "window_seconds": 300},
            "auth_signup": {"limit": 50, "window_seconds": 3600},
            "auth_otp_verify": {"limit": 100, "window_seconds": 600},
        },
        "role_limits": {"enabled": False},
        "auth": {
            # Progressive lockout still tracked (so tests/QA can exercise it)
            # but global monitor mode means nothing is actually blocked.
            "captcha": {"enabled": False},
        },
    },
    "testing": {
        "enabled": False,
    },
    "staging": {
        "mode": "enforce",
        "waf": {"mode": "monitor"},        # soak WAF rules before enforcing
        "bots": {"mode": "monitor"},
    },
    "production": {
        "mode": "enforce",
        "waf": {"mode": "enforce"},
        "bots": {"mode": "enforce"},
    },
}
