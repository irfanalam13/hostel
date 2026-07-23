"""Custom-domain services: DNS verification, SSL monitoring, activation.

DNS and SSL probes are pluggable (module-level callables) so tests and
offline environments never hit the network. Real lookups use dnspython
(TXT/CNAME) and a plain TLS handshake for certificate expiry — certificate
*provisioning* itself is platform infrastructure (Vercel custom domains /
Caddy / certbot; see docs), which is why the model tracks status rather than
issuing certs.
"""
import logging
import socket
import ssl as ssl_lib
from datetime import datetime, timezone as dt_timezone

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.tenants.cache import invalidate_custom_domain_cache

from .models import CustomDomain
from .validators import clean_custom_domain

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Pluggable probes
# --------------------------------------------------------------------------- #
def _dns_lookup(record_type: str, name: str) -> list[str]:
    """Resolve DNS records; [] on any failure. Swapped out in tests."""
    try:
        import dns.resolver

        answers = dns.resolver.resolve(name, record_type, lifetime=5)
        values = []
        for answer in answers:
            text = answer.to_text().strip('"')
            values.append(text.rstrip(".").lower() if record_type == "CNAME" else text)
        return values
    except Exception:
        return []


def _ssl_probe(domain: str) -> datetime | None:
    """The domain's certificate expiry (UTC), or None if unreachable."""
    try:
        context = ssl_lib.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as tls:
                cert = tls.getpeercert()
        expires = cert.get("notAfter")
        if not expires:
            return None
        parsed = datetime.strptime(expires, "%b %d %H:%M:%S %Y %Z")
        return parsed.replace(tzinfo=dt_timezone.utc)
    except Exception:
        return None


dns_lookup = _dns_lookup
ssl_probe = _ssl_probe


# --------------------------------------------------------------------------- #
# Plan gating
# --------------------------------------------------------------------------- #
def domain_limit_for(hostel) -> int:
    """How many custom domains this workspace's plan allows (configurable)."""
    limits = getattr(settings, "CUSTOM_DOMAIN_LIMITS", {}) or {}
    plan = (hostel.plan_name or "").strip().lower()
    if plan in limits:
        return int(limits[plan])
    return int(limits.get("default", 1))


def _audit(hostel, actor, message, meta=None):
    try:
        from apps.auditlog.models import AuditEvent

        AuditEvent.objects.create(
            hostel_id=hostel.pk,
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            action=AuditEvent.Action.UPDATE,
            entity_type="custom_domain",
            entity_id=str(hostel.pk),
            message=message,
            meta=meta or {},
        )
    except Exception:
        logger.exception("custom-domain audit write failed (hostel=%s)", hostel.pk)


# --------------------------------------------------------------------------- #
# Lifecycle
# --------------------------------------------------------------------------- #
def add_domain(hostel, domain: str, actor=None) -> CustomDomain:
    domain = clean_custom_domain(domain)

    if CustomDomain.objects.filter(domain=domain).exists():
        # Same error whether it's ours or another tenant's — no tenant oracle.
        raise ValidationError({"domain": "This domain is already connected to a workspace."},
                              code="taken")

    limit = domain_limit_for(hostel)
    current = CustomDomain.objects.filter(hostel=hostel).count()
    if current >= limit:
        raise ValidationError(
            {"domain": (
                f"Your plan allows {limit} custom domain{'s' if limit != 1 else ''}. "
                "Upgrade to connect more." if limit else
                "Custom domains are not included in your plan. Upgrade to connect one."
            )},
            code="plan_limit",
        )

    record = CustomDomain.objects.create(hostel=hostel, domain=domain)
    _audit(hostel, actor, "Custom domain added", {"domain": domain})
    return record


def check_dns(record: CustomDomain) -> dict:
    """One DNS pass: TXT ownership token + CNAME to the workspace host."""
    txt_values = dns_lookup("TXT", record.txt_record["host"])
    cname_values = dns_lookup("CNAME", record.domain)
    health = {
        "txt": record.verification_token in txt_values,
        "cname": record.cname_record["value"].lower() in cname_values,
        "checked_at": timezone.now().isoformat(),
    }
    record.dns_health = health
    record.last_checked_at = timezone.now()
    record.save(update_fields=["dns_health", "last_checked_at", "updated_at"])
    return health


