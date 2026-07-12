"""Seed the default feature/category/limit catalog on fresh deploys.

Idempotent: delegates to ``catalog.seed_catalog`` with the migration's
historical app registry, using ``get_or_create`` per key so it never clobbers
Super-Admin edits. Re-runnable any time via the ``seed_subscription_catalog``
management command.
"""
from django.db import migrations


def seed(apps, schema_editor):
    from apps.subscriptions.catalog import seed_catalog

    seed_catalog(apps=apps)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("subscriptions", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, noop),
    ]
