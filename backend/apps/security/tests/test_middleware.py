"""EdgeGuard + TenantRateLimit middleware behaviour (unit level, memory
backend, no Redis)."""
import json
from types import SimpleNamespace

from django.http import HttpResponse
from django.test import RequestFactory

from apps.security.middleware import EdgeGuardMiddleware, TenantRateLimitMiddleware

rf = RequestFactory()


def edge():
    return EdgeGuardMiddleware(lambda request: HttpResponse("ok"))


def body(response) -> dict:
    return json.loads(response.content)


TIGHT_IP_LIMITS = {
    "rate_limits": {
        "ip_global": {"enabled": True, "algorithm": "sliding_window",
                      "limit": 2, "window_seconds": 60},
        "ip_burst": {"enabled": False},
        "tenant_global": {"enabled": True, "algorithm": "sliding_window",
                          "limit": 2, "window_seconds": 60},
    },
}


class TestEdgeGuardRateLimiting:
    def test_over_limit_returns_429_envelope(self, install_config):
        install_config(TIGHT_IP_LIMITS)
        middleware = edge()
        for _ in range(2):
            assert middleware(rf.get("/api/x/", REMOTE_ADDR="203.0.113.9")).status_code == 200
        response = middleware(rf.get("/api/x/", REMOTE_ADDR="203.0.113.9"))
        assert response.status_code == 429
        payload = body(response)
        assert payload["success"] is False
        assert payload["meta"]["code"] == "rate_limited"
        assert response["Retry-After"]
        assert response["X-RateLimit-Remaining"] == "0"

    def test_limits_are_per_ip(self, install_config):
        install_config(TIGHT_IP_LIMITS)
        middleware = edge()
        for _ in range(2):
            middleware(rf.get("/api/x/", REMOTE_ADDR="203.0.113.9"))
        assert middleware(rf.get("/api/x/", REMOTE_ADDR="203.0.113.10")).status_code == 200

    def test_monitor_mode_never_blocks(self, install_config):
        install_config({**TIGHT_IP_LIMITS, "mode": "monitor"})
        middleware = edge()
        for _ in range(5):
            assert middleware(rf.get("/api/x/", REMOTE_ADDR="203.0.113.9")).status_code == 200

    def test_rate_headers_on_allowed_api_responses(self, install_config):
        install_config(TIGHT_IP_LIMITS)
        response = edge()(rf.get("/api/x/", REMOTE_ADDR="203.0.113.9"))
        assert response.status_code == 200
        assert response["X-RateLimit-Limit"] == "2"

    def test_exempt_paths_skip_everything(self, install_config):
        install_config({**TIGHT_IP_LIMITS,
                        "rate_limits": {**TIGHT_IP_LIMITS["rate_limits"],
                                        "ip_global": {"enabled": True, "limit": 0,
                                                      "window_seconds": 60}}})
        assert edge()(rf.get("/health/", REMOTE_ADDR="203.0.113.9")).status_code == 200

    def test_disabled_layer_is_a_passthrough(self, install_config, settings):
        settings.SECURITY_ENABLED = False
        install_config(TIGHT_IP_LIMITS)
        middleware = edge()
        for _ in range(5):
            assert middleware(rf.get("/api/x/", REMOTE_ADDR="203.0.113.9")).status_code == 200


