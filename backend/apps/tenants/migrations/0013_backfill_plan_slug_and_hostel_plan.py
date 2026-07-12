"""Backfill Plan.slug for existing rows and link each Hostel to its Plan.

Existing plans predate the ``slug`` field, so populate it from the name. Then
point ``Hostel.plan`` (the new canonical FK) at the Plan matching the legacy
free-text ``plan_name`` where one exists — non-destructive: ``plan_name`` is
left in place for backward compatibility.
"""
from django.db import migrations
from django.utils.text import slugify


def backfill(apps, schema_editor):
    Plan = apps.get_model("tenants", "Plan")
    Hostel = apps.get_model("tenants", "Hostel")

    used = set(Plan.objects.exclude(slug__isnull=True).values_list("slug", flat=True))
    for plan in Plan.objects.filter(slug__isnull=True):
        base = slugify(plan.name or "") or "plan"
        candidate = base[:60]
        i = 2
        while candidate in used:
            suffix = str(i)
            candidate = f"{base[: 60 - len(suffix) - 1]}-{suffix}"
            i += 1
        plan.slug = candidate
        used.add(candidate)
        plan.save(update_fields=["slug"])

    # Resolve each hostel's plan_name to a Plan (match slug, then name).
    plans_by_key = {}
    for plan in Plan.objects.all():
        if plan.slug:
            plans_by_key.setdefault(plan.slug.lower(), plan)
        plans_by_key.setdefault((plan.name or "").lower(), plan)

    for hostel in Hostel.objects.filter(plan__isnull=True).exclude(plan_name=""):
        match = plans_by_key.get((hostel.plan_name or "").strip().lower())
        if match:
            hostel.plan = match
            hostel.save(update_fields=["plan"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("tenants", "0012_hostel_plan_plan_badge_plan_billing_interval_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
