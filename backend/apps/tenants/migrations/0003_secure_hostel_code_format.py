import uuid

from django.db import migrations, models


def make_code(existing_codes):
    code = "HTL-" + uuid.uuid4().hex[:8].upper()
    while code in existing_codes:
        code = "HTL-" + uuid.uuid4().hex[:8].upper()
    existing_codes.add(code)
    return code


def migrate_hostel_codes(apps, schema_editor):
    Hostel = apps.get_model("tenants", "Hostel")
    existing_codes = set()
    for hostel in Hostel.objects.order_by("created_at", "id"):
        code = (hostel.code or "").upper()
        if code == "H-DEMO":
            new_code = "HTL-DEMO0001"
        elif code.startswith("HTL-") and len(code) == 12 and code[4:].isalnum() and code[4:].upper() == code[4:]:
            new_code = code
        else:
            new_code = make_code(existing_codes)

        while new_code in existing_codes:
            new_code = make_code(existing_codes)
        existing_codes.add(new_code)
        if hostel.code != new_code:
            hostel.code = new_code
            hostel.save(update_fields=["code"])


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0002_alter_hostel_code"),
    ]

    operations = [
        migrations.RunPython(migrate_hostel_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="hostel",
            name="code",
            field=models.CharField(blank=True, db_index=True, max_length=12, unique=True),
        ),
    ]
