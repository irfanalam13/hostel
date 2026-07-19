import ssl
from pathlib import Path
from datetime import timedelta

import environ
from celery.schedules import crontab
from corsheaders.defaults import default_headers

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
env = environ.Env(
    DEBUG=(bool, False),
)
# Load backend/.env if present (never commit real secrets — see .env.example)
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env("DEBUG")

# SECRET_KEY: required in production, dev gets an insecure default so the app
# still boots locally. The app refuses to start with the placeholder when DEBUG=False.
# Accepts DJANGO_SECRET_KEY (preferred / documented in .env.example) and falls
# back to the legacy SECRET_KEY name for backward compatibility.
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default=env(
        "SECRET_KEY",
        default="django-insecure-dev-only-key-change-me" if DEBUG else "",
    ),
)
if not DEBUG and (not SECRET_KEY or SECRET_KEY.startswith("django-insecure")):
    raise RuntimeError(
        "SECRET_KEY must be set to a strong, unique value when DEBUG=False. "
        "Generate one with: python -c \"from django.core.management.utils import "
        "get_random_secret_key; print(get_random_secret_key())\""
    )

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=["hostel-mwre.onrender.com","localhost","127.0.0.1"] if DEBUG else [],
)
# Fail fast instead of silently 400-ing every request in production.
if not DEBUG and not ALLOWED_HOSTS:
    raise RuntimeError(
        "ALLOWED_HOSTS must be set (comma-separated) when DEBUG=False. "
        "Example: ALLOWED_HOSTS=api.example.com,example.com"
    )

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "drf_spectacular_sidecar",  # self-hosts Swagger UI / ReDoc assets (no CDN)
    "corsheaders",
    "axes",

    "apps.common",
    "apps.tenants",
    "apps.accounts",
    "apps.hostel",
    "apps.residents",
    "apps.billing",
    "apps.attendance",
    "apps.rooms",
    "apps.admissions",
    "apps.students",
    "apps.fees",
    "apps.payments",
    "apps.operations",
    "apps.complaints",
    "apps.notices",
    "apps.dashboard",
    "apps.reports",
    "apps.auditlog",
    "apps.exports",
    "apps.backups",
    "apps.notifications",
    "apps.idempotency",
    "apps.analytics",
    "apps.marketing",
    "apps.website",
    "apps.domains",
    "apps.subscriptions",
    "apps.staff",
    "apps.finance",
    "apps.accounting",
    "apps.inventory",
    "apps.security",
    "apps.platformops",
    "apps.assistant",
    "apps.aiknowledge",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    # Request id + Server-Timing + structured per-request log (duration, DB
    # time, query count). Sits at the top so it times the whole stack.
    "apps.common.observability.RequestTimingMiddleware",
    # Edge security (Prompt 07): spoof-resistant client IP, IP allow/deny
    # rules, IP reputation, bot detection, WAF-lite and distributed per-IP
    # rate limits. Runs before anything expensive so abusive traffic is
    # rejected with near-zero cost. Config-driven + hot-reloadable.
    "apps.security.middleware.EdgeGuardMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Compress JSON/API responses (>200 bytes, Accept-Encoding permitting) —
    # large list payloads shrink ~5-10x on the wire.
    "django.middleware.gzip.GZipMiddleware",
    # Serve collected static files directly from Gunicorn (no nginx required).
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "apps.common.middleware.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # Disaster-recovery gate: enforces maintenance / emergency (read-only / lock)
    "apps.backups.middleware.DRModeMiddleware",

    # Tenant resolution — resolves the workspace (subdomain / headers) before
    # authentication and rejects unknown/suspended/archived workspaces.
    "apps.tenants.middleware.TenantResolutionMiddleware",
    # Per-workspace, plan-aware rate limit (needs request.tenant) — one tenant
    # can never exhaust the platform for the others.
    "apps.security.middleware.TenantRateLimitMiddleware",
    # Audit trail
    "apps.auditlog.middleware.AuditLogMiddleware",

    # Offline-sync idempotency + payload integrity (needs request.user/.hostel,
    # so it runs after tenant resolution and before brute-force protection).
    "apps.idempotency.middleware.IdempotencyMiddleware",

    # Brute-force protection (must be last so request is fully built)
    "axes.middleware.AxesMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [],
    "APP_DIRS": True,
    "OPTIONS": {
        "context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
        ],
    },
}]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database — PostgreSQL only (local development + production)
# ---------------------------------------------------------------------------
# This project runs on PostgreSQL in every environment; there is no SQLite
# fallback. Configure via DATABASE_URL, e.g.:
#   postgres://USER:PASS@HOST:5432/DBNAME?sslmode=require
# Query params (sslmode, channel_binding, …) pass through to the driver as
# OPTIONS, so managed providers (Neon/Supabase/Render) work without extra config.
# In dev a local Postgres URL is assumed; production MUST set DATABASE_URL.
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://hostel:hostel@localhost:5432/hostel" if DEBUG else "",
    )
}

# Fail fast on a missing/non-Postgres database instead of 500-ing at runtime.
if DATABASES["default"].get("ENGINE") != "django.db.backends.postgresql":
    raise RuntimeError(
        "A PostgreSQL DATABASE_URL is required (postgres://USER:PASS@HOST:5432/DBNAME). "
        "This project does not support SQLite."
    )

