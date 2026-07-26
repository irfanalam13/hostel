"""CAPTCHA decision/verify, abuse detection, replay, and the auth_guard
orchestration."""
import time

from django.test import RequestFactory, override_settings

from apps.security import abuse, auth_guard, captcha, conf, replay, reputation

from .conftest import make_config

rf = RequestFactory()


def _install(overrides=None):
    snap = make_config(overrides)
    conf._snapshot = snap
    conf._snapshot_gen = snap.generation
    conf._last_check = time.monotonic()
    return snap


# --------------------------------------------------------------------------- #
class TestCaptchaDecision:
    def test_disabled_without_secret(self, install_config, fake_redis):
        _install({"auth": {"captcha": {"enabled": True, "trigger_after_failures": 1}}})
        # No SECURITY_CAPTCHA_SECRET -> never configured -> never required.
        assert captcha.is_configured() is False
        assert captcha.is_required("1.2.3.4", failure_count=5) is False

    @override_settings(SECURITY_CAPTCHA_SECRET="s3cret")
    def test_required_after_failures(self, install_config, fake_redis):
        _install({"auth": {"captcha": {"enabled": True, "trigger_after_failures": 3}}})
        assert captcha.is_configured() is True
        assert captcha.is_required("1.2.3.4", failure_count=2) is False
        assert captcha.is_required("1.2.3.4", failure_count=3) is True

    @override_settings(SECURITY_CAPTCHA_SECRET="s3cret")
    def test_required_when_ip_suspicious(self, install_config, fake_redis):
        _install({"auth": {"captcha": {"enabled": True, "trigger_after_failures": 99,
                                       "trigger_on_reputation": "suspicious"}},
                  "reputation": {"suspicious_threshold": 5, "penalties": {"x": 5}}})
        assert captcha.is_required("7.7.7.7", failure_count=0) is False
        reputation.penalize("7.7.7.7", "x")   # score 5 -> suspicious
        assert captcha.is_required("7.7.7.7", failure_count=0) is True

    @override_settings(SECURITY_CAPTCHA_SECRET="s3cret")
    def test_verify_no_token_fails(self, install_config, fake_redis):
        _install({"auth": {"captcha": {"enabled": True}}})
        assert captcha.verify("") is False


class TestCredentialStuffing:
    def test_trips_after_distinct_identities(self, install_config, fake_redis):
        _install({"auth": {"credential_stuffing": {
            "enabled": True, "distinct_identities_threshold": 4, "window_seconds": 300}}})
        tripped = False
        for i in range(4):
            tripped = abuse.record_credential_stuffing("1.2.3.4", f"user{i}", None)
        assert tripped is True
        # Same IP is now penalised toward a reputation block.
        _, score = reputation.status("1.2.3.4")
        assert score > 0

    def test_same_identity_repeated_does_not_trip(self, install_config, fake_redis):
        _install({"auth": {"credential_stuffing": {
            "enabled": True, "distinct_identities_threshold": 4, "window_seconds": 300}}})
        tripped = False
        for _ in range(10):
            tripped = abuse.record_credential_stuffing("1.2.3.4", "same-user", None)
        assert tripped is False    # cardinality is 1, never crosses threshold


class TestEnumeration:
    def test_trips_after_distinct_targets(self, install_config, fake_redis):
        _install({"auth": {"enumeration": {
            "enabled": True, "distinct_targets_threshold": 3, "window_seconds": 300}}})
        tripped = False
        for i in range(3):
            tripped = abuse.record_enumeration("2.2.2.2", f"a{i}@x.com", None)
        assert tripped is True


class TestReplay:
    def test_first_use_ok_second_is_replay(self, install_config, fake_redis):
        assert replay.seen_before("webhook:stripe", "evt_1", ttl=60) is False
        assert replay.seen_before("webhook:stripe", "evt_1", ttl=60) is True

    def test_scopes_are_independent(self, install_config, fake_redis):
        assert replay.seen_before("a", "n", ttl=60) is False
        assert replay.seen_before("b", "n", ttl=60) is False

    def test_forget_allows_reuse(self, install_config, fake_redis):
        replay.seen_before("s", "n", ttl=60)
        replay.forget("s", "n")
        assert replay.seen_before("s", "n", ttl=60) is False

    def test_fail_open_without_redis(self, install_config):
        # No redis -> not treated as replay by default (fail open).
        assert replay.seen_before("s", "n") is False
        assert replay.seen_before("s", "n", fail_closed=True) is True


class TestAuthGuard:
    def test_gate_blocks_when_locked(self, install_config, fake_redis):
        _install({"auth": {"progressive_lockout": {
            "enabled": True, "scope": "ip", "tiers": [[2, 60]]}}})
        request = rf.post("/api/auth/login/")
        request.client_ip = "3.3.3.3"
        auth_guard.register_failure("login", request, "t:a")
        auth_guard.register_failure("login", request, "t:a")
        gate = auth_guard.check_gate("login", request, "t:a")
        assert gate.blocked is True
        assert gate.retry_after > 0

    def test_success_resets(self, install_config, fake_redis):
        _install({"auth": {"progressive_lockout": {
            "enabled": True, "scope": "ip", "tiers": [[2, 60]]}}})
        request = rf.post("/api/auth/login/")
        request.client_ip = "3.3.3.4"
        auth_guard.register_failure("login", request, "t:a")
        auth_guard.register_success("login", request, "t:a")
        assert auth_guard.check_gate("login", request, "t:a").blocked is False

    def test_monitor_mode_never_blocks(self, install_config, fake_redis):
        _install({"mode": "monitor", "auth": {"progressive_lockout": {
            "enabled": True, "scope": "ip", "tiers": [[1, 60]]}}})
        request = rf.post("/api/auth/login/")
        request.client_ip = "3.3.3.5"
        out = auth_guard.register_failure("login", request, "t:a")
        assert out.blocked is False
        assert auth_guard.check_gate("login", request, "t:a").blocked is False

    def test_make_identity_scopes_to_tenant(self, install_config):
        request = rf.post("/api/auth/login/")
        request.tenant = type("T", (), {"pk": 42})()
        assert auth_guard.make_identity(request, "Alice") == "42:alice"

    def test_disabled_layer_is_passthrough(self, install_config, fake_redis, settings):
        settings.SECURITY_ENABLED = False
        _install({"auth": {"progressive_lockout": {"tiers": [[1, 60]]}}})
        request = rf.post("/api/auth/login/")
        request.client_ip = "3.3.3.6"
        for _ in range(5):
            out = auth_guard.register_failure("login", request, "t:a")
        assert out.blocked is False
