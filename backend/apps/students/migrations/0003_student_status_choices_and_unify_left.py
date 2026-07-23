from django.db import migrations, models


def unify_former_to_left(apps, schema_editor):
    """Collapse every non-ACTIVE student onto the single 'former' state, LEFT.

    Historically 'leaving' was recorded two ways: the Vacate button wrote
    INACTIVE while /checkout wrote LEFT. We now standardise on LEFT so the
    Current/Former/All filter partitions cleanly.
    """
    Student = apps.get_model("students", "Student")
    Student.objects.exclude(status="ACTIVE").update(status="LEFT")


def noop_reverse(apps, schema_editor):
    # Irreversible in a meaningful way: we cannot recover the original
    # INACTIVE-vs-LEFT distinction. Leave existing rows as-is.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("students", "0002_student_citizenship_number_student_date_of_birth_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="student",
            name="status",
            field=models.CharField(
                choices=[("ACTIVE", "Active"), ("LEFT", "Left")],
                default="ACTIVE",
                max_length=20,
            ),
        ),
        migrations.RunPython(unify_former_to_left, noop_reverse),
    ]