# Production hardening for Postgres: reuse connections across requests
# (essential with pooled providers like Neon) and verify each pooled connection
# is alive before use.
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=600)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
# Optional per-connection statement timeout (ms) — a runaway query dies instead
# of holding a worker. 0/unset = provider default. (Pooling beyond CONN_MAX_AGE
# belongs in pgbouncer/managed poolers — see docs/PRODUCTION.md.)
_db_stmt_timeout = env.int("DB_STATEMENT_TIMEOUT_MS", default=0)
if _db_stmt_timeout:
    DATABASES["default"].setdefault("OPTIONS", {})["options"] = (
        f"-c statement_timeout={_db_stmt_timeout}"
    )

AUTH_USER_MODEL = "accounts.User"

# ---------------------------------------------------------------------------
# Authentication backends — django-axes wraps the default backend
# ---------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        # Reads the access token from an httpOnly cookie (falls back to Bearer header)
        "apps.accounts.authentication.CookieJWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # Consistent response envelope: {success, message, data, meta}.
    # (BrowsableAPIRenderer kept so the DRF web UI still works in dev.)
    "DEFAULT_RENDERER_CLASSES": (
        "apps.common.renderers.StandardJSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ),
    # Bound list responses -> {count, next, previous, results}
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": env.int("API_PAGE_SIZE", default=25),
    # Rate limiting / abuse protection.
    # RoleRateThrottle (Prompt 08) adds the per-role / per-plan / per-method
    # global API budget on top of DRF's built-ins — atomic on Redis,
    # tenant-aware, monitor-mode-aware. It's config-gated (role_limits.enabled,
    # off in dev) so it's a no-op until switched on. The built-in Anon/User
    # throttles stay for backward compatibility; ScopedRateThrottle still
    # serves any view using the legacy `throttle_scope`. We use cache-resilient
    # subclasses: DRF's built-ins keep their history in the Django cache and a
    # Redis outage would otherwise 500 every anonymous endpoint that reaches
    # the throttle stage (e.g. /api/auth/csrf/) — these fail open instead.
    "DEFAULT_THROTTLE_CLASSES": (
        "apps.security.throttles.RoleRateThrottle",
        "apps.security.throttles.ResilientAnonRateThrottle",
        "apps.security.throttles.ResilientUserRateThrottle",
        "apps.security.throttles.ResilientScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="60/min"),
        "user": env("THROTTLE_USER", default="1000/hour"),
        "auth": env("THROTTLE_AUTH", default="5/min"),
        # Tighter, dedicated buckets for sensitive endpoints (ScopedRateThrottle).
        "signup": env("THROTTLE_SIGNUP", default="3/hour"),
        # Email-verification code requests during signup (resends allowed).
        "signup_otp": env("THROTTLE_SIGNUP_OTP", default="6/hour"),
        "password_reset": env("THROTTLE_PASSWORD_RESET", default="5/hour"),
        "payment": env("THROTTLE_PAYMENT", default="120/min"),
        "backup": env("THROTTLE_BACKUP", default="10/hour"),
        "admissions": env("THROTTLE_ADMISSIONS", default="20/hour"),
        # Public review submissions from the landing page.
        "review": env("THROTTLE_REVIEW", default="5/hour"),
        # Public sales/demo lead submissions from the landing page.
        "lead": env("THROTTLE_LEAD", default="10/hour"),
        # Public website inquiry form (per-IP).
        "website_inquiry": env("THROTTLE_WEBSITE_INQUIRY", default="5/hour"),
        # Custom-domain verification / SSL checks (live DNS+TLS probes).
        "domain_verify": env("THROTTLE_DOMAIN_VERIFY", default="20/hour"),
        # Real-time workspace-username availability checks (public, per-IP).
        "workspace_check": env("THROTTLE_WORKSPACE_CHECK", default="30/min"),
        # Workspace registration by an authenticated user.
        "workspace": env("THROTTLE_WORKSPACE", default="5/hour"),
    },
}

