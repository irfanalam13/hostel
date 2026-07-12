"""Tenant resolution middleware — runs on every request, before authentication.

Resolution order (first identifier present wins):

1. **Subdomain** of ``TENANT_BASE_DOMAIN`` — ``everest.myhostel.com`` -> slug
   ``everest``. This is the canonical workspace routing. Reserved labels
   (``www``, ``api``, …) and the bare root domain resolve to *no* tenant so
   marketing/signup/auth endpoints keep working there.
2. **X-WORKSPACE header** (workspace slug) — for split-domain deployments
   where the SPA lives on the wildcard domain but calls an API on another
   host (e.g. Vercel frontend + Render API): the frontend forwards the
   workspace it is serving.
3. **X-HOSTEL-CODE header** (legacy ``HTL-XXXXXXXX`` Hostel ID).
4. **X-HOSTEL-ID header** (legacy UUID).

If an identifier was *presented* but doesn't resolve to a live workspace the
request is terminated with 404 — it never reaches auth or business logic.
Resolved workspaces are then gated on status: suspended/expired/pending get
403 with a machine-readable code; archived and soft-deleted behave as gone
(404). Lookups go through the Redis-backed cache in ``cache.py``.

Note this attaches *context only*. Authorization (is the caller a member of
this workspace?) is enforced downstream by ``CookieJWTAuthentication`` and
``HasHostelContext`` — which also audit denied cross-tenant attempts.
"""
import ipaddress
import logging

from django.conf import settings
from django.http import HttpResponsePermanentRedirect, JsonResponse

from . import cache as tenant_cache
from .models import HOSTEL_CODE_RE, WorkspaceStatus
from .validators import (
    normalize_workspace_username,
    reserved_workspace_names,
    WORKSPACE_USERNAME_RE,
)

logger = logging.getLogger(__name__)

# Liveness probes must stay dependency-free (no DB / cache hit).
_HEALTH_PREFIX = "/health/"

# Hostnames that are never tenant hosts.
_LOCAL_HOSTS = {"localhost", "127.0.0.1", "testserver", "0.0.0.0"}


def _is_platform_host(host: str) -> bool:
    """True when the host is local, an IP, or in the platform's own domain
    family (base domain or any subdomain of it) — i.e. NOT a candidate for
    custom-domain resolution."""
    host = (host or "").split(":")[0].strip().lower().rstrip(".")
    if not host or host in _LOCAL_HOSTS or _is_ip(host):
        return True
    if host.endswith(".localhost"):
        return True
    base = (getattr(settings, "TENANT_BASE_DOMAIN", "") or "").strip().lower().rstrip(".")
    if base and (host == base or host.endswith("." + base)):
        return True
    return False


def _json_error(status_code: int, message: str, code: str) -> JsonResponse:
    # Mirrors the StandardJSONRenderer envelope so SPA error handling is uniform.
    return JsonResponse(
        {"success": False, "message": message, "data": None, "meta": {"code": code}},
        status=status_code,
    )


