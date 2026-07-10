"""Custom domains & white-label (Prompt 05): validation, verification flow,
activation/primary, routing (direct host + X-Tenant-Host), plan limits, SSL
monitoring, white-label branding propagation, and tenant isolation.

DNS/SSL probes are monkeypatched — no test ever touches the network.
"""
from datetime import timedelta

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.domains import services
from apps.domains.models import CustomDomain
from apps.domains.validators import clean_custom_domain
from django.core.exceptions import ValidationError

pytestmark = pytest.mark.django_db

DOMAINS = "/api/domains/"
PASSWORD = "TestPass!234"

BASE = override_settings(TENANT_BASE_DOMAIN="myhostel.com", ALLOWED_HOSTS=["*"])


def _data(resp):
    body = resp.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


@pytest.fixture
def fake_dns(monkeypatch):
    """Control DNS answers per test: fake_dns.txt / fake_dns.cname."""
    class _Fake:
        txt: list[str] = []
        cname: list[str] = []

    fake = _Fake()

    def lookup(record_type, name):
        return list(fake.txt) if record_type == "TXT" else list(fake.cname)

    monkeypatch.setattr(services, "dns_lookup", lookup)
    return fake


@pytest.fixture
def fake_ssl(monkeypatch):
    class _Fake:
        expires = timezone.now() + timedelta(days=80)

    fake = _Fake()
    monkeypatch.setattr(services, "ssl_probe", lambda domain: fake.expires)
    return fake


def _connect_and_activate(hostel, domain, fake_dns, actor=None):
    record = services.add_domain(hostel, domain, actor=actor)
    fake_dns.txt = [record.verification_token]
    services.verify_domain(record, actor=actor)
    return services.activate_domain(record, actor=actor)


# --- Validation -----------------------------------------------------------------
@pytest.mark.parametrize("value", [
    "everesthostel.com", "hostel.everest.com", "portal.everest.com",
    "erp.everesthostel.edu.np", "a-b.c-d.io",
])
def test_valid_domains(value):
    assert clean_custom_domain(f"  {value.upper()}  ") == value


@override_settings(TENANT_BASE_DOMAIN="myhostel.com")
@pytest.mark.parametrize("value,code", [
    ("", "required"),
    ("https://everest.com", "invalid"),
    ("everest.com/path", "invalid"),
    ("*.everest.com", "wildcard"),
    ("no-dots", "invalid"),
    ("-bad.everest.com", "invalid"),
    ("192.168.1.1", "invalid"),
    ("myhostel.com", "platform_domain"),
    ("everest.myhostel.com", "platform_domain"),
])
def test_invalid_domains(value, code):
    with pytest.raises(ValidationError) as exc:
        clean_custom_domain(value)
    assert exc.value.code == code


def test_duplicate_domain_rejected_across_tenants(hostel, other_hostel):
    services.add_domain(hostel, "hostel.everest.com")
    with pytest.raises(ValidationError):
        services.add_domain(other_hostel, "hostel.everest.com")


# --- Plan gating -----------------------------------------------------------------
@override_settings(CUSTOM_DOMAIN_LIMITS={"free": 0, "basic": 1, "enterprise": 3, "default": 1})
def test_plan_limits_are_configurable(hostel, other_hostel):
    hostel.plan_name = "free"
    hostel.save(update_fields=["plan_name"])
    with pytest.raises(ValidationError) as exc:
        services.add_domain(hostel, "blocked.everest.com")
    assert "not included in your plan" in str(exc.value)

    other_hostel.plan_name = "enterprise"
    other_hostel.save(update_fields=["plan_name"])
    for i in range(3):
        services.add_domain(other_hostel, f"site{i}.everest.com")
    with pytest.raises(ValidationError):
        services.add_domain(other_hostel, "site3.everest.com")


# --- Verification flow --------------------------------------------------------------
def test_verification_via_txt_and_retry(fake_dns, hostel):
    record = services.add_domain(hostel, "hostel.everest.com")
    assert record.status == CustomDomain.Status.PENDING
    assert record.txt_record["host"] == "_hostel-verify.hostel.everest.com"

    # DNS not propagated yet → failed but retryable, with a friendly message.
    services.verify_domain(record)
    record.refresh_from_db()
    assert record.status == CustomDomain.Status.FAILED
    assert "propagate" in record.last_error

    # Owner adds the TXT record → verification succeeds on retry.
    fake_dns.txt = [record.verification_token]
    services.verify_domain(record)
    record.refresh_from_db()
    assert record.status == CustomDomain.Status.VERIFIED
    assert record.verification_method == "txt"
    assert record.verified_at is not None


