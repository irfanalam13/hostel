"""Phase 5 verification: lifecycle assign, history, analytics, upgrade options.
Cleans up everything it creates. Run: python manage.py shell < scripts/verify_phase5.py
"""
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.tenants.models import Hostel, Plan
from apps.subscriptions.models import Feature, PlanFeature, SubscriptionEvent

H = {"HTTP_HOST": "localhost"}
results = []
created_hostel = None
created_pf = None


def check(label, cond):
    results.append((label, bool(cond)))


su = User.objects.create(username="__p5_su__", email="p5@test.local", is_superuser=True, is_staff=True)
client = APIClient()
client.force_authenticate(user=su)

try:
    starter = Plan.objects.get(slug="starter")

    # 1. Analytics endpoint
    r = client.get("/api/platform/analytics/", **H)
    check("analytics 200", r.status_code == 200)
    a = r.json()["data"]
    check("analytics has mrr/arr", "mrr" in a and "arr" in a)
    check("analytics feature_adoption", isinstance(a.get("feature_adoption"), list) and len(a["feature_adoption"]) > 0)

    # 2. Create a hostel and assign a plan via the platform API
    created_hostel = Hostel.objects.create(name="P5 Verify Hostel")
    r = client.post("/api/platform/subscriptions/", {"hostel": str(created_hostel.id), "plan": str(starter.id), "reason": "onboarding"}, format="json", **H)
    check("assign plan 200", r.status_code == 200)
    created_hostel.refresh_from_db()
    check("hostel.plan set", created_hostel.plan_id == starter.id)

    # 3. History records the assignment
    r = client.get(f"/api/platform/subscriptions/{created_hostel.id}/history/", **H)
    hist = r.json()["data"]
    check("history has 1 event", len(hist) == 1)
    check("history kind assigned", hist and hist[0]["kind"] == "assigned")

    # 4. Reassign to same plan → renewed; different price path exercised
    r = client.post("/api/platform/subscriptions/", {"hostel": str(created_hostel.id), "plan": str(starter.id)}, format="json", **H)
    r = client.get(f"/api/platform/subscriptions/{created_hostel.id}/history/", **H)
    kinds = [e["kind"] for e in r.json()["data"]]
    check("renewed recorded", "renewed" in kinds)

    # 5. Upgrade options: enable ai_reports on Starter, then query
    ai = Feature.objects.get(key="ai_reports")
    created_pf, _ = PlanFeature.objects.update_or_create(plan=starter, feature=ai, defaults={"is_enabled": True})
    r = client.get("/api/subscriptions/upgrade-options/?feature=ai_reports", **H)
    check("upgrade-options 200", r.status_code == 200)
    slugs = [p["slug"] for p in r.json()["data"]["plans"]]
    check("starter unlocks ai_reports", "starter" in slugs)

    # 6. Available plans endpoint
    r = client.get("/api/subscriptions/plans/", **H)
    check("available plans 200", r.status_code == 200 and isinstance(r.json()["data"], list))

except Exception:
    import traceback
    traceback.print_exc()
    results.append(("EXCEPTION", False))

ok = sum(1 for _, c in results if c)
for label, c in results:
    print(f"[{'PASS' if c else 'FAIL'}] {label}")
print(f"\n{ok}/{len(results)} checks passed")

# Best-effort cleanup (async audit writes reference the throwaway user via a
# SET_NULL FK; null those first to avoid a delete-time race).
try:
    from apps.auditlog.models import AuditEvent

    if created_pf:
        created_pf.delete()
    if created_hostel:
        SubscriptionEvent.objects.filter(hostel=created_hostel).delete()
        created_hostel.delete()
    AuditEvent.objects.filter(actor=su).update(actor=None)
    su.delete()
except Exception as exc:
    print(f"(cleanup note: {exc!r})")