# ---------------------------------------------------------------------------
# SimpleJWT + cookie transport
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("ACCESS_TOKEN_MINUTES", default=15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("REFRESH_TOKEN_DAYS", default=3)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# "Remember me" logins get a longer refresh-token lifetime (days); the access
# token stays short-lived regardless.
REMEMBER_ME_REFRESH_DAYS = env.int("REMEMBER_ME_REFRESH_DAYS", default=30)

# RBAC: per-(workspace, role) permission-set cache TTL (seconds). Also
# invalidated whenever the workspace's settings change (apps.tenants signal).
PERMISSIONS_CACHE_TTL = env.int("PERMISSIONS_CACHE_TTL", default=300)

# Subscription entitlement (feature/limit) snapshot cache TTL (seconds).
# Invalidated immediately on any plan/catalog/override change via a global
# generation counter (apps.subscriptions.entitlements); this only bounds
# staleness if a signal is ever missed.
ENTITLEMENTS_CACHE_TTL = env.int("ENTITLEMENTS_CACHE_TTL", default=300)

# Master switch for plan-based entitlement enforcement. While the platform is
# still under construction we ship with plans unset, so gating every module
# behind a plan would lock the whole product. With this off, every feature is
# treated as available and every limit as unlimited. Flip to True (or set
# ENTITLEMENTS_ENFORCED=1) once plans are configured per workspace.
ENTITLEMENTS_ENFORCED = env.bool("ENTITLEMENTS_ENFORCED", default=False)

# httpOnly cookie auth configuration (consumed by apps.accounts)
JWT_AUTH_COOKIE = "access_token"
JWT_AUTH_REFRESH_COOKIE = "refresh_token"
JWT_COOKIE_SECURE = env.bool("JWT_COOKIE_SECURE", default=not DEBUG)
JWT_COOKIE_SAMESITE = env("JWT_COOKIE_SAMESITE", default="Lax")
JWT_COOKIE_DOMAIN = env("JWT_COOKIE_DOMAIN", default=None)

# ---------------------------------------------------------------------------
# django-axes (login brute-force lockout)
# ---------------------------------------------------------------------------
AXES_ENABLED = env.bool("AXES_ENABLED", default=True)
AXES_FAILURE_LIMIT = env.int("AXES_FAILURE_LIMIT", default=5)
AXES_COOLOFF_TIME = timedelta(minutes=env.int("AXES_COOLOFF_MINUTES", default=15))
AXES_LOCKOUT_PARAMETERS = ["ip_address", "username"]
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_CALLABLE = "apps.accounts.lockout.lockout_response"

# ---------------------------------------------------------------------------
# CORS / CSRF
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["https://hostel-mwre.onrender.com"] if DEBUG else [],
)
CORS_ALLOW_HEADERS = list(default_headers) + [
    "x-hostel-code",
    "x-hostel-id",
    "x-workspace",
    # Frontend-generated trace id, echoed back by RequestTimingMiddleware.
    "x-request-id",
]
# Let the SPA read the trace id + timing breakdown off responses.
CORS_EXPOSE_HEADERS = ["X-Request-ID", "Server-Timing"]
CORS_ALLOW_CREDENTIALS = True
# In production, require an explicit allow-list and never permit a wildcard
# (a wildcard is incompatible with credentialed requests anyway).
if not DEBUG:
    if not CORS_ALLOWED_ORIGINS:
        raise RuntimeError(
            "CORS_ALLOWED_ORIGINS must be set (comma-separated) when DEBUG=False."
        )
    if "*" in CORS_ALLOWED_ORIGINS:
        raise RuntimeError("CORS_ALLOWED_ORIGINS cannot contain '*' in production.")

CSRF_TRUSTED_ORIGINS = env.list(
    "CSRF_TRUSTED_ORIGINS",
    default=["http://localhost:3000", "https://hostel-mwre.onrender.com",]
)
# The CSRF cookie must be readable by JS so the SPA can echo it back in X-CSRFToken.
CSRF_COOKIE_HTTPONLY = False

# Security headers that should be on in every environment (not just prod).
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True

# ---------------------------------------------------------------------------
# Production security hardening (only active when DEBUG=False)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# Email — Brevo transactional HTTP API only (no SMTP).
#
# PaaS egress firewalls (Render's free/starter tiers included) filter outbound
# SMTP on every port — 25/465/587 and even 2525 aren't reliable — so a send just
# hangs until timeout. Brevo's HTTP API goes over plain HTTPS/443, which is never
# blocked. In prod we send exclusively through it; dev uses the console backend
# so no key is needed locally.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "apps.common.email_backends.BrevoAPIEmailBackend",
)
# Brevo → SMTP & API → API Keys. The only credential email needs now.
BREVO_API_KEY = env("BREVO_API_KEY", default="")
BREVO_API_URL = env("BREVO_API_URL", default="https://api.brevo.com/v3/smtp/email")
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
# Must be a verified sender in Brevo (Senders, Domains & Dedicated IPs).
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@hostel.local")
FRONTEND_URL = env("FRONTEND_URL", default="https://hostel-ten-hazel.vercel.app/")

SPECTACULAR_SETTINGS = {
    "TITLE": "Hostel SaaS API",
    "VERSION": "1.0.0",
    # Serve Swagger UI / ReDoc assets from our own /static/ (via the sidecar)
    # instead of a third-party CDN, so the strict CSP can stay self-origin and
    # the docs work offline / in locked-down deployments.
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
}

