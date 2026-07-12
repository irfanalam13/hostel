"""Ad-hoc Phase 3 platform-API verification. Creates two throwaway users,
exercises the API via DRF's APIClient (force-authenticated), then cleans up
everything it created. Run: python manage.py shell < scripts/verify_platform_api.py
"""
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.tenants.models import Plan

H = {"HTTP_HOST": "localhost"}
results = []
created_plan_ids = []


def check(label, cond):
    results.append((label, bool(cond)))


su = User.objects.create(username="__phase3_su__", email="su@test.local",
                         is_superuser=True, is_staff=True, role="OWNER")
normal = User.objects.create(username="__phase3_user__", email="u@test.local",
                             is_superuser=False, role="OWNER")

client = APIClient()
client.force_authenticate(user=su)

try:
    # 1. Catalog listing
    r = client.get("/api/platform/features/", **H)
    check("features list 200", r.status_code == 200)
    body = r.json()
    n_features = body.get("meta", {}).get("pagination", {}).get("count")
    check("features present", (n_features or 0) > 0)

    # 2. Create a plan
    r = client.post("/api/platform/plans/", {"name": "Phase3 Test Plan", "price_monthly": "9.99"}, format="json", **H)
    check("plan create 201", r.status_code == 201)
    plan = r.json()["data"]
    pid = plan["id"]
    created_plan_ids.append(pid)
    check("plan slug auto-derived", bool(plan.get("slug")))

    # 3. Feature manager GET
    r = client.get(f"/api/platform/plans/{pid}/features/", **H)
    check("plan features GET 200", r.status_code == 200)

    # 4. Dependency violation (enable ai_reports, disable its requirement)
    r = client.put(
        f"/api/platform/plans/{pid}/features/",
        {"features": {"ai_reports": True, "analytics_dashboard": False}},
        format="json", **H,
    )
    check("dependency violation 400", r.status_code == 400)
    check("violation payload", r.json()["errors"].get("code") == "dependency_violation")

    # 5. Force through
    r = client.put(
        f"/api/platform/plans/{pid}/features/",
        {"features": {"ai_reports": True, "analytics_dashboard": False}, "force": True},
        format="json", **H,
    )
    check("force feature save 200", r.status_code == 200)
    rows = {row["key"]: row["enabled"] for row in r.json()["data"]}
    check("ai_reports enabled after force", rows.get("ai_reports") is True)

    # 6. Limits manager
    r = client.put(
        f"/api/platform/plans/{pid}/limits/",
        {"limits": {"max_students": {"value": 500, "is_unlimited": False},
                     "max_rooms": {"value": 0, "is_unlimited": True}}},
        format="json", **H,
    )
    check("limits save 200", r.status_code == 200)
    lrows = {row["key"]: row for row in r.json()["data"]}
    check("max_students=500", lrows["max_students"]["value"] == 500)
    check("max_rooms unlimited", lrows["max_rooms"]["is_unlimited"] is True)

    # 7. Duplicate
    r = client.post(f"/api/platform/plans/{pid}/duplicate/", {}, format="json", **H)
    check("duplicate 201", r.status_code == 201)
    clone = r.json()["data"]
    created_plan_ids.append(clone["id"])
    check("clone inactive", clone["is_active"] is False)
    check("clone distinct slug", clone["slug"] != plan["slug"])

    # 8. Archive action
    r = client.post(f"/api/platform/plans/{pid}/archive/", {}, format="json", **H)
    check("archive 200 + archived", r.status_code == 200 and r.json()["data"]["is_archived"] is True)

    # 9. Comparison matrix
    r = client.get("/api/platform/plans/comparison/", **H)
    check("comparison 200", r.status_code == 200)
    comp = r.json()["data"]
    check("comparison shape", "plans" in comp and "features" in comp and "limits" in comp)

    # 10. Export
    r = client.get("/api/platform/plans/export/", **H)
    check("export 200", r.status_code == 200 and isinstance(r.json()["data"]["plans"], list))

    # 11. Search filter
    r = client.get("/api/platform/plans/?search=Phase3", **H)
    check("search works", r.status_code == 200 and (r.json()["meta"]["pagination"]["count"] or 0) >= 1)

    # 12. Non-super user is denied
    client2 = APIClient()
    client2.force_authenticate(user=normal)
    r = client2.get("/api/platform/plans/", **H)
    check("non-super 403", r.status_code == 403)

except Exception:  # pragma: no cover
    import traceback
    traceback.print_exc()
    results.append(("EXCEPTION", False))
finally:
    Plan.objects.filter(pk__in=created_plan_ids).delete()
    su.delete()
    normal.delete()

ok = sum(1 for _, c in results if c)
for label, c in results:
    print(f"[{'PASS' if c else 'FAIL'}] {label}")
print(f"\n{ok}/{len(results)} checks passed")
