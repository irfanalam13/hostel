#!/usr/bin/env python3
"""Assert the production security posture of Django settings under DEBUG=False.

Run from the `backend/` directory with a production-shaped environment already
exported (DEBUG=False, ALLOWED_HOSTS, CORS/CSRF origins, a strong SECRET_KEY).
`manage.py check --deploy` covers Django's own checks; this adds explicit,
fail-loud assertions for the exact items the CI/CD roadmap (Prompt 02) calls out
so a future settings refactor can't silently weaken them.
"""
from __future__ import annotations

import os
import sys

# Run from backend/: make the Django project (config/) importable even though
# this script lives elsewhere (its own dir, not cwd, is what lands on sys.path).
sys.path.insert(0, os.getcwd())

# Keep the ✓/✗ glyphs printable on a non-UTF-8 console (e.g. Windows cp1252).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):  # pragma: no cover
    pass

import django
from django.conf import settings

django.setup()

failures: list[str] = []


def require(condition: bool, message: str) -> None:
    if not condition:
        failures.append(message)
    else:
        print(f"✓ {message}")


require(settings.DEBUG is False, "DEBUG is False")
require(bool(settings.ALLOWED_HOSTS), "ALLOWED_HOSTS is non-empty")
require(settings.SESSION_COOKIE_SECURE is True, "SESSION_COOKIE_SECURE is True")
require(settings.CSRF_COOKIE_SECURE is True, "CSRF_COOKIE_SECURE is True")
require(settings.SESSION_COOKIE_HTTPONLY is True, "SESSION_COOKIE_HTTPONLY is True")
require(settings.SECURE_SSL_REDIRECT is True, "SECURE_SSL_REDIRECT is True")
require(settings.SECURE_HSTS_SECONDS >= 31536000, "SECURE_HSTS_SECONDS >= 1 year")
require(settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is True, "HSTS includeSubDomains is on")
require(settings.SECURE_CONTENT_TYPE_NOSNIFF is True, "SECURE_CONTENT_TYPE_NOSNIFF is True")
require(getattr(settings, "X_FRAME_OPTIONS", "") == "DENY", "X_FRAME_OPTIONS is DENY")
require("*" not in settings.CORS_ALLOWED_ORIGINS, "CORS does not allow '*'")

middleware = set(settings.MIDDLEWARE)
for required_mw in (
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
):
    require(required_mw in middleware, f"{required_mw} is enabled")

if failures:
    print("\n✗ Production settings assertions FAILED:", file=sys.stderr)
    for f in failures:
        print(f"  - {f}", file=sys.stderr)
    sys.exit(1)

print("\nAll production settings assertions passed.")