# ---------------------------------------------------------------------------
# Files / i18n / misc
# ---------------------------------------------------------------------------
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# WhiteNoise: compress + hash static assets so Gunicorn can serve them in prod.
#
# Media (uploads: website assets, logos, exports, documents) is env-switchable:
#   STORAGE_BACKEND=local  -> filesystem volume (default; dev + single host)
#   STORAGE_BACKEND=s3     -> any S3-compatible object store (AWS S3, MinIO,
#                             Cloudflare R2) via django-storages -- required for
#                             multi-replica/stateless deployments and CDN offload.
STORAGE_BACKEND = env("STORAGE_BACKEND", default="local").strip().lower()
if STORAGE_BACKEND == "s3":
    STORAGES = {
        "default": {"BACKEND": "storages.backends.s3.S3Storage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
    AWS_ACCESS_KEY_ID = env("S3_ACCESS_KEY_ID", default="")
    AWS_SECRET_ACCESS_KEY = env("S3_SECRET_ACCESS_KEY", default="")
    AWS_STORAGE_BUCKET_NAME = env("S3_BUCKET", default="hostel-media")
    # Endpoint empty = AWS S3; set for MinIO (http://minio:9000) or R2.
    AWS_S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", default="") or None
    AWS_S3_REGION_NAME = env("S3_REGION", default="auto")
    # Public CDN/custom domain for media URLs (e.g. media.myhostel.com).
    AWS_S3_CUSTOM_DOMAIN = env("S3_PUBLIC_DOMAIN", default="") or None
    AWS_DEFAULT_ACL = None                 # bucket policy governs access
    AWS_QUERYSTRING_AUTH = env.bool("S3_QUERYSTRING_AUTH", default=False)
    AWS_S3_FILE_OVERWRITE = False          # never silently replace tenant assets
else:
    STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
TIME_ZONE = "Asia/Kathmandu"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Upload validation limits (consumed by apps.common.validators)
MAX_UPLOAD_SIZE_MB = env.int("MAX_UPLOAD_SIZE_MB", default=10)
# Max size of an uploaded backup-restore JSON payload.
MAX_BACKUP_RESTORE_MB = env.int("MAX_BACKUP_RESTORE_MB", default=50)

# Backup encryption key (Fernet). Generate with:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
BACKUP_ENCRYPTION_KEY = env("BACKUP_ENCRYPTION_KEY", default="")

# Redis / Celery (backup scheduling, cache, health checks)
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)

# Run tasks inline in the web process when no Celery worker is deployed. On a
# single-service deploy (e.g. Render without a background worker) transactional
# emails (signup / password-reset OTPs) and audit/security event writes then
# complete in-request instead of piling up in a broker nothing drains. Defaults
# to eager whenever DEBUG is off; dev keeps its real worker + beat (DEBUG=True).
# Set CELERY_TASK_ALWAYS_EAGER=False on a worker-backed deployment to offload
# tasks again — the Celery code and every .delay() call site stay unchanged.
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=not DEBUG)
# A background task that fails is captured on its result rather than raised, so
# it can never 500 an unrelated request. The OTP views still surface delivery
# failures: their tasks call self.retry(), which raises even in eager mode, and
# the view maps it to a 502.
CELERY_TASK_EAGER_PROPAGATES = env.bool("CELERY_TASK_EAGER_PROPAGATES", default=False)
# With no worker, an email would otherwise send INLINE and block the HTTP
# response on the SMTP round-trip (seconds — enough to trip the SPA's ~20s
# request timeout and gunicorn's worker timeout). Dispatch it to a short-lived
# daemon thread instead so the request returns immediately (apps.common.tasking).
# Off in dev/tests: dev has a real worker, and tests want deterministic inline
# delivery into mail.outbox.
EMAIL_SEND_IN_THREAD = env.bool("EMAIL_SEND_IN_THREAD", default=not DEBUG)
# Split deploy (Django on Render + a Celery worker on a separate/free host):
# even with a worker (CELERY_TASK_ALWAYS_EAGER=False) keep user-facing OTP /
# transactional email on THIS host so delivery never depends on that worker
# being up. dispatch_task then runs those tasks in a local daemon thread
# (see apps.common.tasking) instead of publishing them to the broker. Only the
# heavy/background tasks (backups, AI ingestion, push fan-out) ride the broker
# to the worker. Off by default: a single-service or co-located-worker deploy
# keeps the previous behaviour.
EMAIL_TASKS_STAY_LOCAL = env.bool("EMAIL_TASKS_STAY_LOCAL", default=False)

# ---------------------------------------------------------------------------
# AI assistant (apps.assistant BFF <-> ML_hostel microservice)
#
# All AI/LLM logic lives in the separate ML_hostel service; Django only mints a
# short-lived, HMAC-signed context token (tenant + user + permissions) that the
# service verifies, then calls back to Django's real REST/tool endpoints so the
# assistant only ever sees data the caller is already allowed to see. Every knob
# is env-driven and the feature stays behind the ``ai_chat`` plan entitlement, so
# a workspace with no ML service configured simply has no AI surface.
# ---------------------------------------------------------------------------
ML_SERVICE_URL = env("ML_SERVICE_URL", default="http://ml_hostel:9000")
# Browser-facing base for SSE streams (through the gateway/proxy). Defaults to
# the API origin's sibling ``/ai`` path; overridden per-deploy.
ML_PUBLIC_URL = env("ML_PUBLIC_URL", default="")
# Shared secret used to sign/verify the context token. MUST be set in prod;
# falls back to the Django SECRET_KEY in dev so the stack boots without config.
ML_SHARED_SECRET = env("ML_SHARED_SECRET", default="")
# Context token lifetime (seconds) — long enough for a streamed answer + its
# tool round-trips, short enough to be low-value if leaked.
ML_TOKEN_TTL = env.int("ML_TOKEN_TTL", default=900)
# Wall-clock ceiling for a single tool callback the service makes into Django.
ML_TOOL_TIMEOUT = env.float("ML_TOOL_TIMEOUT", default=15.0)
# Wall-clock ceiling for the ingestion embed call (chunk+embed a whole document).
ML_INGEST_TIMEOUT = env.float("ML_INGEST_TIMEOUT", default=120.0)
# Top-K knowledge chunks returned to the assistant per retrieval.
ML_RAG_TOP_K = env.int("ML_RAG_TOP_K", default=5)

