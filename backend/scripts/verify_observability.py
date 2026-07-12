"""Ad-hoc Prompt 09 (monitoring/observability/ops) verification against the
LIVE dev stack. Leaves no data behind (rolled back).

    python manage.py shell < scripts/verify_observability.py
"""
from django.db import transaction

results = []


def check(label, cond):
    results.append((label, bool(cond)))


try:
    with transaction.atomic():
        from apps.security import conf, metrics, reports, threat
        from apps.security.models import IPRule, SecurityEvent, SecuritySetting

        # 1. Metrics library wired
        check("prometheus metrics available", metrics.available())
        metrics.emit("waf_violation", "blocked", {"rules": ["sql_injection"]})
        metrics.record_rate_limit("ip_global", allowed=False)
        check("metric emission does not raise", True)

        # 2. Threat aggregation over real rows
        SecurityEvent.objects.create(event_type="rate_limited", action="blocked",
                                     ip="203.0.113.200", path="/api/x/")
        SecurityEvent.objects.create(event_type="auth_failure", action="logged",
                                     ip="203.0.113.201")
        summary = threat.summary(window_hours=24)
        check("threat summary counts events", summary["total_events"] >= 2)
        check("threat summary has level", summary["threat_level"] in
              ("normal", "elevated", "high", "critical"))
        check("top offenders lists blocked ip",
              any(o["ip"] == "203.0.113.200" for o in threat.top_offenders()))

        # 3. Report generation + CSV
        report = reports.build(period="daily")
        check("report has recommendations", bool(report.get("recommendations")))
        csv_text = reports.to_csv(report)
        check("report csv well-formed", "section,key,value" in csv_text)

        # 4. Dynamic config rule + hot reload (generation bump)
        gen_before = conf.get_config().generation
        SecuritySetting.objects.create(key="kill.rate_limiter", value=True)
        check("kill switch setting hot-reloads",
              conf.get_config().generation != gen_before)
        check("kill switch reflected in config",
              conf.get_config().get("kill.rate_limiter") is True)

        # 5. Rate limiter bypassed under kill switch
        from apps.security import engine

        decision = engine.check("ip_global", "203.0.113.202")
        check("engine bypasses under kill switch", decision.allowed is True)

        # 6. IP rule loads into snapshot
        import ipaddress

        IPRule.objects.create(cidr="198.51.100.0/24", action="deny", note="verify")
        conf.bump()
        matched = conf.get_config().match_ip_rule(ipaddress.ip_address("198.51.100.5"))
        check("ip rule active in resolved config", matched is not None)

        raise RuntimeError("rollback")
except RuntimeError as e:
    if str(e) != "rollback":
        raise
finally:
    from apps.security import conf as _conf

    _conf.bump()
    _conf.reset_for_tests()

print("\n=== Monitoring / observability / ops verification ===")
failed = 0
for label, ok in results:
    print(f"{'PASS' if ok else 'FAIL':4}  {label}")
    failed += 0 if ok else 1
print(f"\n{len(results) - failed}/{len(results)} checks passed")
