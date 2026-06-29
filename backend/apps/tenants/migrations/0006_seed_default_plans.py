from django.db import migrations


# Default catalog mirroring the previous static landing copy, now numeric so
# discounts can apply. These are starting points — admins edit them (and launch
# discounts) from the Django admin. Seeded only when a plan of the same name
# doesn't already exist, so it never clobbers real data.
DEFAULT_PLANS = [
    {
        "name": "Starter",
        "description": "For a single small hostel getting organised.",
        "price_monthly": 0,
        "period": "forever",
        "max_students": 60,
        "max_rooms": 50,
        "features": [
            "Up to 50 beds",
            "Admissions & occupancy",
            "Basic billing & payments",
            "Offline PWA access",
            "Community support",
        ],
        "cta_label": "Get started",
        "cta_href": "/signup",
        "is_featured": False,
        "is_public": True,
        "sort_order": 0,
    },
    {
        "name": "Growth",
        "description": "For growing hostels that need automation and insights.",
        "price_monthly": 1999,
        "period": "per hostel / month",
        "max_students": 500,
        "max_rooms": 200,
        "features": [
            "Unlimited beds",
            "Automated recurring billing",
            "Reports & analytics",
            "Attendance, gate & visitors",
            "Push notifications",
            "Priority support",
        ],
        "cta_label": "Start free trial",
        "cta_href": "/signup",
        "is_featured": True,
        "is_public": True,
        "sort_order": 1,
    },
    {
        "name": "Enterprise",
        "description": "For institutions and multi-property operators.",
        "price_monthly": 4999,
        "period": "per hostel / month",
        "max_students": 5000,
        "max_rooms": 2000,
        "features": [
            "Everything in Growth",
            "Multi-tenant management",
            "SSO & advanced roles",
            "Disaster recovery & backups",
            "Audit & compliance exports",
            "Dedicated success manager",
        ],
        "cta_label": "Contact sales",
        "cta_href": "#contact",
        "is_featured": False,
        "is_public": True,
        "sort_order": 2,
    },
]


def seed_plans(apps, schema_editor):
    Plan = apps.get_model("tenants", "Plan")
    for data in DEFAULT_PLANS:
        Plan.objects.get_or_create(name=data["name"], defaults=data)


def unseed_plans(apps, schema_editor):
    Plan = apps.get_model("tenants", "Plan")
    Plan.objects.filter(name__in=[p["name"] for p in DEFAULT_PLANS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0005_alter_plan_options_plan_cta_href_plan_cta_label_and_more"),
    ]

    operations = [
        migrations.RunPython(seed_plans, unseed_plans),
    ]
