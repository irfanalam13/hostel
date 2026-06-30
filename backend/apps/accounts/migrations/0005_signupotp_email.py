from django.db import migrations, models


class Migration(migrations.Migration):
    """Re-key SignupOTP from a User FK to an email address.

    Signup-email verification happens before any account exists, so the OTP is
    tied to the email being verified rather than to a user row. The table was
    introduced in 0004 but never used, so this is a safe destructive swap.
    """

    dependencies = [
        ("accounts", "0004_signupotp"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="signupotp",
            name="user",
        ),
        migrations.AddField(
            model_name="signupotp",
            name="email",
            field=models.EmailField(db_index=True, default="", max_length=254),
            preserve_default=False,
        ),
    ]
