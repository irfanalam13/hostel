"""Test settings — fast, deterministic, isolated.

Imports the real settings and overrides only what makes the suite fast and
reliable:

* in-memory SQLite (no disk, fresh per run)
* fast password hasher (login/signup tests don't pay bcrypt cost)
* django-axes and DRF throttling disabled by default — the few tests that
  exercise brute-force lockout / rate limiting re-enable them locally with
  ``override_settings`` so they don't bleed lockout state into other tests
* locmem email backend so password-reset emails are captured in ``mail.outbox``
* Celery runs tasks eagerly (no broker needed)

Run with::

    pytest                      # uses this module via pytest.ini
    DJANGO_SETTINGS_MODULE=config.settings_test python manage.py test
"""
import os

# The base settings read .env; force DEBUG on for sane local defaults before import.
os.environ.setdefault("DEBUG", "True")

from .settings import *  # noqa: F401,F403

# --- Database: in-memory SQLite, isolated from dev db.sqlite3 --------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# --- Speed: cheap password hashing -----------------------------------------
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# --- Brute-force / rate limiting: off by default (opt back in per-test) -----
AXES_ENABLED = False
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

# Disable DRF throttling globally; throttle-specific tests override this.
REST_FRAMEWORK = {**REST_FRAMEWORK}  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = ()
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}

# --- Cache: in-memory (no Redis in CI); tenant-cache tests still exercise the
# cache-aside logic against locmem ------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "tests",
    }
}

# --- Email captured in memory ----------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# --- Celery eager (no Redis broker in CI) ----------------------------------
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# --- Media to a temp-ish location so ImageField/FileField tests don't litter -
MEDIA_ROOT = BASE_DIR / "test-media"  # noqa: F405

# --- Quieten logging during tests ------------------------------------------
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
