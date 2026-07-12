"""Algorithm semantics on the in-memory backend (identical contract to the
Lua scripts — same inputs, same {allowed, remaining, retry} behaviour)."""
import pytest

from apps.security import algorithms
from apps.security.algorithms import MemoryBackend, evaluate


class Clock:
    def __init__(self, start_ms: int = 1_000_000):
        self.now = start_ms

    def __call__(self) -> int:
        return self.now

    def advance(self, ms: int) -> None:
        self.now += ms


@pytest.fixture
def clock(monkeypatch):
    c = Clock()
    monkeypatch.setattr(algorithms, "_now_ms", c)
    return c


# --------------------------------------------------------------------------- #
class TestSlidingWindow:
    def test_allows_up_to_limit_then_denies(self, clock):
        backend = MemoryBackend()
        for expected_remaining in (2, 1, 0):
            allowed, remaining, retry = backend.sliding_window("k", 3, 1000)
            assert allowed == 1
            assert remaining == expected_remaining
        allowed, _, retry = backend.sliding_window("k", 3, 1000)
        assert allowed == 0
        assert retry > 0

    def test_window_slides(self, clock):
        backend = MemoryBackend()
        for _ in range(3):
            backend.sliding_window("k", 3, 1000)
        assert backend.sliding_window("k", 3, 1000)[0] == 0
        clock.advance(1001)  # oldest events age out of the rolling window
        assert backend.sliding_window("k", 3, 1000)[0] == 1

    def test_keys_are_independent(self, clock):
        backend = MemoryBackend()
        assert backend.sliding_window("a", 1, 1000)[0] == 1
        assert backend.sliding_window("a", 1, 1000)[0] == 0
        assert backend.sliding_window("b", 1, 1000)[0] == 1


class TestTokenBucket:
    def test_burst_up_to_capacity(self, clock):
        backend = MemoryBackend()
        assert backend.token_bucket("k", 2, 1.0)[0] == 1
        assert backend.token_bucket("k", 2, 1.0)[0] == 1
        allowed, _, retry = backend.token_bucket("k", 2, 1.0)
        assert allowed == 0
        assert retry > 0

    def test_refills_over_time(self, clock):
        backend = MemoryBackend()
        backend.token_bucket("k", 2, 1.0)
        backend.token_bucket("k", 2, 1.0)
        assert backend.token_bucket("k", 2, 1.0)[0] == 0
        clock.advance(1000)  # 1 token/s refill
        assert backend.token_bucket("k", 2, 1.0)[0] == 1

    def test_never_exceeds_capacity(self, clock):
        backend = MemoryBackend()
        backend.token_bucket("k", 2, 1.0)
        clock.advance(60_000)  # a long idle refills to capacity, not beyond
        assert backend.token_bucket("k", 2, 1.0)[0] == 1
        assert backend.token_bucket("k", 2, 1.0)[0] == 1
        assert backend.token_bucket("k", 2, 1.0)[0] == 0


class TestLeakyBucketGCRA:
    def test_burst_tolerance_then_constant_rate(self, clock):
        backend = MemoryBackend()
        # emission 100ms, tau 200ms -> 3 back-to-back conforming requests
        assert backend.leaky_bucket("k", 100, 200)[0] == 1
        assert backend.leaky_bucket("k", 100, 200)[0] == 1
        assert backend.leaky_bucket("k", 100, 200)[0] == 1
        allowed, _, retry = backend.leaky_bucket("k", 100, 200)
        assert allowed == 0
        assert retry > 0

    def test_recovers_at_emission_rate(self, clock):
        backend = MemoryBackend()
        for _ in range(3):
            backend.leaky_bucket("k", 100, 200)
        assert backend.leaky_bucket("k", 100, 200)[0] == 0
        clock.advance(100)  # one emission interval frees one slot
        assert backend.leaky_bucket("k", 100, 200)[0] == 1


# --------------------------------------------------------------------------- #
class TestEvaluateDispatch:
    def test_sliding_window_decision(self, clock):
        backend = MemoryBackend()
        rule = {"algorithm": "sliding_window", "limit": 2, "window_seconds": 60}
        assert evaluate(backend, "k", rule).allowed is True
        assert evaluate(backend, "k", rule).allowed is True
        decision = evaluate(backend, "k", rule)
        assert decision.allowed is False
        assert decision.algorithm == "sliding_window"
        assert decision.retry_after >= 1
        headers = decision.headers(60)
        assert headers["X-RateLimit-Limit"] == "2"
        assert headers["X-RateLimit-Remaining"] == "0"
        assert "Retry-After" in headers

    def test_token_bucket_decision(self, clock):
        backend = MemoryBackend()
        rule = {"algorithm": "token_bucket", "capacity": 1, "refill_rate": 1}
        assert evaluate(backend, "k", rule).allowed is True
        decision = evaluate(backend, "k", rule)
        assert decision.allowed is False
        assert decision.algorithm == "token_bucket"

    def test_leaky_bucket_decision(self, clock):
        backend = MemoryBackend()
        rule = {"algorithm": "leaky_bucket", "limit": 10, "window_seconds": 1, "burst": 2}
        assert evaluate(backend, "k", rule).allowed is True
        assert evaluate(backend, "k", rule).algorithm == "leaky_bucket"
