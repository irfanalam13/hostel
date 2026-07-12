"""Tests for PWA analytics ingestion + reporting."""
import pytest

from apps.analytics.models import AnalyticsEvent, Browser, DeviceType
from apps.analytics.services import build_report, parse_user_agent

pytestmark = pytest.mark.django_db

COLLECT = "/api/analytics/collect/"
REPORT = "/api/analytics/report/"

CHROME_ANDROID = (
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0 Mobile Safari/537.36"
)
SAFARI_MAC = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) "
    "Version/17.0 Safari/605.1.15"
)


# --------------------------------------------------------------------------- #
# User-Agent parsing
# --------------------------------------------------------------------------- #
def test_parse_user_agent_chrome_android():
    device, browser, platform = parse_user_agent(CHROME_ANDROID)
    assert device == DeviceType.MOBILE
    assert browser == Browser.CHROME
    assert platform == "Android"


def test_parse_user_agent_safari_mac():
    device, browser, platform = parse_user_agent(SAFARI_MAC)
    assert device == DeviceType.DESKTOP
    assert browser == Browser.SAFARI
    assert platform == "macOS"


def test_parse_user_agent_edge_over_chrome():
    _, browser, _ = parse_user_agent("Mozilla/5.0 ... Chrome/120 Edg/120.0")
    assert browser == Browser.EDGE


# --------------------------------------------------------------------------- #
# Ingestion
# --------------------------------------------------------------------------- #
def test_collect_creates_events_with_server_parsed_ua(auth_client, warden, hostel):
    client = auth_client(warden, hostel)
    resp = client.post(
        COLLECT,
        {
            "app_version": "1.2.3",
            "events": [
                {"event_type": "INSTALL_PROMPT"},
                {"event_type": "FEATURE_USED", "name": "payments"},
                {"event_type": "CACHE_HIT", "value": 20},
            ],
        },
        format="json",
        HTTP_USER_AGENT=CHROME_ANDROID,
    )
    assert resp.status_code == 200
    assert resp.data["accepted"] == 3
    ev = AnalyticsEvent.objects.filter(hostel=hostel, event_type="FEATURE_USED").first()
    assert ev.name == "payments"
    assert ev.device_type == DeviceType.MOBILE
    assert ev.browser == Browser.CHROME
    assert ev.app_version == "1.2.3"


def test_collect_rejects_unknown_event_type(auth_client, warden, hostel):
    client = auth_client(warden, hostel)
    resp = client.post(
        COLLECT, {"events": [{"event_type": "NONSENSE"}]}, format="json"
    )
    assert resp.status_code == 400


def test_collect_requires_auth(api):
    assert api.post(COLLECT, {"events": [{"event_type": "INSTALLED"}]}, format="json").status_code in (
        401,
        403,
    )


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def _seed(hostel, user):
    def mk(event_type, **kw):
        AnalyticsEvent.objects.create(hostel=hostel, user=user, event_type=event_type, **kw)

    mk("INSTALL_PROMPT")
    mk("INSTALL_PROMPT")
    mk("INSTALLED")  # install rate = 1/2 = 0.5
    mk("UPDATE_AVAILABLE")
    mk("UPDATE_APPLIED")  # update rate = 1/1 = 1.0
    mk("PUSH_RECEIVED")
    mk("PUSH_RECEIVED")
    mk("PUSH_OPEN")  # open rate = 1/2 = 0.5
    mk("CACHE_HIT", value=75)
    mk("CACHE_MISS", value=25)  # efficiency = 75/100 = 0.75
    mk("SYNC_SUCCESS", value=9)
    mk("SYNC_FAILURE", value=1)  # success rate = 9/10 = 0.9
    mk("OFFLINE_SESSION", value=120)
    mk("FEATURE_USED", name="payments")
    mk("FEATURE_USED", name="payments")
    mk("ERROR", name="boom")


def test_report_computes_rates(hostel, warden):
    _seed(hostel, warden)
    report = build_report(hostel, days=30)
    assert report["install"]["rate"] == 0.5
    assert report["update"]["rate"] == 1.0
    assert report["push"]["open_rate"] == 0.5
    assert report["cache"]["efficiency"] == 0.75
    assert report["sync"]["success_rate"] == 0.9
    assert report["offline_usage"]["total_seconds"] == 120
    assert report["errors"]["total"] == 1
    assert report["feature_adoption"][0]["name"] == "payments"
    assert report["feature_adoption"][0]["uses"] == 2


def test_report_endpoint_staff_only(auth_client, resident_user, hostel):
    assert auth_client(resident_user, hostel).get(REPORT).status_code == 403


def test_report_endpoint_ok_for_superuser(auth_client, superuser, warden, hostel):
    # PWA telemetry is a platform-operator surface: only super admins may read it.
    _seed(hostel, warden)
    resp = auth_client(superuser, hostel).get(REPORT, {"days": 7})
    assert resp.status_code == 200
    assert resp.data["window_days"] == 7
    assert resp.data["install"]["rate"] == 0.5


def test_report_endpoint_forbidden_for_owner(auth_client, owner, hostel):
    # Tenant owners are walled off from platform telemetry (super admin only).
    assert auth_client(owner, hostel).get(REPORT).status_code == 403


def test_report_tenant_isolated(hostel, other_hostel, warden, make_user):
    _seed(hostel, warden)
    outsider = make_user(role="OWNER", hostel=other_hostel)
    report = build_report(other_hostel, days=30)
    assert report["total_events"] == 0
    assert report["install"]["rate"] == 0.0
    assert outsider  # silence lint