class TestEdgeGuardWafAndBots:
    def test_waf_enforce_blocks_injection(self, install_config):
        install_config({"waf": {"mode": "enforce"}})
        response = edge()(rf.get("/api/x/?q=1%20UNION%20SELECT%20a%20FROM%20b",
                                 REMOTE_ADDR="203.0.113.9"))
        assert response.status_code == 403
        assert body(response)["meta"]["code"] == "request_blocked"

    def test_waf_monitor_logs_but_allows(self, install_config):
        install_config({"waf": {"mode": "monitor"}})
        response = edge()(rf.get("/api/x/?q=1%20UNION%20SELECT%20a%20FROM%20b",
                                 REMOTE_ADDR="203.0.113.9"))
        assert response.status_code == 200

    def test_attack_tool_user_agent_blocked_in_enforce(self, install_config):
        install_config({"bots": {"mode": "enforce"}})
        response = edge()(rf.get("/api/x/", REMOTE_ADDR="203.0.113.9",
                                 HTTP_USER_AGENT="sqlmap/1.7"))
        assert response.status_code == 403
        assert body(response)["meta"]["code"] == "bot_blocked"

    def test_browser_user_agent_passes(self, install_config):
        install_config({"bots": {"mode": "enforce"}})
        response = edge()(rf.get("/api/x/", REMOTE_ADDR="203.0.113.9",
                                 HTTP_USER_AGENT="Mozilla/5.0 Chrome/126"))
        assert response.status_code == 200


class TestEdgeGuardIPRules:
    def test_deny_rule_blocks_even_in_monitor_mode(self, install_config):
        install_config({"mode": "monitor"},
                       ip_rules=[("203.0.113.0/24", "deny", None, 1)])
        response = edge()(rf.get("/api/x/", REMOTE_ADDR="203.0.113.9"))
        assert response.status_code == 403

    def test_trust_rule_bypasses_rate_limits(self, install_config):
        install_config(TIGHT_IP_LIMITS, ip_rules=[("203.0.113.9", "trust", None, 1)])
        middleware = edge()
        for _ in range(5):
            assert middleware(rf.get("/api/x/", REMOTE_ADDR="203.0.113.9")).status_code == 200

    def test_allow_rule_bypasses_limits_but_not_waf(self, install_config):
        install_config({**TIGHT_IP_LIMITS, "waf": {"mode": "enforce"}},
                       ip_rules=[("203.0.113.9", "allow", None, 1)])
        middleware = edge()
        for _ in range(5):
            assert middleware(rf.get("/api/x/", REMOTE_ADDR="203.0.113.9")).status_code == 200
        response = middleware(rf.get("/api/x/?q=<script>alert(1)</script>",
                                     REMOTE_ADDR="203.0.113.9"))
        assert response.status_code == 403


class TestTenantRateLimit:
    @staticmethod
    def _request(tenant):
        request = rf.get("/api/residents/", REMOTE_ADDR="203.0.113.9")
        request.tenant = tenant
        return request

    def test_tenant_budget_shared_and_isolated(self, install_config):
        install_config(TIGHT_IP_LIMITS)
        middleware = TenantRateLimitMiddleware(lambda request: HttpResponse("ok"))
        tenant_a = SimpleNamespace(pk=1, plan_name="free", slug="a")
        tenant_b = SimpleNamespace(pk=2, plan_name="free", slug="b")

        for _ in range(2):
            assert middleware(self._request(tenant_a)).status_code == 200
        blocked = middleware(self._request(tenant_a))
        assert blocked.status_code == 429
        assert body(blocked)["meta"]["code"] == "tenant_rate_limited"
        # Workspace isolation: tenant B is unaffected by tenant A's flood.
        assert middleware(self._request(tenant_b)).status_code == 200

    def test_plan_multiplier_raises_the_budget(self, install_config):
        install_config({**TIGHT_IP_LIMITS,
                        "plan_multipliers": {"enterprise": 3.0, "default": 1.0}})
        middleware = TenantRateLimitMiddleware(lambda request: HttpResponse("ok"))
        tenant = SimpleNamespace(pk=3, plan_name="enterprise", slug="big")
        for _ in range(6):  # 2 * 3.0 multiplier
            assert middleware(self._request(tenant)).status_code == 200
        assert middleware(self._request(tenant)).status_code == 429

    def test_no_tenant_is_a_passthrough(self, install_config):
        install_config(TIGHT_IP_LIMITS)
        middleware = TenantRateLimitMiddleware(lambda request: HttpResponse("ok"))
        request = rf.get("/api/x/", REMOTE_ADDR="203.0.113.9")
        request.tenant = None
        for _ in range(5):
            assert middleware(request).status_code == 200