# ---------------------------------------------------------------------------
# Cache — Redis-backed (tenant resolution runs on every request, so cached
# tenant lookups must be sub-millisecond). apps.tenants.cache degrades to a
# direct DB lookup if Redis is unreachable, so a cache outage never 500s.
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("CACHE_URL", default=REDIS_URL),
        "KEY_PREFIX": "hostel",
        "TIMEOUT": 300,
        # Bound every Redis operation: a hung/unreachable Redis must degrade
        # (tenant/membership caches fall back to the DB) instead of stalling
        # the request for the OS TCP timeout.
        "OPTIONS": {
            "socket_connect_timeout": env.float("REDIS_CONNECT_TIMEOUT", default=1.5),
            "socket_timeout": env.float("REDIS_SOCKET_TIMEOUT", default=1.5),
        },
    }
}

# Sessions are only used by the Django admin (the API is JWT-cookie based) —
# keep them out of Postgres on the hot path via write-through cache.
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"

# Requests slower than this are logged at WARNING by RequestTimingMiddleware.
SLOW_REQUEST_MS = env.int("SLOW_REQUEST_MS", default=300)

# Audit events are inserted by a Celery worker (sync fallback if the broker is
# down) so the request never waits on the audit INSERT.
AUDIT_LOG_ASYNC = env.bool("AUDIT_LOG_ASYNC", default=True)

# Audit retention: events older than this are archived to JSONL then pruned
# (chain checkpoint advances so the surviving tail stays verifiable). 0 = keep
# forever. Archives are written under AUDIT_ARCHIVE_DIR.
AUDIT_RETENTION_DAYS = env.int("AUDIT_RETENTION_DAYS", default=365)
AUDIT_ARCHIVE_DIR = env.str("AUDIT_ARCHIVE_DIR", default=str(BASE_DIR / "audit-archive"))

# Membership (user↔hostel) checks are cached this many seconds; entries are
# also invalidated by UserHostel save/delete signals.
MEMBERSHIP_CACHE_TTL = env.int("MEMBERSHIP_CACHE_TTL", default=60)

# ---------------------------------------------------------------------------
# Multi-tenant workspaces (subdomain routing)
# ---------------------------------------------------------------------------
# The wildcard base domain tenants live under: <slug>.<TENANT_BASE_DOMAIN>.
# In production set e.g. TENANT_BASE_DOMAIN=myhostel.com and include
# ".myhostel.com" in ALLOWED_HOSTS. Default "localhost" makes
# http://everest.localhost:8000 work in dev with zero DNS setup.
TENANT_BASE_DOMAIN = env("TENANT_BASE_DOMAIN", default="localhost")
TENANT_URL_SCHEME = env("TENANT_URL_SCHEME", default="http" if DEBUG else "https")
# Host-header validation for wildcard workspace hosts: when the API itself is
# served on the tenant domain, every <slug>.<base> must pass ALLOWED_HOSTS.
# (".localhost" in dev makes http://everest.localhost:8000 work zero-config.)
if TENANT_BASE_DOMAIN:
    _wildcard_host = f".{TENANT_BASE_DOMAIN}"
    if _wildcard_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_wildcard_host)
# Workspace-username rules (see apps.tenants.validators). Max is capped at 63
# (DNS label limit) regardless of this setting.
WORKSPACE_USERNAME_MIN_LENGTH = env.int("WORKSPACE_USERNAME_MIN_LENGTH", default=3)
WORKSPACE_USERNAME_MAX_LENGTH = env.int("WORKSPACE_USERNAME_MAX_LENGTH", default=32)
# Extra reserved workspace names, merged with the built-in list in
# apps.tenants.validators.BASE_RESERVED_WORKSPACE_NAMES.
RESERVED_WORKSPACE_NAMES = env.list("RESERVED_WORKSPACE_NAMES", default=[])
# New workspaces start on a trial of this many days (0 = created active).
TENANT_TRIAL_DAYS = env.int("TENANT_TRIAL_DAYS", default=14)
# Tenant-lookup cache TTLs (seconds); entries are also invalidated on change.
TENANT_CACHE_TTL = env.int("TENANT_CACHE_TTL", default=300)
TENANT_NEGATIVE_CACHE_TTL = env.int("TENANT_NEGATIVE_CACHE_TTL", default=60)

# ---------------------------------------------------------------------------
# Edge security & rate limiting foundation (Prompt 07) — apps.security
# ---------------------------------------------------------------------------
# Master switch for the whole security layer (middleware + throttles). The
# full policy is layered: apps/security/defaults.py -> per-environment
# overlay -> YAML (SECURITY_CONFIG_FILE) -> SECURITY_* env vars -> DB
# (SecuritySetting rows, hot-reloaded). See docs/EDGE_SECURITY.md.
SECURITY_ENABLED = env.bool("SECURITY_ENABLED", default=True)
# Which environment overlay applies: development / testing / staging / production.
SECURITY_ENVIRONMENT = env(
    "SECURITY_ENVIRONMENT", default="development" if DEBUG else "production"
)
# Optional YAML policy file (infrastructure-managed layer).
SECURITY_CONFIG_FILE = env("SECURITY_CONFIG_FILE", default="")
# How often each process re-checks the shared config generation (hot reload).
SECURITY_CONFIG_RECHECK_SECONDS = env.int("SECURITY_CONFIG_RECHECK_SECONDS", default=5)
# Reverse proxies whose X-Forwarded-For is trusted (CIDRs). Empty = the
# private-network defaults in apps/security/defaults.py (Docker/K8s networks).
TRUSTED_PROXIES = env.list("TRUSTED_PROXIES", default=[])