def _is_ip(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def extract_workspace_subdomain(host: str) -> str | None:
    """Return the workspace label from a hostname, or None if the host is not
    a tenant host (root domain, reserved label, localhost, IP, other domain).

    Returns the *raw* label (may still be invalid — the caller validates) so
    ``bad_label.myhostel.com`` can be rejected explicitly rather than silently
    treated as the root domain.
    """
    host = (host or "").split(":")[0].strip().lower().rstrip(".")
    if not host or host in _LOCAL_HOSTS or _is_ip(host):
        return None

    base = (getattr(settings, "TENANT_BASE_DOMAIN", "") or "").strip().lower().rstrip(".")
    if not base or host == base:
        return None
    if not host.endswith("." + base):
        return None  # a different domain entirely (e.g. the Render API host)

    label = host[: -(len(base) + 1)]
    if "." in label:
        # Nested subdomains (a.b.myhostel.com) are not workspace hosts.
        return None
    if label in reserved_workspace_names():
        return None  # www./api./… behave as the root domain
    return label


class TenantResolutionMiddleware:
    """Resolve the workspace for every request and attach it as
    ``request.tenant`` (and ``request.hostel`` for backward compatibility)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        request.hostel = None

        # CORS preflight carries no credentials/context — let it through.
        if request.method == "OPTIONS":
            return self.get_response(request)

        # Health checks never touch DB/cache.
        if request.path.startswith(_HEALTH_PREFIX):
            return self.get_response(request)

        tenant, presented = self._resolve(request)

        if presented and tenant is None:
            # Renamed workspace? Old usernames live on as aliases — answer
            # with a permanent redirect to the new URL so bookmarks keep
            # working (Prompt 04 rename policy).
            moved = self._alias_redirect(request)
            if moved is not None:
                return moved
            return _json_error(404, "Workspace not found.", "workspace_not_found")

        if tenant is not None:
            gate = self._status_gate(tenant)
            if gate is not None:
                return gate
            request.tenant = tenant
            request.hostel = tenant  # legacy name used across the codebase

        return self.get_response(request)

    # ------------------------------------------------------------------ #
    def _resolve(self, request):
        """Returns (tenant_or_None, identifier_was_presented)."""
        # 1) Subdomain of the platform base domain
        try:
            host = request.get_host()
        except Exception:  # DisallowedHost is normally raised before us
            host = request.META.get("HTTP_HOST", "")
        label = extract_workspace_subdomain(host)
        if label is not None:
            label = normalize_workspace_username(label)
            if not WORKSPACE_USERNAME_RE.match(label):
                return None, True  # invalid label on the wildcard domain -> 404
            return tenant_cache.get_tenant_by_slug(label), True

        # 2) Custom domain served directly (Prompt 05): the request's own host
        # is neither localhost/IP nor the platform family — look it up as an
        # ACTIVE custom domain. Miss -> fall through to headers (the API host
        # itself lands here in split deployments and must not 404).
        bare_host = (host or "").split(":")[0].strip().lower().rstrip(".")
        if bare_host and not _is_platform_host(bare_host):
            tenant = tenant_cache.get_tenant_by_custom_domain(bare_host)
            if tenant is not None:
                return tenant, True

        # 3) Explicit workspace header (split-domain deployments)
        slug = normalize_workspace_username(request.headers.get("X-WORKSPACE") or "")
        if slug:
            if not WORKSPACE_USERNAME_RE.match(slug):
                return None, True
            return tenant_cache.get_tenant_by_slug(slug), True

        # 4) Custom-domain host forwarded by the frontend (split deployments:
        # the SPA on hostel.everest.com calls the API on another host and
        # forwards the host it is serving). Presented-but-unknown -> 404.
        tenant_host = (request.headers.get("X-TENANT-HOST") or "").strip().lower().rstrip(".")
        if tenant_host:
            if _is_platform_host(tenant_host) or len(tenant_host) > 253:
                return None, True
            return tenant_cache.get_tenant_by_custom_domain(tenant_host.split(":")[0]), True

        # 5) Legacy Hostel ID code header
        code = (request.headers.get("X-HOSTEL-CODE") or "").strip().upper()
        if code:
            if not HOSTEL_CODE_RE.match(code):
                return None, True
            return tenant_cache.get_tenant_by_code(code), True

        # 6) Legacy raw-id header
        hostel_id = (request.headers.get("X-HOSTEL-ID") or "").strip()
        if hostel_id:
            return tenant_cache.get_tenant_by_id(hostel_id), True

        return None, False

    @staticmethod
    def _presented_slug(request):
        """The workspace *slug* this request presented (subdomain or
        X-Workspace header), or None for code/id identifiers."""
        try:
            host = request.get_host()
        except Exception:
            host = request.META.get("HTTP_HOST", "")
        label = extract_workspace_subdomain(host)
        if label is not None:
            return normalize_workspace_username(label)
        header = normalize_workspace_username(request.headers.get("X-WORKSPACE") or "")
        return header or None

    def _alias_redirect(self, request):
        """A 301 to the workspace's current URL when the presented slug is a
        retired username (rename alias); None otherwise."""
        slug = self._presented_slug(request)
        if not slug or not WORKSPACE_USERNAME_RE.match(slug):
            return None
        hostel = tenant_cache.get_alias_hostel(slug)
        if hostel is None or hostel.is_deleted:
            return None
        path = request.get_full_path()
        response = HttpResponsePermanentRedirect(f"{hostel.workspace_url}{path}")
        # Machine-readable hint for API/SSR clients that don't auto-follow.
        response["X-Workspace-Moved-To"] = hostel.slug or ""
        return response

    @staticmethod
    def _status_gate(tenant):
        """A JsonResponse when the workspace must not serve requests, else None."""
        if tenant.is_deleted or tenant.status == WorkspaceStatus.ARCHIVED:
            return _json_error(404, "Workspace not found.", "workspace_not_found")
        if tenant.status == WorkspaceStatus.SUSPENDED:
            return _json_error(
                403, "This workspace is suspended. Contact support.", "workspace_suspended"
            )
        if tenant.status == WorkspaceStatus.EXPIRED:
            return _json_error(
                403, "This workspace's subscription has expired.", "workspace_expired"
            )
        if tenant.status == WorkspaceStatus.PENDING:
            return _json_error(
                403, "This workspace is not ready yet.", "workspace_pending"
            )
        if not tenant.is_active:
            return _json_error(403, "This workspace is disabled.", "workspace_inactive")
        return None
