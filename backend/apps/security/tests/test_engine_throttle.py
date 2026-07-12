"""Engine rule resolution / fail strategy + DRF throttle foundation."""
from types import SimpleNamespace

from django.test import RequestFactory

from apps.security import engine
from apps.security.locks import RedisLock
from apps.security.throttling import SecurityScopedThrottle, TenantScopedThrottle

rf = RequestFactory()


class TestEngine:
    def test_unknown_scope_allows(self, install_config):
        install_config()
        assert engine.check("nonexistent_scope", "ip:1.2.3.4").allowed is True

    def test_disabled_rule_allows(self, install_config):
        install_config({"rate_limits": {"ip_global": {"enabled": False}}})
        for _ in range(10):
            assert engine.check("ip_global", "ip:1.2.3.4").allowed is True

    def test_explicit_rule_and_scope_isolation(self, install_config):
        install_config()
        rule = {"algorithm": "sliding_window", "limit": 1, "window_seconds": 60}
        assert engine.check("custom", "a", rule=rule).allowed is True
        assert engine.check("custom", "a", rule=rule).allowed is False
        assert engine.check("custom", "b", rule=rule).allowed is True   # other identity
        assert engine.check("other", "a", rule=rule).allowed is True    # other scope

    def test_multiplier_scales_the_limit(self, install_config):
        install_config()
        rule = {"algorithm": "sliding_window", "limit": 2, "window_seconds": 60}
        for _ in range(4):
            assert engine.check("scaled", "t:1", rule=rule, multiplier=2.0).allowed is True
        assert engine.check("scaled", "t:1", rule=rule, multiplier=2.0).allowed is False

    def test_redis_required_backend_applies_fail_strategy(self, install_config):
        # backend=redis but Redis is unreachable (fixture forces None client).
        install_config({"backend": "redis", "fail_strategy": "open"})
        assert engine.check("ip_global", "ip:1.2.3.4").degraded is True
        assert engine.check("ip_global", "ip:1.2.3.4").allowed is True

        install_config({"backend": "redis", "fail_strategy": "closed"})
        decision = engine.check("ip_global", "ip:1.2.3.4")
        assert decision.allowed is False
        assert decision.meta.get("reason") == "fail_closed"


class TestThrottles:
    def _make(self, scope_name, limit=1):
        class _Throttle(SecurityScopedThrottle):
            scope = scope_name

        return _Throttle()

    def test_scoped_throttle_enforces_config_rule(self, install_config):
        install_config({"rate_limits": {"api_custom": {
            "enabled": True, "algorithm": "sliding_window",
            "limit": 1, "window_seconds": 60}}})
        throttle = self._make("api_custom")
        request = rf.get("/api/x/")
        request.client_ip = "203.0.113.9"
        assert throttle.allow_request(request, None) is True
        assert throttle.allow_request(request, None) is False
        assert throttle.wait() >= 1

    def test_monitor_mode_lets_requests_through(self, install_config):
        install_config({"mode": "monitor",
                        "rate_limits": {"api_custom": {
                            "enabled": True, "limit": 1, "window_seconds": 60}}})
        throttle = self._make("api_custom")
        request = rf.get("/api/x/")
        request.client_ip = "203.0.113.9"
        for _ in range(3):
            assert throttle.allow_request(request, None) is True

    def test_tenant_throttle_keys_by_workspace_with_plan_multiplier(self, install_config):
        install_config({"plan_multipliers": {"pro": 2.0, "default": 1.0},
                        "rate_limits": {"exports": {
                            "enabled": True, "limit": 1, "window_seconds": 60}}})

        class ExportThrottle(TenantScopedThrottle):
            scope = "exports"

        throttle = ExportThrottle()
        request = rf.get("/api/exports/")
        request.tenant = SimpleNamespace(pk=7, plan_name="pro", slug="w")
        request.client_ip = "203.0.113.9"
        assert throttle.allow_request(request, None) is True   # 1 * 2.0 = 2
        assert throttle.allow_request(request, None) is True
        assert throttle.allow_request(request, None) is False


class TestRedisLock:
    def test_lock_degrades_per_fail_strategy_without_redis(self, install_config):
        install_config({"fail_strategy": "open"})
        with RedisLock("job:1") as lock:
            assert lock.acquired is True

        install_config({"fail_strategy": "closed"})
        with RedisLock("job:2") as lock:
            assert lock.acquired is False