@override_settings(TENANT_BASE_DOMAIN="myhostel.com")
def test_verification_via_cname(fake_dns, hostel):
    record = services.add_domain(hostel, "portal.everest.com")
    fake_dns.cname = [f"{hostel.slug}.myhostel.com"]
    services.verify_domain(record)
    record.refresh_from_db()
    assert record.status == CustomDomain.Status.VERIFIED
    assert record.verification_method == "cname"


def test_activation_requires_verification(fake_dns, hostel):
    record = services.add_domain(hostel, "hostel.everest.com")
    with pytest.raises(ValidationError):
        services.activate_domain(record)


# --- Activation, primary, routing ------------------------------------------------------
@BASE
def test_active_domain_routes_to_tenant(api, fake_dns, fake_ssl, hostel):
    _connect_and_activate(hostel, "hostel.everest.com", fake_dns)

    # Direct host routing: the custom domain resolves the tenant pre-auth.
    resp = api.get("/api/website/public/", HTTP_HOST="hostel.everest.com")
    assert resp.status_code == 200, resp.content
    assert _data(resp)["workspace"]["username"] == hostel.slug
    # The canonical public URL is now the custom domain.
    assert _data(resp)["workspace"]["public_url"] == "https://hostel.everest.com"

    # Split-topology bridge: the SPA forwards the host it serves.
    resp = api.get("/api/website/public/", HTTP_X_TENANT_HOST="hostel.everest.com")
    assert resp.status_code == 200
    assert _data(resp)["workspace"]["username"] == hostel.slug


@BASE
def test_login_works_identically_on_custom_domain(api, fake_dns, fake_ssl, make_user, hostel):
    """Same tenant, same account, from both the workspace URL and the custom
    domain — no duplicate accounts or sessions."""
    user = make_user(role="WARDEN", hostel=hostel, password=PASSWORD)
    _connect_and_activate(hostel, "hostel.everest.com", fake_dns)

    via_workspace = api.post("/api/auth/login/", {"username": user.username, "password": PASSWORD},
                             HTTP_X_WORKSPACE=hostel.slug)
    from rest_framework.test import APIClient

    via_domain = APIClient().post("/api/auth/login/",
                                  {"username": user.username, "password": PASSWORD},
                                  HTTP_HOST="hostel.everest.com")
    assert via_workspace.status_code == via_domain.status_code == 200
    assert via_workspace.data["user"]["id"] == via_domain.data["user"]["id"]
    assert via_domain.data["workspace"]["username"] == hostel.slug


@BASE
def test_inactive_and_disabled_domains_do_not_route(api, fake_dns, fake_ssl, hostel):
    record = services.add_domain(hostel, "hostel.everest.com")
    # Pending domain: host resolves no tenant → public endpoint has no context.
    assert api.get("/api/website/public/", HTTP_HOST="hostel.everest.com").status_code == 404

    fake_dns.txt = [record.verification_token]
    services.verify_domain(record)
    services.activate_domain(record)
    assert api.get("/api/website/public/", HTTP_HOST="hostel.everest.com").status_code == 200

    services.disable_domain(record)
    assert api.get("/api/website/public/", HTTP_HOST="hostel.everest.com").status_code == 404


@BASE
def test_domain_maps_to_exactly_one_tenant(api, fake_dns, fake_ssl, hostel, other_hostel):
    _connect_and_activate(hostel, "hostel.everest.com", fake_dns)
    resp = api.get("/api/website/public/", HTTP_HOST="hostel.everest.com")
    assert _data(resp)["workspace"]["username"] == hostel.slug
    assert _data(resp)["workspace"]["username"] != other_hostel.slug


def test_primary_switch(fake_dns, fake_ssl, hostel):
    with override_settings(CUSTOM_DOMAIN_LIMITS={"default": 2}):
        first = _connect_and_activate(hostel, "one.everest.com", fake_dns)
        second = _connect_and_activate(hostel, "two.everest.com", fake_dns)
    first.refresh_from_db()
    second.refresh_from_db()
    # Activating the second (make_primary default) moved primary over.
    assert second.is_primary and not first.is_primary
    services.set_primary_domain(first)
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.is_primary and not second.is_primary
    assert services.public_url_for(hostel) == "https://one.everest.com"


# --- SSL monitoring ---------------------------------------------------------------------
def test_ssl_status_transitions(fake_dns, fake_ssl, hostel):
    record = _connect_and_activate(hostel, "hostel.everest.com", fake_dns)
    record.refresh_from_db()
    assert record.ssl_status == CustomDomain.SslStatus.ACTIVE

    fake_ssl.expires = timezone.now() + timedelta(days=5)
    services.check_ssl(record)
    assert record.ssl_status == CustomDomain.SslStatus.EXPIRING

    fake_ssl.expires = timezone.now() - timedelta(days=1)
    services.check_ssl(record)
    assert record.ssl_status == CustomDomain.SslStatus.EXPIRED


