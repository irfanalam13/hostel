"""Progressive lockout tiers, per-IP/identity scoping, reset."""
from apps.security import progressive

from .conftest import make_config

TIERS = {"auth": {"progressive_lockout": {
    "enabled": True, "scope": "both", "failure_window_seconds": 3600,
    "tiers": [[3, 30], [5, 120], [8, 600]],
}}}


def _install(install_config, overrides=None):
    import time

    from apps.security import conf
    from apps.security.conf import _deep_merge

    snap = make_config(_deep_merge(TIERS, overrides or {}))
    conf._snapshot = snap
    conf._snapshot_gen = snap.generation
    conf._last_check = time.monotonic()
    return snap


def test_no_lockout_before_first_tier(install_config, fake_redis):
    _install(install_config)
    state = progressive.register_failure("login", "1.2.3.4", "t:alice")
    assert state.locked is False
    assert progressive.is_locked("login", "1.2.3.4", "t:alice").locked is False


def test_crosses_tiers_with_escalating_blocks(install_config, fake_redis):
    _install(install_config)
    for _ in range(2):
        progressive.register_failure("login", "1.2.3.4", "t:alice")
    third = progressive.register_failure("login", "1.2.3.4", "t:alice")
    assert third.locked is True
    assert third.retry_after == 30       # tier 1: 3 failures -> 30s

    for _ in range(2):
        state = progressive.register_failure("login", "1.2.3.4", "t:alice")
    assert state.retry_after == 120       # tier 2: 5 failures -> 120s


def test_is_locked_reports_active_block(install_config, fake_redis):
    _install(install_config)
    for _ in range(3):
        progressive.register_failure("login", "9.9.9.9", "t:bob")
    state = progressive.is_locked("login", "9.9.9.9", "t:bob")
    assert state.locked is True
    assert state.retry_after > 0


def test_reset_clears_counters_and_block(install_config, fake_redis):
    _install(install_config)
    for _ in range(3):
        progressive.register_failure("login", "9.9.9.9", "t:bob")
    progressive.reset("login", "9.9.9.9", "t:bob")
    assert progressive.is_locked("login", "9.9.9.9", "t:bob").locked is False
    assert progressive.failure_count("login", "9.9.9.9", "t:bob") == 0


def test_identity_scope_isolates_accounts(install_config, fake_redis):
    _install(install_config, {"auth": {"progressive_lockout": {"scope": "identity"}}})
    for _ in range(3):
        progressive.register_failure("login", "1.2.3.4", "t:alice")
    # Different identity from the same IP is unaffected under identity scope.
    assert progressive.is_locked("login", "1.2.3.4", "t:carol").locked is False


def test_ip_scope_blocks_all_identities_from_ip(install_config, fake_redis):
    _install(install_config, {"auth": {"progressive_lockout": {"scope": "ip"}}})
    for _ in range(3):
        progressive.register_failure("login", "5.5.5.5", "t:alice")
    # IP scope: a fresh identity from the same IP is already locked.
    assert progressive.is_locked("login", "5.5.5.5", "t:zoe").locked is True


def test_disabled_is_noop(install_config, fake_redis):
    _install(install_config, {"auth": {"progressive_lockout": {"enabled": False}}})
    for _ in range(10):
        state = progressive.register_failure("login", "1.2.3.4", "t:alice")
    assert state.locked is False


def test_degrades_without_redis(install_config):
    # No fake_redis fixture -> get_client is None (autouse).
    _install(install_config)
    state = progressive.register_failure("login", "1.2.3.4", "t:alice")
    assert state.degraded is True
    assert state.locked is False
