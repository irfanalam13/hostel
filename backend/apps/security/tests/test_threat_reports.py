"""Threat aggregation + security report generation (Prompt 09)."""
import pytest

from apps.security import reports, threat
from apps.security.models import SecurityEvent

pytestmark = pytest.mark.django_db


def _event(event_type, action="blocked", ip="203.0.113.1", path="/api/x/"):
    return SecurityEvent.objects.create(
        event_type=event_type, action=action, ip=ip, path=path,
    )


class TestThreatSummary:
    def test_empty_is_normal(self, install_config):
        data = threat.summary(window_hours=24)
        assert data["total_events"] == 0
        assert data["threat_level"] == "normal"

    def test_counts_and_top_ips(self, install_config):
        for _ in range(3):
            _event("rate_limited", ip="203.0.113.9")
        _event("waf_violation", ip="203.0.113.10")
        _event("bot_detected", action="logged", ip="203.0.113.10")

        data = threat.summary(window_hours=24)
        assert data["total_events"] == 5
        assert data["blocked_events"] == 4
        assert data["by_type"]["rate_limited"] == 3
        assert data["top_ips"][0]["ip"] == "203.0.113.9"
        assert data["top_ips"][0]["count"] == 3

    def test_threat_level_thresholds(self, install_config):
        # Override thresholds low so a handful of events cross "elevated".
        install_config({"threat": {"levels": {"elevated": 3, "high": 100, "critical": 1000}}})
        for _ in range(3):
            _event("rate_limited")
        assert threat.summary(window_hours=24)["threat_level"] == "elevated"

    def test_tenant_scoping(self, install_config):
        from apps.tenants.models import Hostel

        h = Hostel.objects.create(name="T1")
        SecurityEvent.objects.create(event_type="rate_limited", action="blocked",
                                     ip="1.1.1.1", tenant=h)
        _event("rate_limited", ip="2.2.2.2")  # global, no tenant
        scoped = threat.summary(window_hours=24, tenant_id=h.pk)
        assert scoped["total_events"] == 1

    def test_top_offenders_only_blocked(self, install_config):
        _event("rate_limited", action="blocked", ip="9.9.9.9")
        _event("bot_detected", action="logged", ip="8.8.8.8")
        offenders = threat.top_offenders(window_hours=24)
        ips = [o["ip"] for o in offenders]
        assert "9.9.9.9" in ips
        assert "8.8.8.8" not in ips


class TestReports:
    def test_build_has_sections_and_recommendations(self, install_config):
        for _ in range(2):
            _event("auth_failure", ip="5.5.5.5")
        report = reports.build(period="daily")
        assert report["period"] == "daily"
        assert report["window_hours"] == 24
        assert "recommendations" in report and report["recommendations"]
        assert "offenders" in report

    def test_csv_export_is_wellformed(self, install_config):
        _event("waf_violation")
        csv_text = reports.to_csv(reports.build(period="daily"))
        assert "section,key,value" in csv_text
        assert "threat_level" in csv_text

    def test_weekly_window(self, install_config):
        assert reports.build(period="weekly")["window_hours"] == 168
