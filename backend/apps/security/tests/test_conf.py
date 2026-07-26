"""Config layering, coercion, hot reload and IP-rule matching."""
import ipaddress

import pytest

from apps.security import conf
from apps.security.conf import _coerce, _deep_merge, _set_path

from .conftest import make_config


class TestMergingPrimitives:
    def test_deep_merge_nested_override(self):
        merged = _deep_merge({"a": {"b": 1, "c": 2}, "d": 3}, {"a": {"b": 9}})
        assert merged == {"a": {"b": 9, "c": 2}, "d": 3}

    def test_deep_merge_does_not_mutate_base(self):
        base = {"a": {"b": 1}}
        _deep_merge(base, {"a": {"b": 2}})
        assert base["a"]["b"] == 1

    def test_set_path_creates_intermediate_nodes(self):
        data = {}
        _set_path(data, "waf.rules.xss", False)
        assert data == {"waf": {"rules": {"xss": False}}}

    @pytest.mark.parametrize("raw,expected", [
        ("true", True), ("False", False), ("42", 42), ("1.5", 1.5),
        ("a,b,c", ["a", "b", "c"]), ("enforce", "enforce"),
        ('["x","y"]', ["x", "y"]),
    ])
    def test_coerce(self, raw, expected):
        assert _coerce(raw) == expected


class TestEnvOverrides:
    def test_env_var_reaches_resolved_config(self, monkeypatch):
        monkeypatch.setenv("SECURITY_RATE_IP_LIMIT", "42")
        monkeypatch.setenv("SECURITY_WAF_MODE", "monitor")
        conf.reset_for_tests()
        config = conf.get_config()
        assert config.get("rate_limits.ip_global.limit") == 42
        assert config.get("waf.mode") == "monitor"


@pytest.mark.django_db
class TestDatabaseLayerHotReload:
    def test_setting_row_overrides_and_hot_reloads(self):
        from apps.security.models import SecuritySetting

        before = conf.get_config()
        assert before.get("bots.blocked_action") == "block"

        # Saving bumps the generation (signal) -> next get_config() rebuilds.
        SecuritySetting.objects.create(key="bots.blocked_action", value="log")
        after = conf.get_config()
        assert after.get("bots.blocked_action") == "log"
        assert after.generation != before.generation

    def test_inactive_setting_is_ignored(self):
        from apps.security.models import SecuritySetting

        SecuritySetting.objects.create(key="waf.enabled", value=False, active=False)
        assert conf.get_config().get("waf.enabled") is True

    def test_ip_rule_rows_load_and_expire(self):
        from datetime import timedelta

        from django.utils import timezone

        from apps.security.models import IPRule

        IPRule.objects.create(cidr="203.0.113.0/24", action="deny")
        IPRule.objects.create(cidr="198.51.100.1", action="allow",
                              expires_at=timezone.now() - timedelta(minutes=1))
        config = conf.get_config()
        assert config.match_ip_rule(ipaddress.ip_address("203.0.113.7")) is not None
        # Expired rule filtered out at load time.
        assert config.match_ip_rule(ipaddress.ip_address("198.51.100.1")) is None


class TestSnapshotLookups:
    def test_ip_rule_precedence_trust_beats_deny(self):
        config = make_config(ip_rules=[
            ("203.0.113.0/24", "deny", None, 1),
            ("203.0.113.7", "trust", None, 2),
        ])
        action, rule_id = config.match_ip_rule(ipaddress.ip_address("203.0.113.7"))
        assert action == "trust"
        action, _ = config.match_ip_rule(ipaddress.ip_address("203.0.113.8"))
        assert action == "deny"

    def test_tenant_scoped_rule_only_hits_its_tenant(self):
        config = make_config(ip_rules=[("203.0.113.0/24", "deny", 42, 1)])
        assert config.match_ip_rule(ipaddress.ip_address("203.0.113.7"), 42) is not None
        assert config.match_ip_rule(ipaddress.ip_address("203.0.113.7"), 7) is None
        assert config.match_ip_rule(ipaddress.ip_address("203.0.113.7")) is None

    def test_plan_multiplier_with_fallback(self):
        config = make_config({"plan_multipliers": {"pro": 2.5, "default": 1.0}})
        assert config.plan_multiplier("PRO") == 2.5
        assert config.plan_multiplier("unknown") == 1.0
        assert config.plan_multiplier("") == 1.0

    def test_exempt_paths(self):
        config = make_config()
        assert config.is_exempt_path("/health/") is True
        assert config.is_exempt_path("/api/residents/") is False

    def test_monitor_mode_disables_section_enforcement(self):
        config = make_config({"mode": "monitor", "waf": {"mode": "enforce"}})
        assert config.section_enforces("waf") is False
        config = make_config({"mode": "enforce", "waf": {"mode": "enforce"}})
        assert config.section_enforces("waf") is True
