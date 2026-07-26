"""Super-Admin security ops API (Prompt 09) — access control, feeds,
dynamic rules, kill switch. Runs through the full stack via APIClient."""
import pytest

from apps.security.models import IPRule, SecurityEvent, SecuritySetting

pytestmark = pytest.mark.django_db

BASE = "/api/platform/security"


def test_requires_platform_admin(api, auth_client, warden, hostel):
    # Anonymous -> 401/403; a tenant admin (non-superuser) -> 403.
    assert api.get(f"{BASE}/summary/").status_code in (401, 403)
    resp = auth_client(warden, hostel).get(f"{BASE}/summary/")
    assert resp.status_code == 403


def test_summary_ok_for_superuser(auth_client, superuser, hostel):
    SecurityEvent.objects.create(event_type="rate_limited", action="blocked", ip="1.1.1.1")
    resp = auth_client(superuser, hostel).get(f"{BASE}/summary/")
    assert resp.status_code == 200
    body = resp.json()["data"] if "data" in resp.json() else resp.json()
    assert "threat_level" in body
    assert "posture" in body
    assert body["posture"]["config_generation"] >= 1


def test_event_feed_filters(auth_client, superuser, hostel):
    SecurityEvent.objects.create(event_type="waf_violation", action="blocked", ip="2.2.2.2")
    SecurityEvent.objects.create(event_type="bot_detected", action="logged", ip="3.3.3.3")
    client = auth_client(superuser, hostel)
    resp = client.get(f"{BASE}/events/?event_type=waf_violation")
    assert resp.status_code == 200
    payload = resp.json().get("data", resp.json())
    assert payload["count"] == 1
    assert payload["results"][0]["ip"] == "2.2.2.2"


def test_ip_rule_lifecycle_and_hot_reload(auth_client, superuser, hostel):
    from apps.security import conf

    client = auth_client(superuser, hostel)
    gen_before = conf.get_config().generation

    created = client.post(f"{BASE}/ip-rules/",
                          {"cidr": "203.0.113.0/24", "action": "deny"}, format="json")
    assert created.status_code == 201
    assert IPRule.objects.filter(cidr="203.0.113.0/24", action="deny").exists()
    # Saving an IPRule bumps the config generation (hot reload across containers).
    assert conf.get_config().generation != gen_before

    rule_id = created.json().get("data", created.json())["id"]
    assert client.delete(f"{BASE}/ip-rules/{rule_id}/").status_code in (200, 204)
    assert not IPRule.objects.filter(id=rule_id).exists()


def test_invalid_cidr_rejected(auth_client, superuser, hostel):
    resp = auth_client(superuser, hostel).post(
        f"{BASE}/ip-rules/", {"cidr": "not-an-ip", "action": "deny"}, format="json")
    assert resp.status_code == 400


def test_dynamic_setting_editor(auth_client, superuser, hostel):
    client = auth_client(superuser, hostel)
    resp = client.post(f"{BASE}/settings/",
                       {"key": "waf.mode", "value": "monitor"}, format="json")
    assert resp.status_code == 201
    assert SecuritySetting.objects.filter(key="waf.mode").exists()


def test_kill_switch_engages_and_restores(auth_client, superuser, hostel):
    client = auth_client(superuser, hostel)
    engage = client.post(f"{BASE}/kill-switch/",
                        {"target": "rate_limiter", "engage": True,
                         "reason": "incident-123"}, format="json")
    assert engage.status_code == 200
    row = SecuritySetting.objects.get(key="kill.rate_limiter")
    assert row.value is True

    restore = client.post(f"{BASE}/kill-switch/",
                         {"target": "rate_limiter", "engage": False}, format="json")
    assert restore.status_code == 200
    assert not SecuritySetting.objects.filter(key="kill.rate_limiter").exists()


def test_kill_switch_waf_toggles_enabled(auth_client, superuser, hostel):
    client = auth_client(superuser, hostel)
    client.post(f"{BASE}/kill-switch/", {"target": "waf", "engage": True}, format="json")
    assert SecuritySetting.objects.get(key="waf.enabled").value is False
    client.post(f"{BASE}/kill-switch/", {"target": "waf", "engage": False}, format="json")
    assert SecuritySetting.objects.get(key="waf.enabled").value is True


def test_reputation_clear_requires_ip(auth_client, superuser, hostel):
    client = auth_client(superuser, hostel)
    assert client.post(f"{BASE}/reputation/clear/", {}, format="json").status_code == 400
    assert client.post(f"{BASE}/reputation/clear/",
                       {"ip": "1.2.3.4"}, format="json").status_code == 200


def test_report_json_and_csv(auth_client, superuser, hostel):
    SecurityEvent.objects.create(event_type="auth_failure", action="logged", ip="4.4.4.4")
    client = auth_client(superuser, hostel)
    assert client.get(f"{BASE}/report/?period=daily").status_code == 200
    csv_resp = client.get(f"{BASE}/report/?period=daily&fmt=csv")
    assert csv_resp.status_code == 200
    assert "text/csv" in csv_resp["Content-Type"]