# CAPTCHA (Prompt 08) — verified server-side by apps.security.captcha when the
# auth layer decides a challenge is required. The SECRET stays backend-only;
# the SITE KEY is public (inlined into the SPA as NEXT_PUBLIC_CAPTCHA_SITE_KEY).
# CAPTCHA is a no-op until a secret is set, regardless of config flags.
SECURITY_CAPTCHA_SECRET = env("SECURITY_CAPTCHA_SECRET", default="")
SECURITY_CAPTCHA_SITE_KEY = env("SECURITY_CAPTCHA_SITE_KEY", default="")

# ---------------------------------------------------------------------------
# Custom domains & white-label (Prompt 05)
# ---------------------------------------------------------------------------
# Per-plan custom-domain allowances (plan_name, lowercased). "default" covers
# unknown plans. Fully configurable without code changes, e.g.:
#   CUSTOM_DOMAIN_LIMITS=free:0,basic:1,professional:1,enterprise:3
_domain_limits_raw = env("CUSTOM_DOMAIN_LIMITS", default="free:0,basic:1,professional:1,enterprise:3,default:1")
CUSTOM_DOMAIN_LIMITS = {}
for _pair in _domain_limits_raw.split(","):
    if ":" in _pair:
        _plan, _n = _pair.split(":", 1)
        try:
            CUSTOM_DOMAIN_LIMITS[_plan.strip().lower()] = int(_n)
        except ValueError:
            pass

# Timezone-safe scheduling: run Celery Beat in the project timezone so "Sunday
# 2AM" / "1st of the month" mean local time, not UTC.
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = False
CELERY_TASK_ACKS_LATE = True

# ---------------------------------------------------------------------------
# Celery worker / broker hardening (Oracle worker deployment)
#
# These knobs are consumed by a *real* worker/producer; the eager Render
# deploy (CELERY_TASK_ALWAYS_EAGER=True) runs tasks inline and never touches
# the broker, so nothing here changes its behaviour. Everything is env-driven
# so the dedicated Oracle Celery VM can be tuned without a code change.
# See docs/deployment/oracle-worker.md.
# ---------------------------------------------------------------------------
# JSON-only wire format (safe; no pickle). These match Celery's own defaults
# but are pinned explicitly so the contract is visible in production.
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

# Survive a broker (Redis) blip: keep retrying the connection at startup and at
# runtime instead of crashing the worker. 0 = retry forever.
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = env.int(
    "CELERY_BROKER_CONNECTION_MAX_RETRIES", default=0
)

# Redis transport options. `visibility_timeout` is how long a task reserved by a
# worker may run before Redis assumes it was lost and redelivers it — it MUST
# exceed the longest-running task (backups can take a while), or that task gets
# duplicated. `socket_keepalive` lets a dead TCP connection be noticed promptly.
_celery_visibility_timeout = env.int("CELERY_VISIBILITY_TIMEOUT", default=3600)
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": _celery_visibility_timeout,
    "socket_keepalive": True,
    # Bound the broker connection so an unreachable/misconfigured broker can't
    # stall a producer (a web request doing .delay()/apply_async) on the OS TCP
    # timeout. A healthy broker connects in <10ms, so this only bites during an
    # outage — where failing fast lets the in-request sync fallbacks (audit /
    # security events) run instead of the request hanging and 502-ing.
    "socket_connect_timeout": env.float("CELERY_BROKER_CONNECT_TIMEOUT", default=2.0),
    "socket_timeout": env.float("CELERY_BROKER_SOCKET_TIMEOUT", default=2.0),
}
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
    "visibility_timeout": _celery_visibility_timeout,
}

# Every task in this project is fire-and-forget — nothing ever reads an
# AsyncResult — so don't store results at all. This keeps task execution
# (and, crucially, a producer's apply_async in a web request) from ever
# touching the result backend. Without it, a broken/unreachable result-store
# Redis makes Celery run a ~20×1s reconnect loop ("Connection to Redis lost:
# Retry N/20" → "Retry limit exceeded while trying to reconnect to the Celery
# result store backend") that blocked request-otp for ~20s even after the OTP
# itself was moved off the broker. Re-enable per-task with ignore_result=False
# if a task ever needs its return value.
CELERY_TASK_IGNORE_RESULT = env.bool("CELERY_TASK_IGNORE_RESULT", default=True)
# Belt-and-suspenders: if the result backend is ever contacted anyway, fail fast
# instead of the long reconnect loop above.
CELERY_RESULT_BACKEND_ALWAYS_RETRY = env.bool(
    "CELERY_RESULT_BACKEND_ALWAYS_RETRY", default=False
)
CELERY_RESULT_BACKEND_MAX_RETRIES = env.int(
    "CELERY_RESULT_BACKEND_MAX_RETRIES", default=1
)

# Fair dispatch: with long tasks, prefetch=1 stops one worker hogging the queue.
CELERY_WORKER_PREFETCH_MULTIPLIER = env.int(
    "CELERY_WORKER_PREFETCH_MULTIPLIER", default=1
)
# Recycle each worker process after N tasks / M kilobytes of RSS to cap slow
# memory growth on the small Oracle Free-tier VM (max_memory is in KB).
CELERY_WORKER_MAX_TASKS_PER_CHILD = env.int(
    "CELERY_WORKER_MAX_TASKS_PER_CHILD", default=1000
)
CELERY_WORKER_MAX_MEMORY_PER_CHILD = env.int(
    "CELERY_WORKER_MAX_MEMORY_PER_CHILD", default=300_000
)

