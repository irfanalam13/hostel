"""Ad-hoc Phase 2 verification. Runs in a rolled-back transaction so it leaves
no data behind. Invoke: python manage.py shell < scripts/verify_entitlements.py
"""
from django.db import transaction

from apps.tenants.models import Hostel, Plan
from apps.subscriptions.models import (
    Feature, LimitDefinition, PlanFeature, PlanLimit, FeatureOverride, LimitOverride,
)
from apps.subscriptions.entitlements import Entitlements, resolve_plan
from apps.subscriptions.gates import enforce_limit, enforce_feature
from apps.subscriptions.exceptions import FeatureNotAvailable, PlanLimitExceeded

results = []

def check(label, cond):
    results.append((label, bool(cond)))

try:
    with transaction.atomic():
        plan = Plan.objects.get(slug="starter")
        hostel = Hostel.objects.create(name="Verify Hostel", plan=plan)

        # 1. Plan resolution via canonical FK
        check("resolve_plan == starter", resolve_plan(hostel).pk == plan.pk)

        # 2. Stable default-on feature enabled by catalog default
        check("student_management default-on", Entitlements(hostel).can_use("student_management"))

        # 3. Beta feature default-off (release-stage gate)
        check("ai_reports beta default-off", not Entitlements(hostel).can_use("ai_reports"))

        # 4. Plan enables a beta feature -> now on (signal bumps cache generation)
        ai = Feature.objects.get(key="ai_reports")
        PlanFeature.objects.create(plan=plan, feature=ai, is_enabled=True)
        check("ai_reports on after PlanFeature", Entitlements(hostel).can_use("ai_reports"))

        # 5. Per-hostel override revokes a plan feature
        FeatureOverride.objects.create(hostel=hostel, feature=ai, is_enabled=False, reason="test")
        check("ai_reports off after override", not Entitlements(hostel).can_use("ai_reports"))

        # 6. enforce_feature raises structured error
        try:
            enforce_feature(hostel, "ai_reports")
            check("enforce_feature raised", False)
        except FeatureNotAvailable as e:
            check("enforce_feature code", e.detail.get("code") == "feature_not_available")

        # 7. Limit resolution: default max_rooms == 50
        check("max_rooms default 50", Entitlements(hostel).limit("max_rooms") == 50)

        # 8. PlanLimit override on the plan
        rooms_ld = LimitDefinition.objects.get(key="max_rooms")
        PlanLimit.objects.create(plan=plan, limit=rooms_ld, value=3)
        check("max_rooms == 3 from PlanLimit", Entitlements(hostel).limit("max_rooms") == 3)

        # 9. Unlimited limit override for the hostel
        LimitOverride.objects.create(hostel=hostel, limit=rooms_ld, is_unlimited=True)
        check("max_rooms unlimited via override", Entitlements(hostel).limit("max_rooms") is None)
        check("is_unlimited true", Entitlements(hostel).is_unlimited("max_rooms"))

        # 10. enforce_limit blocks when quota is 0 (LimitOverride value=0, 0 residents)
        students_ld = LimitDefinition.objects.get(key="max_students")
        LimitOverride.objects.create(hostel=hostel, limit=students_ld, value=0)
        try:
            enforce_limit(hostel, "max_students")
            check("enforce_limit raised at 0 quota", False)
        except PlanLimitExceeded as e:
            check("enforce_limit code", e.detail.get("code") == "plan_limit_reached")
            # DRF stringifies APIException.detail leaf values.
            check("enforce_limit reports max=0", int(e.detail.get("max")) == 0)

        # 11. enforce_limit no-ops when unlimited
        try:
            enforce_limit(hostel, "max_rooms")  # unlimited via override above
            check("enforce_limit unlimited no-op", True)
        except Exception:
            check("enforce_limit unlimited no-op", False)

        transaction.set_rollback(True)
except Exception as exc:  # pragma: no cover
    results.append(("EXCEPTION", False))
    print("ERROR:", repr(exc))

ok = sum(1 for _, c in results if c)
for label, c in results:
    print(f"[{'PASS' if c else 'FAIL'}] {label}")
print(f"\n{ok}/{len(results)} checks passed")
