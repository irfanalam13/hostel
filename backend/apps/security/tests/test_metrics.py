"""Prometheus metric emission (Prompt 09). Guarded — skips cleanly if
prometheus_client isn't installed."""
import pytest

from apps.security import metrics


@pytest.mark.skipif(not metrics.available(), reason="prometheus_client not installed")
class TestMetrics:
    def _value(self, counter, **labels):
        # Read a labelled counter's current value from the prometheus client.
        return counter.labels(**labels)._value.get()

    def test_emit_increments_event_counter(self, install_config):
        before = self._value(metrics.SECURITY_EVENTS, event_type="waf_violation",
                             action="blocked")
        metrics.emit("waf_violation", "blocked", {"rules": ["sql_injection"]})
        after = self._value(metrics.SECURITY_EVENTS, event_type="waf_violation",
                            action="blocked")
        assert after == before + 1

    def test_auth_events_counted_separately(self, install_config):
        before = self._value(metrics.AUTH_EVENTS, event_type="auth_lockout")
        metrics.emit("auth_lockout", "blocked")
        after = self._value(metrics.AUTH_EVENTS, event_type="auth_lockout")
        assert after == before + 1

    def test_rate_limit_decision_counter(self, install_config):
        before = self._value(metrics.RATE_LIMIT_DECISIONS, scope="ip_global",
                             result="limited")
        metrics.record_rate_limit("ip_global", allowed=False)
        after = self._value(metrics.RATE_LIMIT_DECISIONS, scope="ip_global",
                            result="limited")
        assert after == before + 1

    def test_emit_never_raises_on_bad_input(self, install_config):
        # Robustness: emission must never raise into the request path.
        metrics.emit("x", "y", None)
        metrics.record_rate_limit("", True, degraded=True)


def test_emit_is_noop_when_unavailable(install_config, monkeypatch):
    # Force the "not installed" branch and prove it's a silent no-op.
    monkeypatch.setattr(metrics, "_AVAILABLE", False)
    metrics.emit("waf_violation", "blocked")
    metrics.record_rate_limit("ip_global", False)
    metrics.set_reputation_blocked(5)