# Publish-side retry policy (used by .delay()/apply_async on the producer): retry
# a few times if the broker is momentarily unreachable rather than raising.
CELERY_TASK_PUBLISH_RETRY = True
CELERY_TASK_PUBLISH_RETRY_POLICY = {
    "max_retries": env.int("CELERY_PUBLISH_MAX_RETRIES", default=3),
    "interval_start": 0,
    "interval_step": 0.5,
    "interval_max": 3,
}

# TLS for a rediss:// broker / result backend (e.g. Upstash, Redis Cloud TLS).
# Kombu warns "Secure redis scheme specified (rediss) with no ssl options" when
# a rediss:// URL is used without ssl options — supplying them silences it and
# actually verifies the certificate. Only set when the URL really is rediss://:
# passing ssl options with a plain redis:// URL raises ValueError at startup.
# CELERY_SSL_CERT_REQS: CERT_REQUIRED (default, verify the cert — correct for
# Upstash/Redis-Cloud which present valid certs), CERT_OPTIONAL, or CERT_NONE
# (only for providers with self-signed certs).
_celery_ssl_cert_reqs = {
    "CERT_NONE": ssl.CERT_NONE,
    "CERT_OPTIONAL": ssl.CERT_OPTIONAL,
    "CERT_REQUIRED": ssl.CERT_REQUIRED,
}.get(env("CELERY_SSL_CERT_REQS", default="CERT_REQUIRED").upper(), ssl.CERT_REQUIRED)

if CELERY_BROKER_URL.startswith("rediss://"):
    CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": _celery_ssl_cert_reqs}
if CELERY_RESULT_BACKEND.startswith("rediss://"):
    CELERY_REDIS_BACKEND_USE_SSL = {"ssl_cert_reqs": _celery_ssl_cert_reqs}

# ---------------------------------------------------------------------------
# Disaster recovery (Phase 4)
# ---------------------------------------------------------------------------
# Retention: how many backups to keep per hostel, per bucket.
BACKUP_RETENTION = {
    "daily": env.int("BACKUP_RETENTION_DAILY", default=7),    # keep 7 days
    "weekly": env.int("BACKUP_RETENTION_WEEKLY", default=4),  # keep 4 weeks
    "monthly": env.int("BACKUP_RETENTION_MONTHLY", default=12),  # keep 6-12 months
}
# Validation size sanity bounds for a stored (compressed) backup file.
BACKUP_MIN_BYTES = env.int("BACKUP_MIN_BYTES", default=20)
BACKUP_MAX_BYTES = env.int("BACKUP_MAX_BYTES", default=500 * 1024 * 1024)
# Where DR failure alerts are emailed (comma-separated). Empty = log/Sentry only.
DR_ALERT_EMAILS = env.list("DR_ALERT_EMAILS", default=[])
# A scheduled backup is considered "missing" if none succeeded within this many
# hours (drives the missed-backup monitor). RPO target = 24h.
BACKUP_MAX_AGE_HOURS = env.int("BACKUP_MAX_AGE_HOURS", default=26)

# Scheduled backups + retention (timezone = CELERY_TIMEZONE above).
CELERY_BEAT_SCHEDULE = {
    # Custom-domain health: DNS re-validation + SSL expiry monitoring (daily 3AM).
    "domains-revalidate": {
        "task": "domains.revalidate",
        "schedule": crontab(hour=3, minute=30),
    },
    "dr-daily-backups": {
        "task": "apps.backups.tasks.run_scheduled_backups",
        "schedule": crontab(hour=1, minute=0),  # every day 01:00
        "args": ("daily",),
    },
    "dr-weekly-backups": {
        "task": "apps.backups.tasks.run_scheduled_backups",
        "schedule": crontab(hour=2, minute=0, day_of_week=0),  # Sunday 02:00
        "args": ("weekly",),
    },
    "dr-monthly-backups": {
        "task": "apps.backups.tasks.run_scheduled_backups",
        "schedule": crontab(hour=3, minute=0, day_of_month=1),  # 1st of month 03:00
        "args": ("monthly",),
    },
    "dr-apply-retention": {
        "task": "apps.backups.tasks.apply_retention",
        "schedule": crontab(hour=4, minute=0),  # daily 04:00
    },
    "dr-check-missed-backups": {
        "task": "apps.backups.tasks.check_missed_backups",
        "schedule": crontab(hour="*/6", minute=30),  # every 6 hours
    },
    # Push notifications.
    "notifications-send-scheduled": {
        "task": "apps.notifications.tasks.send_scheduled_notifications",
        "schedule": crontab(minute="*"),  # every minute: dispatch anything due
    },
    "notifications-retry-failed": {
        "task": "apps.notifications.tasks.retry_failed_deliveries",
        "schedule": crontab(minute="*/5"),  # every 5 minutes
    },
    "notifications-prune-subscriptions": {
        "task": "apps.notifications.tasks.prune_expired_subscriptions",
        "schedule": crontab(hour=4, minute=30),  # daily 04:30
    },
    # Analytics aggregation pipeline: build durable rollups BEFORE pruning raw.
    "analytics-rollup": {
        "task": "apps.analytics.tasks.rollup_analytics",
        "schedule": crontab(hour=4, minute=35),  # daily 04:35 (before prune)
    },
    # PWA analytics retention.
    "analytics-prune-old": {
        "task": "apps.analytics.tasks.prune_old_analytics",
        "schedule": crontab(hour=4, minute=45),  # daily 04:45
    },
    # Security-event retention + expired temporary IP-rule reaping.
    "security-prune-events": {
        "task": "apps.security.tasks.prune_security_events",
        "schedule": crontab(hour=5, minute=0),  # daily 05:00
    },
    # Audit-trail retention: archive-then-prune events beyond AUDIT_RETENTION_DAYS.
    "auditlog-prune-events": {
        "task": "apps.auditlog.tasks.prune_audit_events",
        "schedule": crontab(hour=5, minute=15),  # daily 05:15
    },
    # Ops governance: auto start/complete maintenance windows at their times.
    "platformops-transition-maintenance": {
        "task": "apps.platformops.tasks.transition_maintenance_windows",
        "schedule": crontab(minute="*/1"),  # every minute
    },
    # Ops governance: reap expired feature-flag overrides.
    "platformops-reap-overrides": {
        "task": "apps.platformops.tasks.reap_feature_overrides",
        "schedule": crontab(minute=20),  # hourly at :20
    },
}