def verify_domain(record: CustomDomain, actor=None) -> CustomDomain:
    """Attempt ownership verification (TXT preferred, CNAME accepted).
    Safe to call repeatedly — the UI and the periodic task both retry it."""
    health = check_dns(record)

    if health["txt"] or health["cname"]:
        record.verification_method = "txt" if health["txt"] else "cname"
        record.verified_at = timezone.now()
        record.status = CustomDomain.Status.VERIFIED
        record.last_error = ""
        record.save(update_fields=["verification_method", "verified_at", "status",
                                   "last_error", "updated_at"])
        _audit(record.hostel, actor, "Custom domain verified",
               {"domain": record.domain, "method": record.verification_method})
        return record

    record.status = CustomDomain.Status.FAILED if record.verified_at is None else record.status
    record.last_error = (
        "Verification records not found yet. DNS changes can take up to 48 hours "
        "to propagate — we'll keep retrying automatically."
    )
    record.save(update_fields=["status", "last_error", "updated_at"])
    return record


@transaction.atomic
def activate_domain(record: CustomDomain, actor=None, make_primary: bool = True) -> CustomDomain:
    """Turn a verified domain on: it starts resolving to this workspace, and
    (by default) becomes the primary public URL. Caches are invalidated so the
    change is immediate."""
    if record.status not in (CustomDomain.Status.VERIFIED, CustomDomain.Status.ACTIVE,
                             CustomDomain.Status.DISABLED):
        raise ValidationError({"detail": "Verify domain ownership before activating."},
                              code="not_verified")
    if record.verified_at is None:
        raise ValidationError({"detail": "Verify domain ownership before activating."},
                              code="not_verified")

    record.status = CustomDomain.Status.ACTIVE
    record.save(update_fields=["status", "updated_at"])
    if make_primary:
        set_primary_domain(record, actor=actor)
    else:
        invalidate_custom_domain_cache(record.domain)
    check_ssl(record)
    _audit(record.hostel, actor, "Custom domain activated",
           {"domain": record.domain, "primary": make_primary})
    return record


@transaction.atomic
def set_primary_domain(record: CustomDomain, actor=None) -> CustomDomain:
    if record.status != CustomDomain.Status.ACTIVE:
        raise ValidationError({"detail": "Only an active domain can be primary."})
    CustomDomain.objects.filter(hostel=record.hostel, is_primary=True).exclude(
        pk=record.pk
    ).update(is_primary=False)
    record.is_primary = True
    record.save(update_fields=["is_primary", "updated_at"])
    for domain in CustomDomain.objects.filter(hostel=record.hostel):
        invalidate_custom_domain_cache(domain.domain)
    _audit(record.hostel, actor, "Primary domain changed", {"domain": record.domain})
    return record


def disable_domain(record: CustomDomain, actor=None) -> CustomDomain:
    record.status = CustomDomain.Status.DISABLED
    record.is_primary = False
    record.save(update_fields=["status", "is_primary", "updated_at"])
    invalidate_custom_domain_cache(record.domain)
    _audit(record.hostel, actor, "Custom domain disabled", {"domain": record.domain})
    return record


def remove_domain(record: CustomDomain, actor=None) -> None:
    domain = record.domain
    hostel = record.hostel
    record.delete()
    invalidate_custom_domain_cache(domain)
    _audit(hostel, actor, "Custom domain removed", {"domain": domain})


def check_ssl(record: CustomDomain) -> CustomDomain:
    """Refresh the certificate snapshot. Expiring-soon threshold: 21 days."""
    expires = ssl_probe(record.domain)
    if expires is None:
        record.ssl_status = CustomDomain.SslStatus.PENDING
        record.ssl_expires_at = None
    else:
        record.ssl_expires_at = expires
        days_left = (expires - timezone.now()).days
        if days_left < 0:
            record.ssl_status = CustomDomain.SslStatus.EXPIRED
        elif days_left <= 21:
            record.ssl_status = CustomDomain.SslStatus.EXPIRING
        else:
            record.ssl_status = CustomDomain.SslStatus.ACTIVE
    record.save(update_fields=["ssl_status", "ssl_expires_at", "updated_at"])
    return record


# --------------------------------------------------------------------------- #
# Resolution + public URL helpers
# --------------------------------------------------------------------------- #
def primary_domain_for(hostel) -> CustomDomain | None:
    return CustomDomain.objects.filter(
        hostel=hostel, is_primary=True, status=CustomDomain.Status.ACTIVE
    ).first()


def public_url_for(hostel) -> str:
    """The canonical public URL: the primary custom domain when one is active,
    else the default workspace URL. Drives SEO, sitemaps and share links."""
    primary = primary_domain_for(hostel)
    if primary:
        return f"https://{primary.domain}"
    return hostel.workspace_url
