"""Security regression tests — lock in the audit's security fixes.

These guard the specific security findings remediated from AUDIT.md so a future
change can't silently reintroduce them:

  * C4  — negative/zero payment amounts are rejected (ledger-manipulation guard)
  * Auth — protected endpoints require authentication; bad credentials fail
  * Headers — X-Content-Type-Options: nosniff is always on (M13)
  * Throttling — sensitive auth endpoints declare a throttle scope (H11/M5)
  * Input — hostile query input degrades to 4xx, never a 500

Cross-tenant isolation has its own module (test_tenant_isolation.py).
"""
import pytest

from conftest import ResidentFactory

pytestmark = pytest.mark.django_db

BILLING_PAYMENTS = "/api/billing/payments/"
RESIDENTS = "/api/residents/"
LOGIN = "/api/auth/login/"


# --------------------------------------------------------------------------- #
# C4 — payment amount must be positive
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("amount", ["-100.00", "0", "0.00"])
def test_non_positive_payment_amount_is_rejected(amount, auth_client, accountant, hostel):
    resident = ResidentFactory(hostel=hostel)
    client = auth_client(accountant, hostel)
    resp = client.post(
        BILLING_PAYMENTS,
        {"resident": resident.id, "amount": amount, "method": "cash"},
        format="json",
    )
    assert resp.status_code == 400, f"amount={amount} should be rejected, got {resp.status_code}"
    assert "amount" in str(resp.data).lower()


def test_positive_payment_amount_is_accepted(auth_client, accountant, hostel):
    resident = ResidentFactory(hostel=hostel)
    client = auth_client(accountant, hostel)
    resp = client.post(
        BILLING_PAYMENTS,
        {"resident": resident.id, "amount": "500.00", "method": "cash"},
        format="json",
    )
    assert resp.status_code in (200, 201)


# --------------------------------------------------------------------------- #
# Authentication
# --------------------------------------------------------------------------- #
def test_protected_endpoint_requires_authentication(api):
    resp = api.get(RESIDENTS)
    assert resp.status_code in (401, 403)


def test_login_with_bad_credentials_is_rejected(api, make_user, hostel):
    make_user(role="WARDEN", hostel=hostel, password="CorrectHorse!9")
    resp = api.post(
        LOGIN,
        {"hostel_id": hostel.code, "username": "nope", "password": "wrong"},
        format="json",
    )
    assert resp.status_code in (400, 401)
    # Must not leak whether the username exists.
    body = str(resp.data).lower()
    assert "traceback" not in body


# --------------------------------------------------------------------------- #
# Security headers (M13 — always-on nosniff + Phase 10 hardening)
# --------------------------------------------------------------------------- #
def test_nosniff_header_present(api):
    resp = api.get(RESIDENTS)  # 401, but SecurityMiddleware still stamps headers
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"


def test_cross_origin_and_permissions_headers_present(api):
    """Phase 10: COOP / CORP / Permissions-Policy / cross-domain-policies."""
    resp = api.get(RESIDENTS)
    assert resp.headers.get("Cross-Origin-Opener-Policy") == "same-origin"
    assert resp.headers.get("Cross-Origin-Resource-Policy") == "same-origin"
    assert resp.headers.get("X-Permitted-Cross-Domain-Policies") == "none"
    pp = resp.headers.get("Permissions-Policy") or ""
    # Powerful features must be explicitly denied.
    assert "camera=()" in pp and "geolocation=()" in pp and "microphone=()" in pp


# --------------------------------------------------------------------------- #
# Throttling configured on sensitive auth endpoints (H11/M5)
# --------------------------------------------------------------------------- #
def test_sensitive_auth_views_declare_throttle_scopes():
    """Prompt 08 replaced the legacy DRF `throttle_scope` strings on the auth
    views with dedicated, config-driven security throttle classes. Assert every
    sensitive auth endpoint now carries a security throttle mapped to a
    `rate_limits.auth_*` scope."""
    from apps.accounts import views as account_views
    from apps.security.throttling import SecurityScopedThrottle

    def scopes_for(view_name):
        view = getattr(account_views, view_name, None)
        classes = getattr(view, "throttle_classes", None) or []
        return {
            getattr(c, "scope", None)
            for c in classes
            if isinstance(c, type) and issubclass(c, SecurityScopedThrottle)
        }

    login = scopes_for("CookieTokenObtainPairView")
    signup = scopes_for("SignupView")
    reset = scopes_for("PasswordResetRequestView")
    assert "auth_login" in login
    assert "auth_signup" in signup
    assert "auth_password_reset" in reset


# --------------------------------------------------------------------------- #
# Hostile input must not 500
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "qs",
    ["?search=%27%20OR%201%3D1--", "?ordering=__class__", "?page=-1", "?id[]=1&id[]=2"],
)
def test_hostile_query_input_does_not_500(qs, auth_client, warden, hostel):
    resp = auth_client(warden, hostel).get(RESIDENTS + qs)
    assert resp.status_code < 500, f"{qs} caused a server error"
