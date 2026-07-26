"""Ad-hoc Prompt 07 (edge security foundation) verification against the LIVE
dev stack (real Redis, real DB). Runs in a rolled-back transaction so it
leaves no data behind.

Invoke inside the web container (or any env with Redis + DB reachable):

    python manage.py shell < scripts/verify_edge_security.py
"""
import time
import uuid

from django.db import transaction
from django.test import RequestFactory

results = []


def check(label, cond):
    results.append((label, bool(cond)))


rf = RequestFactory()

try:
    with transaction.atomic():
        from apps.security import conf, engine, redis_client
        from apps.security.algorithms import RedisBackend
        from apps.security.ip import resolve_client_ip
        from apps.security.locks import RedisLock
        from apps.security.models import IPRule, SecuritySetting
        from apps.security.waf import inspect

        # 1. Config resolution + environment overlay
        conf.reset_for_tests()
        config = conf.get_config()
        check("config loads", config is not None)
        check("config has rate_limits", bool(config.get("rate_limits.ip_global.limit")))
        print(f"   environment mode={config.get('mode')} "
              f"fail={config.get('fail_strategy')} backend={config.get('backend')}")

        # 2. Redis connectivity + distributed algorithms (live Lua)
        client = redis_client.get_client()
        check("redis reachable", client is not None)
        if client is not None:
            backend = RedisBackend(client)
            key = f"sec:verify:{uuid.uuid4().hex}"
            allowed = [backend.sliding_window(key, 3, 60_000)[0] for _ in range(4)]
            check("lua sliding window 3-allow-1-deny", allowed == [1, 1, 1, 0])
            key2 = f"sec:verify:{uuid.uuid4().hex}"
            allowed = [backend.token_bucket(key2, 2, 1.0)[0] for _ in range(3)]
            check("lua token bucket burst 2", allowed == [1, 1, 0])
            key3 = f"sec:verify:{uuid.uuid4().hex}"
            allowed = [backend.leaky_bucket(key3, 100, 200)[0] for _ in range(4)]
            check("lua GCRA burst tolerance", allowed == [1, 1, 1, 0])
            client.delete(key, key2, key3)

        # 3. Engine end-to-end (multi-container-correct path)
        identity = f"verify:{uuid.uuid4().hex}"
        rule = {"algorithm": "sliding_window", "limit": 2, "window_seconds": 60}
        engine_ok = (engine.check("verify_scope", identity, rule=rule).allowed
                     and engine.check("verify_scope", identity, rule=rule).allowed
                     and not engine.check("verify_scope", identity, rule=rule).allowed)
        check("engine enforces explicit rule", engine_ok)

        # 4. Distributed lock: exclusion + safe release
        with RedisLock(f"verify:{uuid.uuid4().hex}", ttl=5) as lock:
            check("lock acquired", lock.acquired)
            second = RedisLock(lock.key.removeprefix("sec:lock:"), ttl=5)
            check("lock mutual exclusion", not second.acquire())
        check("lock released", RedisLock(lock.key.removeprefix("sec:lock:"), ttl=5).acquire())

        # 5. Hot reload: DB override propagates without restart
        gen_before = conf.get_config().generation
        SecuritySetting.objects.create(key="bots.blocked_action", value="log")
        time.sleep(0)  # signal fires synchronously
        cfg2 = conf.get_config()
        check("hot reload generation bumped", cfg2.generation != gen_before)
        check("hot reload value applied", cfg2.get("bots.blocked_action") == "log")

        # 6. IPRule loads into the snapshot
        IPRule.objects.create(cidr="203.0.113.0/24", action="deny", note="verify")
        import ipaddress
        cfg3 = conf.get_config()
        check("ip rule matched", cfg3.match_ip_rule(ipaddress.ip_address("203.0.113.7")) is not None)

        # 7. Spoof-resistant IP resolution
        req = rf.get("/", REMOTE_ADDR="203.0.113.5", HTTP_X_FORWARDED_FOR="9.9.9.9")
        check("direct peer ignores XFF",
              resolve_client_ip(req, cfg3).ip == "203.0.113.5")

        # 8. WAF flags an injection attempt, passes clean traffic
        bad = rf.get("/api/x/?q=1%20UNION%20SELECT%20a%20FROM%20b")
        good = rf.get("/api/residents/?search=o'brien")
        check("waf flags sqli", any(v.rule == "sql_injection" for v in inspect(bad, cfg3)))
        check("waf clean on legit query", inspect(good, cfg3) == [])

        raise RuntimeError("rollback")  # leave no data behind
except RuntimeError as e:
    if str(e) != "rollback":
        raise
finally:
    from apps.security import conf as _conf
    _conf.bump()            # drop snapshots built from the rolled-back data
    _conf.reset_for_tests()

print("\n=== Edge security foundation verification ===")
failed = 0
for label, ok in results:
    print(f"{'PASS' if ok else 'FAIL':4}  {label}")
    failed += 0 if ok else 1
print(f"\n{len(results) - failed}/{len(results)} checks passed")
