"""Docker-profile test settings — real Postgres + Redis.

Unlike ``config.settings_test`` (in-memory SQLite/locmem, used locally and by
the pre-commit hook for speed), this module keeps the real, env-driven
``DATABASES``/``CACHES``/``CELERY_*`` from ``config.settings`` so the suite
actually exercises the Postgres engine — the one axis ``settings_test``
deliberately skips. Used by the ``docker compose --profile test`` `test`
service, which points ``DATABASE_URL``/``REDIS_URL`` at the ephemeral
``postgres_test``/``redis_test`` containers.

Keeps the same fast/deterministic test conveniences as ``settings_test``
(cheap password hasher, Axes and DRF throttling disabled, logging
silenced) so results are apples-to-apples with the local suite.

Run with::

    DJANGO_SETTINGS_MODULE=config.settings_test_docker pytest
"""
from .settings import *  # noqa: F401,F403

# --- Speed: cheap password hashing -----------------------------------------
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# --- Brute-force / rate limiting: off by default (opt back in per-test) -----
AXES_ENABLED = False
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

# Edge security foundation off by default; its own tests re-enable it with
# override_settings + the deterministic in-memory limiter backend.
SECURITY_ENABLED = False
SECURITY_ENVIRONMENT = "testing"

# Disable DRF throttling globally; throttle-specific tests override this.
REST_FRAMEWORK = {**REST_FRAMEWORK}  # noqa: F405
REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"] = ()
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {}

# --- Celery eager: the `test` profile has no worker service, so anything
# dispatched via apply_async() (e.g. apps.auditlog.tasks.persist_audit_event)
# would otherwise sit in Redis unconsumed and silently never happen. Real
# Postgres/Redis connectivity is still exercised for everything else. --------
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# --- Quieten logging during tests ------------------------------------------
import logging  # noqa: E402

logging.disable(logging.CRITICAL)
