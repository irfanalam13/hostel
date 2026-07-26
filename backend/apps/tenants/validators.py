"""Workspace-username (tenant slug) validation.

The workspace username is the *permanent* unique identifier of a tenant and
doubles as its subdomain (``everest`` -> ``https://everest.myhostel.com``), so
the rules here are exactly the DNS-label rules plus a configurable reserved
list:

* lowercase letters, digits and hyphens only
* must start and end with a letter or digit
* length between ``WORKSPACE_USERNAME_MIN_LENGTH`` and
  ``WORKSPACE_USERNAME_MAX_LENGTH`` (settings-configurable, hard-capped at 63
  — the DNS label limit)
* not on the reserved list (``admin``, ``api``, ``www``, …)

This module is deliberately free of model imports so it can be used from
models, serializers, middleware and migrations without circular imports.
DB-touching checks (availability, suggestions) live in ``services.py``.
"""
import re

from django.conf import settings
from django.core.exceptions import ValidationError

# DNS label: alnum, hyphens allowed in the middle only.
WORKSPACE_USERNAME_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

# Hard DNS limit for a single label — settings may lower it, never raise it.
_DNS_LABEL_MAX = 63

# Subdomains that must never become a workspace. Merged with the
# settings-provided list so deployments can extend (but not shrink) it.
BASE_RESERVED_WORKSPACE_NAMES = frozenset({
    "admin", "api", "www", "mail", "root", "dashboard", "system", "support",
    "login", "auth", "docs", "static", "media", "assets", "cdn", "status",
    "health", "monitor", "test", "app", "staging", "dev", "demo", "internal",
    "billing", "smtp", "imap", "pop", "ftp", "ns1", "ns2", "webmail",
    "signup", "register", "account", "accounts", "security", "help", "blog",
})


def reserved_workspace_names() -> frozenset:
    """The effective reserved set: built-ins + RESERVED_WORKSPACE_NAMES setting."""
    extra = getattr(settings, "RESERVED_WORKSPACE_NAMES", [])
    return BASE_RESERVED_WORKSPACE_NAMES | {str(n).strip().lower() for n in extra if n}


def workspace_username_limits() -> tuple[int, int]:
    min_len = int(getattr(settings, "WORKSPACE_USERNAME_MIN_LENGTH", 3))
    max_len = min(int(getattr(settings, "WORKSPACE_USERNAME_MAX_LENGTH", 32)), _DNS_LABEL_MAX)
    return max(min_len, 1), max_len


def normalize_workspace_username(value: str) -> str:
    """Trim + lowercase. Never invents characters — validation rejects the rest."""
    return (value or "").strip().lower()


def validate_workspace_username(value: str) -> str:
    """Validate an already-normalized workspace username.

    Returns the value on success; raises ``ValidationError`` with a stable
    ``code`` (``required`` / ``too_short`` / ``too_long`` / ``invalid`` /
    ``reserved``) so API consumers can branch on the failure reason.
    """
    min_len, max_len = workspace_username_limits()

    if not value:
        raise ValidationError("Workspace username is required.", code="required")
    if len(value) < min_len:
        raise ValidationError(
            f"Workspace username must be at least {min_len} characters.", code="too_short"
        )
    if len(value) > max_len:
        raise ValidationError(
            f"Workspace username must be at most {max_len} characters.", code="too_long"
        )
    if not WORKSPACE_USERNAME_RE.match(value):
        raise ValidationError(
            "Use lowercase letters, numbers and hyphens only; it must start and "
            "end with a letter or number.",
            code="invalid",
        )
    if value in reserved_workspace_names():
        raise ValidationError("This workspace username is reserved.", code="reserved")
    return value


def clean_workspace_username(value: str) -> str:
    """Normalize + validate in one step (the usual entry point)."""
    return validate_workspace_username(normalize_workspace_username(value))
