"""Re-seed the subscription feature/limit catalog (idempotent).

    python manage.py seed_subscription_catalog

Safe to run any time — it only adds rows that don't exist yet and never
overwrites Super-Admin edits.
"""
from django.core.management.base import BaseCommand

from apps.subscriptions.catalog import seed_catalog


class Command(BaseCommand):
    help = "Seed the subscription feature categories, features and limit definitions."

    def handle(self, *args, **options):
        seed_catalog(stdout=self.stdout)
