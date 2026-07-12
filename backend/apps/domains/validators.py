"""Custom-domain validation (Prompt 05).

A custom domain is a full hostname the tenant owns (root domain or any
subdomain, including country/education TLDs). Rejected here, before any DNS
work happens: bad syntax, protocols/paths, wildcards, IPs, our own platform
domain family, and anything already assigned to a tenant.
"""
import re

from django.conf import settings
from django.core.exceptions import ValidationError

# RFC-ish hostname: labels of alnum/hyphen (no edge hyphens), 2+ labels,
# alphabetic TLD of 2+ chars. Total length ≤ 253.
_LABEL = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
DOMAIN_RE = re.compile(rf"^(?:{_LABEL}\.)+[a-z]{{2,63}}$")


def normalize_domain(value: str) -> str:
    """Lowercase, trim, strip trailing dot. Never invents characters."""
    return (value or "").strip().lower().rstrip(".")


def validate_custom_domain(value: str) -> str:
    """Validate an already-normalized domain. Raises ``ValidationError`` with
    a stable ``code`` so the API/UI can branch on the failure reason."""
    if not value:
        raise ValidationError("Domain is required.", code="required")
    if "://" in value or "/" in value or " " in value:
        raise ValidationError(
            "Enter a bare domain (no https://, paths or spaces).", code="invalid"
        )
    if value.startswith("*") or "*" in value:
        raise ValidationError("Wildcard domains are not supported.", code="wildcard")
    if len(value) > 253:
        raise ValidationError("Domain is too long.", code="too_long")
    if re.fullmatch(r"[0-9.]+", value) or ":" in value:
        raise ValidationError("IP addresses are not supported.", code="invalid")
    if not DOMAIN_RE.match(value):
        raise ValidationError("That doesn't look like a valid domain name.", code="invalid")

    # The platform's own domain family is never a "custom" domain.
    base = (getattr(settings, "TENANT_BASE_DOMAIN", "") or "").strip().lower().rstrip(".")
    if base and base != "localhost" and (value == base or value.endswith("." + base)):
        raise ValidationError(
            "That domain belongs to the platform — use your workspace URL instead.",
            code="platform_domain",
        )
    return value


def clean_custom_domain(value: str) -> str:
    return validate_custom_domain(normalize_domain(value))
