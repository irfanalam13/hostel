"""Cached tenant lookup.

Tenant resolution runs on *every* request before authentication, so the
hot path must avoid a DB round-trip. Hostels are cached (pickled model
instances) under three keys — slug, code and id — with a short TTL plus
explicit invalidation from the ``post_save`` / ``post_delete`` signals wired
in ``apps.py``.

Unknown identifiers are negative-cached briefly so a burst of requests to a
non-existent subdomain cannot hammer the database.

Every helper degrades gracefully: if the cache backend is down, we fall
through to the database rather than failing the request.
"""
import logging

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Bump the version segment if the cached payload shape ever changes.
_KEY_PREFIX = "tenant:v1"
_MISS = "__miss__"  # negative-cache sentinel


def _ttl() -> int:
    return int(getattr(settings, "TENANT_CACHE_TTL", 300))


def _negative_ttl() -> int:
    return int(getattr(settings, "TENANT_NEGATIVE_CACHE_TTL", 60))


def _key(kind: str, value: str) -> str:
    return f"{_KEY_PREFIX}:{kind}:{value}"


def _cached_lookup(kind: str, value: str, db_fetch):
    """Generic cache-aside lookup with negative caching and cache-failure fallback."""
    key = _key(kind, value)
    try:
        hit = cache.get(key)
    except Exception:  # cache down — serve from the DB, don't 500 the request
        logger.warning("tenant cache read failed for %s", key, exc_info=True)
        hit = None

    if hit == _MISS:
        return None
    if hit is not None:
        return hit

    tenant = db_fetch()
    try:
        cache.set(key, tenant if tenant is not None else _MISS,
                  _ttl() if tenant is not None else _negative_ttl())
    except Exception:
        logger.warning("tenant cache write failed for %s", key, exc_info=True)
    return tenant


def get_tenant_by_slug(slug: str):
    """Resolve a live (non-soft-deleted) tenant by workspace username."""
    from .models import Hostel

    slug = (slug or "").strip().lower()
    if not slug:
        return None
    return _cached_lookup(
        "slug", slug, lambda: Hostel.objects.filter(slug=slug, is_deleted=False).first()
    )


def get_tenant_by_code(code: str):
    """Resolve a live tenant by legacy Hostel ID code (``HTL-XXXXXXXX``)."""
    from .models import Hostel

    code = (code or "").strip().upper()
    if not code:
        return None
    return _cached_lookup(
        "code", code, lambda: Hostel.objects.filter(code=code, is_deleted=False).first()
    )


def get_tenant_by_id(tenant_id: str):
    """Resolve a live tenant by UUID primary key."""
    from .models import Hostel

    tenant_id = str(tenant_id or "").strip()
    if not tenant_id:
        return None

    def _fetch():
        try:
            return Hostel.objects.filter(id=tenant_id, is_deleted=False).first()
        except (ValueError, Exception):
            return None

    return _cached_lookup("id", tenant_id, _fetch)


def get_alias_hostel(slug: str):
    """The hostel behind a retired workspace username (rename alias), or None.
    Cached (incl. negative results) exactly like tenant lookups — this runs on
    every unknown-subdomain request, so it must not add a DB hit per probe."""
    from .models import WorkspaceAlias

    slug = (slug or "").strip().lower()
    if not slug:
        return None

    def _fetch():
        alias = (
            WorkspaceAlias.objects.filter(slug=slug).select_related("hostel").first()
        )
        return alias.hostel if alias else None

    return _cached_lookup("alias", slug, _fetch)


def get_tenant_by_custom_domain(host: str):
    """The hostel behind an ACTIVE custom domain, or None. Cached (negative
    results included) — this runs for every request on a non-platform host."""
    host = (host or "").strip().lower().rstrip(".")
    if not host:
        return None

    def _fetch():
        from apps.domains.models import CustomDomain

        record = (
            CustomDomain.objects.filter(domain=host, status=CustomDomain.Status.ACTIVE)
            .select_related("hostel")
            .first()
        )
        if record is None or record.hostel.is_deleted:
            return None
        return record.hostel

    return _cached_lookup("domain", host, _fetch)


def invalidate_custom_domain_cache(host: str) -> None:
    try:
        cache.delete(_key("domain", (host or "").strip().lower().rstrip(".")))
    except Exception:
        pass  # TTL bounds staleness


def invalidate_alias_cache(slug: str) -> None:
    try:
        cache.delete(_key("alias", (slug or "").strip().lower()))
    except Exception:
        pass  # TTL bounds staleness


def invalidate_tenant_cache(hostel) -> None:
    """Drop every cache entry for a tenant.

    Called from model signals on save/delete, so any change (rename, status
    change, suspension, archive, subscription update) takes effect on the
    next request.
    """
    keys = [_key("id", str(hostel.pk))]
    if getattr(hostel, "slug", None):
        keys.append(_key("slug", hostel.slug))
    if getattr(hostel, "code", None):
        keys.append(_key("code", hostel.code))
    try:
        cache.delete_many(keys)
    except Exception:
        logger.warning("tenant cache invalidation failed for %s", hostel.pk, exc_info=True)
