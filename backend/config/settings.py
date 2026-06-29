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
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
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

    # Tenant resolution
    "apps.common.middleware.HostelResolveMiddleware",
    # Audit trail
    "apps.auditlog.middleware.AuditLogMiddleware",
    "apps.common.middleware.HostelContextMiddleware",

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
# Database — Postgres via DATABASE_URL (.env), SQLite fallback for local dev
# ---------------------------------------------------------------------------
# DATABASE_URL is read from backend/.env. A full Postgres URL works as-is, e.g.:
#   postgresql://USER:PASS@HOST:5432/DBNAME?sslmode=require
# Query params (sslmode, channel_binding, …) are passed through to the driver
# as OPTIONS, so managed providers like Neon/Supabase work without extra config.
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}

# Production hardening for Postgres: reuse connections across requests
# (essential with pooled providers like Neon) and verify each pooled connection
# is alive before use. SQLite ignores these, so guard on the engine.
if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=600)
    DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

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
    # Rate limiting / abuse protection
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.ScopedRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": env("THROTTLE_ANON", default="60/min"),
        "user": env("THROTTLE_USER", default="1000/hour"),
        "auth": env("THROTTLE_AUTH", default="5/min"),
        # Tighter, dedicated buckets for sensitive endpoints (ScopedRateThrottle).
        "signup": env("THROTTLE_SIGNUP", default="3/hour"),
        "password_reset": env("THROTTLE_PASSWORD_RESET", default="5/hour"),
        "payment": env("THROTTLE_PAYMENT", default="120/min"),
        "backup": env("THROTTLE_BACKUP", default="10/hour"),
        "admissions": env("THROTTLE_ADMISSIONS", default="20/hour"),
        # Public review submissions from the landing page.
        "review": env("THROTTLE_REVIEW", default="5/hour"),
        # Public sales/demo lead submissions from the landing page.
        "lead": env("THROTTLE_LEAD", default="10/hour"),
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
CORS_ALLOW_HEADERS = list(default_headers) + ["x-hostel-code", "x-hostel-id"]
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
# Email (password reset). Console backend in dev; SMTP via env in prod.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend"
    if DEBUG
    else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="no-reply@hostel.local")
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

SPECTACULAR_SETTINGS = {
    "TITLE": "Hostel SaaS API",
    "VERSION": "1.0.0",
}

# ---------------------------------------------------------------------------
# Files / i18n / misc
# ---------------------------------------------------------------------------
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# WhiteNoise: compress + hash static assets so Gunicorn can serve them in prod.
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

# Timezone-safe scheduling: run Celery Beat in the project timezone so "Sunday
# 2AM" / "1st of the month" mean local time, not UTC.
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = False
CELERY_TASK_ACKS_LATE = True

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
    # PWA analytics retention.
    "analytics-prune-old": {
        "task": "apps.analytics.tasks.prune_old_analytics",
        "schedule": crontab(hour=4, minute=45),  # daily 04:45
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
