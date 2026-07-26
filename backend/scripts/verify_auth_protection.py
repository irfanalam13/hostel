"""Ad-hoc Prompt 08 (auth protection & API rate limiting) verification against
the LIVE dev stack (real Redis). Leaves no data behind.

    python manage.py shell < scripts/verify_auth_protection.py
"""
import time
import uuid

from django.test import RequestFactory, override_settings

results = []


def check(label, cond):
    results.append((label, bool(cond)))


rf = RequestFactory()

try:
    from apps.security import (
        abuse, captcha, conf, progressive, redis_client, replay, reputation,
    )
    from apps.security.throttles import LoginRateThrottle, RoleRateThrottle

    conf.reset_for_tests()
    check("redis reachable", redis_client.get_client() is not None)

    # Install an enforce snapshot with tiny tiers for a deterministic check.
    from apps.security.conf import SecurityConfig, _deep_merge
    from apps.security.defaults import DEFAULTS

    data = _deep_merge(DEFAULTS, {
        "enabled": True, "mode": "enforce", "backend": "redis",
        "events": {"persist": False},
        "auth": {"progressive_lockout": {
            "enabled": True, "scope": "both", "failure_window_seconds": 3600,
            "tiers": [[3, 30], [5, 120]]}},
        "role_limits": {"enabled": True, "anon": 2, "window_seconds": 60,
                        "roles": {"STUDENT": 3, "default": 5},
                        "method_costs": {"GET": 1, "POST": 2, "OPTIONS": 0}},
        "rate_limits": {"auth_login": {"enabled": True, "algorithm": "sliding_window",
                                       "limit": 3, "window_seconds": 300}},
    })
    snap = SecurityConfig(data, [], generation=999)
    conf._snapshot = snap
    conf._snapshot_gen = 999
    conf._last_check = time.monotonic()

    ip = f"203.0.113.{uuid.uuid4().int % 254}"
    ident = f"verify:{uuid.uuid4().hex}"

    with override_settings(SECURITY_ENABLED=True):
        # 1. Progressive lockout escalates through tiers
        progressive.reset("login", ip, ident)
        states = [progressive.register_failure("login", ip, ident) for _ in range(3)]
        check("progressive lockout after tier 1", states[-1].locked and states[-1].retry_after == 30)
        check("is_locked reflects block", progressive.is_locked("login", ip, ident).locked)
        progressive.reset("login", ip, ident)
        check("reset clears lockout", not progressive.is_locked("login", ip, ident).locked)

        # 2. Credential stuffing detection
        ip2 = f"198.51.100.{uuid.uuid4().int % 254}"
        tripped = any(abuse.record_credential_stuffing(ip2, f"user{i}", None) for i in range(8))
        check("credential stuffing detected", tripped)
        _, score = reputation.status(ip2)
        check("stuffing penalised reputation", score > 0)
        reputation.clear(ip2)

        # 3. Replay protection
        nonce = uuid.uuid4().hex
        check("replay first use ok", replay.seen_before("verify", nonce, ttl=60) is False)
        check("replay second use blocked", replay.seen_before("verify", nonce, ttl=60) is True)

        # 4. CAPTCHA gated by secret (none set here -> never required)
        check("captcha off without secret", captcha.is_required(ip, failure_count=99) is False)

        # 5. Login IP throttle over the engine
        throttle = LoginRateThrottle()
        req = rf.post("/api/auth/login/")
        req.client_ip = ip
        allowed = sum(throttle.allow_request(req, None) for _ in range(3))
        check("login throttle allows up to limit", allowed == 3)
        check("login throttle blocks over limit", throttle.allow_request(req, None) is False)

        # 6. Role throttle: anon budget
        from types import SimpleNamespace

        rt = RoleRateThrottle()
        anon = rf.get("/api/x/")
        anon.client_ip = f"192.0.2.{uuid.uuid4().int % 254}"
        anon.user = SimpleNamespace(is_authenticated=False)
        anon_allowed = sum(rt.allow_request(anon, None) for _ in range(2))
        check("role throttle anon budget", anon_allowed == 2 and rt.allow_request(anon, None) is False)

    conf.reset_for_tests()
except Exception as e:
    print(f"ERROR during verification: {e}")
    raise

print("\n=== Auth protection & API rate limiting verification ===")
failed = 0
for label, ok in results:
    print(f"{'PASS' if ok else 'FAIL':4}  {label}")
    failed += 0 if ok else 1
print(f"\n{len(results) - failed}/{len(results)} checks passed")
