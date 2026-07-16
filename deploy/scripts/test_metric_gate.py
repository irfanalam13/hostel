"""Unit tests for the metric gate's pure evaluation core (Phase 3, §3).

Run: python -m pytest deploy/scripts/test_metric_gate.py
No Prometheus or network needed — `classify` is deliberately pure.
"""
from metric_gate import Thresholds, classify

T = Thresholds(max_error_rate=0.05, max_p95=1.0)


def test_healthy_has_no_breaches():
    assert classify(error_rate=0.01, p95=0.4, t=T) == []


def test_error_rate_breach():
    breaches = classify(error_rate=0.20, p95=0.4, t=T)
    assert len(breaches) == 1 and "error_rate" in breaches[0]


def test_latency_breach():
    breaches = classify(error_rate=0.0, p95=2.5, t=T)
    assert len(breaches) == 1 and "p95" in breaches[0]


def test_both_breach():
    assert len(classify(error_rate=0.5, p95=3.0, t=T)) == 2


def test_none_samples_are_not_breaches():
    # Cold target / metric not yet scraped must NOT trigger a false rollback.
    assert classify(error_rate=None, p95=None, t=T) == []


def test_exactly_at_threshold_is_ok():
    # Strictly-greater-than semantics: at the limit is still healthy.
    assert classify(error_rate=0.05, p95=1.0, t=T) == []
