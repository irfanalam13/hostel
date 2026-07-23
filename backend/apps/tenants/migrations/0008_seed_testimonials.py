from django.db import migrations


# Featured = shown as cards on the landing (the curated/"purified" picks).
FEATURED = [
    {
        "author_name": "Priya Sharma",
        "author_role": "Warden, City Girls' Hostel",
        "rating": 5,
        "quote": "We replaced three spreadsheets and a register book. Collections are up and month-end takes an hour, not a week.",
    },
    {
        "author_name": "Anil Gurung",
        "author_role": "Hostel Manager, Sunrise College",
        "rating": 5,
        "quote": "The offline mode is a lifesaver. Our campus internet is unreliable, but the front desk never stops working.",
    },
    {
        "author_name": "Rajesh Thapa",
        "author_role": "Owner, Greenfield Hostels",
        "rating": 5,
        "quote": "Occupancy and dues at a glance across all four blocks. I finally run the hostel from my phone.",
    },
]

# Approved but not featured — these don't show as cards, but they DO count toward
# the public rating stats (total reviews, appreciation %, overall rating).
APPROVED = [
    ("Meera Joshi", "Warden, Riverside Hostel", 5, "Admissions used to take a day of paperwork. Now it's a few minutes per resident."),
    ("Bikash Rai", "Accountant, Hilltop Boys' Hostel", 5, "Invoices generate themselves and reconciliation is finally painless."),
    ("Sunita K.C.", "Owner, Lotus Residency", 4, "Great value and very easy for my staff to pick up. A few reports I'd still like to see."),
    ("Deepak Adhikari", "Manager, Everest Student Living", 5, "Bed allocation and transfers are so much clearer now."),
    ("Nisha Tamang", "Warden, Maple Girls' Hostel", 4, "The notices and notifications save me a lot of phone calls."),
    ("Hari Prasad", "Owner, Greenwood Hostels", 5, "Dues tracking alone paid for the subscription in the first month."),
    ("Sabina Lama", "Finance, Unity Boarding", 4, "Audit-ready exports made our inspection painless."),
    ("Ramesh Shrestha", "Manager, Downtown Stays", 3, "Solid product overall; setup took us a little while to get right."),
    ("Gita Bhandari", "Warden, Sunflower Hostel", 5, "Attendance and gate logs give us real peace of mind on safety."),
]


def seed(apps, schema_editor):
    Testimonial = apps.get_model("tenants", "Testimonial")
    # Only seed a fresh install; never touch real submissions/curation.
    if Testimonial.objects.exists():
        return
    for i, t in enumerate(FEATURED):
        Testimonial.objects.create(
            **t, is_approved=True, is_featured=True, sort_order=i, source="seed"
        )
    for name, role, rating, quote in APPROVED:
        Testimonial.objects.create(
            author_name=name, author_role=role, rating=rating, quote=quote,
            is_approved=True, is_featured=False, source="seed",
        )


def unseed(apps, schema_editor):
    Testimonial = apps.get_model("tenants", "Testimonial")
    Testimonial.objects.filter(source="seed").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0007_testimonial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
