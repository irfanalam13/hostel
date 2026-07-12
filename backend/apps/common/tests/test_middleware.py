"""Middleware: tenant resolution, security headers, DR-mode gating.

Covered (Phase 10 §2 HasHostelContext validation + infra behaviour).
Tenant resolution now lives in apps.tenants.middleware (workspace/subdomain
architecture) — the legacy X-HOSTEL-CODE header behaviour is asserted here,
the full subdomain/status matrix in apps/tenants/tests/test_middleware.py."""
import pytest
from django.test import RequestFactory

from apps.common.middleware import SecurityHeadersMiddleware
from apps.tenants.middleware import TenantResolutionMiddleware

pytestmark = pytest.mark.django_db


def _resolve(**headers):
    """Run TenantResolutionMiddleware and return (request.hostel, response)."""
    captured = {"hostel": None}

    def get_response(request):
        captured["hostel"] = request.hostel
        from django.http import HttpResponse

        return HttpResponse("ok")

    mw = TenantResolutionMiddleware(get_response)
    req = RequestFactory().get("/api/residents/", **headers)
    resp = mw(req)
    return captured["hostel"], resp


# --- Tenant resolution (legacy X-HOSTEL-CODE path) ---------------------------
def test_valid_code_resolves_hostel(hostel):
    resolved, resp = _resolve(HTTP_X_HOSTEL_CODE=hostel.code)
    assert resolved == hostel
    assert resp.status_code == 200


def test_unknown_code_is_blocked(db):
    # A presented-but-unresolvable identifier must terminate the request.
    resolved, resp = _resolve(HTTP_X_HOSTEL_CODE="HTL-NOPE9999")
    assert resolved is None
    assert resp.status_code == 404


def test_malformed_code_is_rejected_before_db(db):
    # Spaces / overly long values fail the regex and never hit the DB.
    assert _resolve(HTTP_X_HOSTEL_CODE="bad code!")[1].status_code == 404
    assert _resolve(HTTP_X_HOSTEL_CODE="x" * 60)[1].status_code == 404


def test_inactive_hostel_is_blocked(hostel):
    hostel.is_active = False
    hostel.save(update_fields=["is_active"])
    resolved, resp = _resolve(HTTP_X_HOSTEL_CODE=hostel.code)
    assert resolved is None
    assert resp.status_code == 403


def test_no_code_resolves_to_none(db):
    resolved, resp = _resolve()
    assert resolved is None
    assert resp.status_code == 200


# --- SecurityHeadersMiddleware ---------------------------------------------
def test_security_headers_present():
    from django.http import HttpResponse

    mw = SecurityHeadersMiddleware(lambda r: HttpResponse("ok"))
    resp = mw(RequestFactory().get("/api/anything/"))
    assert resp["Referrer-Policy"]
    assert "geolocation=()" in resp["Permissions-Policy"]


# --- DRModeMiddleware (maintenance / emergency) ----------------------------
def test_maintenance_mode_blocks_writes_allows_reads(api, auth_client, make_user, hostel):
    from apps.backups.models import DRMode, DRState

    user = make_user(role="WARDEN", hostel=hostel)
    client = auth_client(user, hostel)
    DRState.set_mode(DRMode.MAINTENANCE, reason="upgrade")

    # Reads pass...
    assert client.get("/api/residents/").status_code == 200
    # ...writes are gated with 503.
    assert client.post("/api/residents/", {"full_name": "X"}).status_code == 503


def test_emergency_mode_locks_everything_but_auth(api, auth_client, make_user, hostel):
    from apps.backups.models import DRMode, DRState

    user = make_user(role="WARDEN", hostel=hostel)
    client = auth_client(user, hostel)
    DRState.set_mode(DRMode.EMERGENCY, reason="restore in progress")

    assert client.get("/api/residents/").status_code == 503
    # Auth endpoints stay reachable so an admin can log in to drive recovery.
    assert api.post("/api/auth/login/", {"hostel_id": "HTL-NOPE9999", "username": "x", "password": "y"}).status_code != 503
