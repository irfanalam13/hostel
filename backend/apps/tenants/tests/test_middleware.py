"""Tenant resolution middleware — subdomain routing, header fallbacks,
status gating, hostname parsing and cache behaviour."""
import pytest
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from apps.tenants import services
from apps.tenants.middleware import (
    TenantResolutionMiddleware,
    extract_workspace_subdomain,
)
from apps.tenants.models import WorkspaceStatus

pytestmark = pytest.mark.django_db

BASE = override_settings(TENANT_BASE_DOMAIN="myhostel.com", ALLOWED_HOSTS=["*"])


def run(path="/api/residents/", **extra):
    """Run the middleware; returns (resolved_tenant, response)."""
    captured = {"tenant": None}

    def get_response(request):
        captured["tenant"] = request.tenant
        return HttpResponse("ok")

    mw = TenantResolutionMiddleware(get_response)
    resp = mw(RequestFactory().get(path, **extra))
    return captured["tenant"], resp


# --- Hostname parsing --------------------------------------------------------
@BASE
@pytest.mark.parametrize("host,expected", [
    ("everest.myhostel.com", "everest"),
    ("everest.myhostel.com:8000", "everest"),
    ("EVEREST.MYHOSTEL.COM", "everest"),
    ("myhostel.com", None),            # root domain
    ("www.myhostel.com", None),        # reserved -> behaves as root
    ("api.myhostel.com", None),        # reserved -> behaves as root
    ("a.b.myhostel.com", None),        # nested subdomain: not a tenant host
    ("localhost", None),
    ("127.0.0.1", None),
    ("testserver", None),
    ("othersite.com", None),           # unrelated domain (e.g. Render API host)
    ("evil-myhostel.com", None),       # suffix trick must not match
])
def test_extract_workspace_subdomain(host, expected):
    assert extract_workspace_subdomain(host) == expected


# --- Subdomain resolution ----------------------------------------------------
@BASE
def test_subdomain_resolves_tenant(make_user):
    hostel = services.provision_workspace(
        owner=make_user(role="OWNER"), hostel_name="Everest",
        workspace_username="everest",
    )
    tenant, resp = run(HTTP_HOST="everest.myhostel.com")
    assert tenant == hostel
    assert resp.status_code == 200


@BASE
def test_unknown_subdomain_is_404(db):
    tenant, resp = run(HTTP_HOST="ghost.myhostel.com")
    assert tenant is None
    assert resp.status_code == 404
    assert b"workspace_not_found" in resp.content


@BASE
def test_invalid_subdomain_label_is_404(db):
    tenant, resp = run(HTTP_HOST="bad_label.myhostel.com")
    assert resp.status_code == 404


@BASE
def test_root_domain_passes_without_tenant(db):
    tenant, resp = run(HTTP_HOST="myhostel.com")
    assert tenant is None
    assert resp.status_code == 200


@BASE
def test_reserved_subdomain_passes_without_tenant(db):
    tenant, resp = run(HTTP_HOST="www.myhostel.com")
    assert tenant is None
    assert resp.status_code == 200


# --- Header fallbacks --------------------------------------------------------
@BASE
def test_x_workspace_header_resolves(make_user):
    hostel = services.provision_workspace(
        owner=make_user(role="OWNER"), hostel_name="Everest",
        workspace_username="everest",
    )
    tenant, resp = run(HTTP_X_WORKSPACE="everest")
    assert tenant == hostel


@BASE
def test_x_workspace_unknown_is_404(db):
    _, resp = run(HTTP_X_WORKSPACE="ghost")
    assert resp.status_code == 404


def test_legacy_hostel_code_header_still_works(hostel):
    tenant, resp = run(HTTP_X_HOSTEL_CODE=hostel.code)
    assert tenant == hostel


def test_legacy_hostel_id_header_still_works(hostel):
    tenant, resp = run(HTTP_X_HOSTEL_ID=str(hostel.id))
    assert tenant == hostel


def test_garbage_hostel_id_is_404(db):
    _, resp = run(HTTP_X_HOSTEL_ID="not-a-uuid")
    assert resp.status_code == 404


@BASE
def test_subdomain_takes_priority_over_headers(make_user, hostel):
    everest = services.provision_workspace(
        owner=make_user(role="OWNER"), hostel_name="Everest",
        workspace_username="everest",
    )
    tenant, _ = run(HTTP_HOST="everest.myhostel.com", HTTP_X_HOSTEL_CODE=hostel.code)
    assert tenant == everest


# --- Status gating -----------------------------------------------------------
@BASE
@pytest.mark.parametrize("status_value,expected_http", [
    (WorkspaceStatus.TRIAL, 200),
    (WorkspaceStatus.ACTIVE, 200),
    (WorkspaceStatus.SUSPENDED, 403),
    (WorkspaceStatus.EXPIRED, 403),
    (WorkspaceStatus.PENDING, 403),
    (WorkspaceStatus.ARCHIVED, 404),
])
def test_status_gate(make_user, status_value, expected_http):
    hostel = services.provision_workspace(
        owner=make_user(role="OWNER"), hostel_name="Everest",
        workspace_username="everest",
    )
    hostel.status = status_value
    hostel.save(update_fields=["status"])
    _, resp = run(HTTP_HOST="everest.myhostel.com")
    assert resp.status_code == expected_http


@BASE
def test_soft_deleted_workspace_is_gone(make_user):
    hostel = services.provision_workspace(
        owner=make_user(role="OWNER"), hostel_name="Everest",
        workspace_username="everest",
    )
    services.soft_delete_workspace(hostel)
    _, resp = run(HTTP_HOST="everest.myhostel.com")
    assert resp.status_code == 404


# --- Exemptions --------------------------------------------------------------
def test_health_checks_skip_resolution(db):
    _, resp = run(path="/health/", HTTP_X_HOSTEL_CODE="HTL-NOPE9999")
    assert resp.status_code == 200


def test_options_preflight_skips_resolution(db):
    mw = TenantResolutionMiddleware(lambda r: HttpResponse("ok"))
    resp = mw(RequestFactory().options("/api/residents/", HTTP_X_WORKSPACE="ghost"))
    assert resp.status_code == 200


# --- Caching -----------------------------------------------------------------
@BASE
def test_tenant_lookup_is_cached(make_user, django_assert_num_queries):
    services.provision_workspace(
        owner=make_user(role="OWNER"), hostel_name="Everest",
        workspace_username="everest",
    )
    run(HTTP_HOST="everest.myhostel.com")  # warm the cache
    with django_assert_num_queries(0):
        tenant, resp = run(HTTP_HOST="everest.myhostel.com")
    assert tenant is not None and tenant.slug == "everest"


@BASE
def test_cache_invalidated_on_status_change(make_user):
    hostel = services.provision_workspace(
        owner=make_user(role="OWNER"), hostel_name="Everest",
        workspace_username="everest",
    )
    _, resp = run(HTTP_HOST="everest.myhostel.com")
    assert resp.status_code == 200
    services.suspend_workspace(hostel)
    _, resp = run(HTTP_HOST="everest.myhostel.com")
    assert resp.status_code == 403  # change visible immediately, no TTL wait


@BASE
def test_unknown_subdomains_are_negative_cached(db, django_assert_num_queries):
    run(HTTP_HOST="ghost.myhostel.com")
    with django_assert_num_queries(0):
        _, resp = run(HTTP_HOST="ghost.myhostel.com")
    assert resp.status_code == 404
