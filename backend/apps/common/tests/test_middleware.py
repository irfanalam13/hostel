"""Middleware: tenant resolution, security headers, DR-mode gating.

Covered (Phase 10 §2 HasHostelContext validation + infra behaviour)."""
import pytest
from django.test import RequestFactory

from apps.common.middleware import (
    HostelResolveMiddleware,
    SecurityHeadersMiddleware,
)

pytestmark = pytest.mark.django_db


def _resolve(**headers):
    """Run HostelResolveMiddleware over a request and return request.hostel."""
    captured = {}

    def get_response(request):
        captured["hostel"] = request.hostel
        from django.http import HttpResponse

        return HttpResponse("ok")

    mw = HostelResolveMiddleware(get_response)
    req = RequestFactory().get("/api/residents/", **headers)
    mw(req)
    return captured["hostel"]


# --- HostelResolveMiddleware -----------------------------------------------
def test_valid_code_resolves_hostel(hostel):
    assert _resolve(HTTP_X_HOSTEL_CODE=hostel.code) == hostel


def test_unknown_code_resolves_to_none(db):
    assert _resolve(HTTP_X_HOSTEL_CODE="HTL-NOPE9999") is None


def test_malformed_code_is_rejected_before_db(db):
    # Spaces / overly long values fail the regex and never hit the DB.
    assert _resolve(HTTP_X_HOSTEL_CODE="bad code!") is None
    assert _resolve(HTTP_X_HOSTEL_CODE="x" * 60) is None


def test_inactive_hostel_does_not_resolve(hostel):
    hostel.is_active = False
    hostel.save(update_fields=["is_active"])
    assert _resolve(HTTP_X_HOSTEL_CODE=hostel.code) is None


def test_no_code_resolves_to_none(db):
    assert _resolve() is None


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