def test_revalidation_task_flags_problems(fake_dns, fake_ssl, hostel):
    from apps.auditlog.models import AuditEvent
    from apps.domains.tasks import revalidate_custom_domains

    record = _connect_and_activate(hostel, "hostel.everest.com", fake_dns)
    fake_dns.txt = []  # records removed after activation
    fake_ssl.expires = timezone.now() + timedelta(days=3)  # expiring cert

    result = revalidate_custom_domains()
    assert result["checked"] == 1 and result["issues"] == 1
    warning = AuditEvent.objects.filter(entity_type="custom_domain",
                                        message__icontains="health warning").first()
    assert warning is not None
    assert "verification records missing" in warning.message
    # Never auto-deactivated by a DNS blip.
    record.refresh_from_db()
    assert record.status == CustomDomain.Status.ACTIVE


# --- API ------------------------------------------------------------------------------
def test_domain_api_flow(auth_client, make_user, fake_dns, fake_ssl, hostel):
    owner = make_user(role="OWNER", hostel=hostel, password=PASSWORD)
    client = auth_client(owner, hostel)

    resp = client.post(DOMAINS, {"domain": "Hostel.Everest.COM"}, format="json")
    assert resp.status_code == 201, resp.content
    created = _data(resp)
    assert created["domain"] == "hostel.everest.com"
    assert created["records"]["txt"]["host"] == "_hostel-verify.hostel.everest.com"

    domain_id = created["id"]
    fake_dns.txt = [created["records"]["txt"]["value"]]
    assert _data(client.post(f"{DOMAINS}{domain_id}/verify/"))["status"] == "verified"
    activated = _data(client.post(f"{DOMAINS}{domain_id}/activate/"))
    assert activated["status"] == "active" and activated["is_primary"] is True

    listing = _data(client.get(DOMAINS))
    assert listing["public_url"] == "https://hostel.everest.com"
    assert len(listing["domains"]) == 1

    assert client.delete(f"{DOMAINS}{domain_id}/").status_code == 204


def test_domain_api_permissions_and_isolation(auth_client, make_user, fake_dns,
                                              hostel, other_hostel):
    staff = make_user(role="STAFF", hostel=hostel)
    assert auth_client(staff, hostel).get(DOMAINS).status_code == 403

    make_user(role="OWNER", hostel=hostel)
    record = services.add_domain(hostel, "hostel.everest.com")
    owner_b = make_user(role="OWNER", hostel=other_hostel)
    # B cannot see or verify A's domain.
    assert _data(auth_client(owner_b, other_hostel).get(DOMAINS))["domains"] == []
    assert auth_client(owner_b, other_hostel).post(
        f"{DOMAINS}{record.id}/verify/").status_code == 400


# --- White-label branding -----------------------------------------------------------------
def test_white_label_propagates_to_login_branding(api, auth_client, make_user, hostel):
    owner = make_user(role="OWNER", hostel=hostel)
    auth_client(owner, hostel).patch(
        "/api/tenants/manage/settings/white_label/",
        {"enabled": True, "platform_name": "Everest OS", "browser_title": "Everest OS Portal",
         "hide_platform_branding": True},
        format="json",
    )
    data = _data(api.get("/api/tenants/workspaces/public/", HTTP_X_WORKSPACE=hostel.slug))
    assert data["white_label"]["platform_name"] == "Everest OS"
    assert data["white_label"]["browser_title"] == "Everest OS Portal"
    assert data["white_label"]["hide_platform_branding"] is True


def test_white_label_in_public_site_payload(api, hostel):
    data = _data(api.get("/api/website/public/", HTTP_X_WORKSPACE=hostel.slug))
    # Defaults: hostel name is the natural platform name.
    assert data["white_label"]["platform_name"] == hostel.name


def test_email_and_pdf_branding_helpers(fake_dns, fake_ssl, auth_client, make_user, hostel):
    from apps.tenants.branding import email_branding, pdf_branding

    owner = make_user(role="OWNER", hostel=hostel)
    auth_client(owner, hostel).patch(
        "/api/tenants/manage/settings/white_label/",
        {"platform_name": "Everest OS", "email_sender_name": "Everest Hostel Team"},
        format="json",
    )
    _connect_and_activate(hostel, "hostel.everest.com", fake_dns)
    hostel.refresh_from_db()

    email = email_branding(hostel)
    assert email["sender_name"] == "Everest Hostel Team"
    assert email["from_email"].startswith("Everest Hostel Team <")
    assert email["site_url"] == "https://hostel.everest.com"  # custom domain, not the platform's

    pdf = pdf_branding(hostel)
    assert pdf["name"] == "Everest OS"
    assert pdf["primary_color"].startswith("#")
    assert "hostel.everest.com" in pdf["footer"]