# ---------------------------------------------------------------------------
# Web Push (VAPID) — used by apps.notifications
# ---------------------------------------------------------------------------
# Generate a keypair with:  python manage.py vapid_keys
# The PUBLIC key is also exposed to the browser as NEXT_PUBLIC_VAPID_PUBLIC_KEY.
# Push delivery is disabled (no-op) until both VAPID_PRIVATE_KEY and
# VAPID_SUBJECT are set.
VAPID_PUBLIC_KEY = env("NEXT_PUBLIC_VAPID_PUBLIC_KEY", default="")
VAPID_PRIVATE_KEY = env("VAPID_PRIVATE_KEY", default="")
VAPID_SUBJECT = env("VAPID_SUBJECT", default="")
NOTIFICATIONS_MAX_RETRIES = env.int("NOTIFICATIONS_MAX_RETRIES", default=3)

# Application version surfaced on the system-status dashboard.
APP_VERSION = env("APP_VERSION", default="1.0.0")

# PWA analytics: how long to keep raw events before pruning.
ANALYTICS_RETENTION_DAYS = env.int("ANALYTICS_RETENTION_DAYS", default=90)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Console is always on. File logging is opt-in (LOG_TO_FILE), defaulting to on
# in production so errors are never lost to a discarded stdout stream.
LOG_LEVEL = env("LOG_LEVEL", default="DEBUG" if DEBUG else "INFO")
LOG_TO_FILE = env.bool("LOG_TO_FILE", default=not DEBUG)
LOG_DIR = Path(env("LOG_DIR", default=str(BASE_DIR / "logs")))

_log_handlers = ["console"]
_handlers_config = {
    "console": {
        "class": "logging.StreamHandler",
        "formatter": "verbose",
    },
}
if LOG_TO_FILE:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _log_handlers.append("file")
    _handlers_config["file"] = {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": str(LOG_DIR / "app.log"),
        "maxBytes": env.int("LOG_MAX_BYTES", default=10 * 1024 * 1024),
        "backupCount": env.int("LOG_BACKUP_COUNT", default=5),
        "formatter": "verbose",
    }

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{asctime} {levelname} {name} {process:d} {message}",
            "style": "{",
        },
    },
    "handlers": _handlers_config,
    "root": {"handlers": _log_handlers, "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": _log_handlers, "level": "INFO", "propagate": False},
        "django.request": {"handlers": _log_handlers, "level": "ERROR", "propagate": False},
        # Application logger namespace (use logging.getLogger("apps.<name>")).
        "apps": {"handlers": _log_handlers, "level": LOG_LEVEL, "propagate": False},
        "celery": {"handlers": _log_handlers, "level": "INFO", "propagate": False},
    },
}

# ---------------------------------------------------------------------------
# Error tracking (Sentry) — optional, activated only when SENTRY_DSN is set.
# Requires `sentry-sdk` in requirements; the import is guarded so the app boots
# without it installed.
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Prometheus metrics (observability) — optional, off by default.
# When PROMETHEUS_ENABLED=True, django-prometheus exposes /metrics (HTTP latency,
# request/response counts, DB query timings). The metrics endpoint is internal:
# expose it only to the monitoring network / scraper, never to the public web
# (the production Nginx config restricts /metrics to the private network).
# Wrapping middleware must bracket the stack: the "Before" middleware first and
# the "After" middleware last, so latency covers the whole request.
# ---------------------------------------------------------------------------
PROMETHEUS_ENABLED = env.bool("PROMETHEUS_ENABLED", default=False)
if PROMETHEUS_ENABLED:
    INSTALLED_APPS.append("django_prometheus")
    MIDDLEWARE.insert(0, "django_prometheus.middleware.PrometheusBeforeMiddleware")
    MIDDLEWARE.append("django_prometheus.middleware.PrometheusAfterMiddleware")

SENTRY_DSN = env("SENTRY_DSN", default="")
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            traces_sample_rate=env.float("SENTRY_TRACES_SAMPLE_RATE", default=0.0),
            send_default_pii=False,
            environment=env("SENTRY_ENVIRONMENT", default="production" if not DEBUG else "development"),
        )
    except ImportError:
        import warnings

        warnings.warn("SENTRY_DSN is set but sentry-sdk is not installed; error tracking is disabled.")
