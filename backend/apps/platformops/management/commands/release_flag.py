"""Drive a feature flag as a progressive-release control (Phase 3, §3 CD).

Dark-launch → ramp → confirm → (if needed) instant rollback, all on the existing
flag engine (apps.platformops.flags). Deploy code behind `is_enabled("my_flag")`,
ship it dark, then ramp exposure without another deploy:

    # create dark (off for everyone)
    python manage.py release_flag checkout_v2 --name "Checkout v2" --describe "New flow"
    # ramp
    python manage.py release_flag checkout_v2 --activate --rollout 10
    python manage.py release_flag checkout_v2 --rollout 50
    python manage.py release_flag checkout_v2 --rollout 100
    # limit to roles while testing
    python manage.py release_flag checkout_v2 --activate --roles OWNER,ADMIN
    # INSTANT ROLLBACK (kill beats everything, no deploy needed)
    python manage.py release_flag checkout_v2 --kill
    # inspect only
    python manage.py release_flag checkout_v2 --show
"""
from django.core.management.base import BaseCommand, CommandError

from apps.platformops.flags import invalidate_cache
from apps.platformops.models import FeatureFlag


class Command(BaseCommand):
    help = "Create/update a feature flag to drive a progressive release or roll it back."

    def add_arguments(self, parser):
        parser.add_argument("key", help="Flag key (slug).")
        parser.add_argument("--name", help="Human-readable name (set on create/update).")
        parser.add_argument("--describe", dest="description", help="Description.")

        state = parser.add_mutually_exclusive_group()
        state.add_argument("--activate", action="store_true", help="Set is_active=True.")
        state.add_argument("--deactivate", action="store_true", help="Set is_active=False.")

        kill = parser.add_mutually_exclusive_group()
        kill.add_argument("--kill", action="store_true", help="Emergency OFF (overrides all) -> rollback.")
        kill.add_argument("--unkill", action="store_true", help="Clear the kill switch.")

        parser.add_argument("--rollout", type=int, help="Rollout percentage (0-100).")
        parser.add_argument("--roles", help="Comma-separated role codes to target (empty string clears).")
        parser.add_argument("--show", action="store_true", help="Print current state and exit (no change).")

    def handle(self, *args, **opts):
        key = opts["key"]

        if opts["show"]:
            try:
                flag = FeatureFlag.objects.get(key=key)
            except FeatureFlag.DoesNotExist as e:
                raise CommandError(f"Flag '{key}' does not exist.") from e
            return self._print(flag)

        flag, created = FeatureFlag.objects.get_or_create(key=key)
        if created:
            flag.name = opts.get("name") or key
            self.stdout.write(f"Created flag '{key}' (off for everyone).")

        if opts.get("name") is not None:
            flag.name = opts["name"]
        if opts.get("description") is not None:
            flag.description = opts["description"]

        if opts["activate"]:
            flag.is_active = True
        elif opts["deactivate"]:
            flag.is_active = False

        if opts["kill"]:
            flag.kill = True
        elif opts["unkill"]:
            flag.kill = False

        if opts.get("rollout") is not None:
            pct = opts["rollout"]
            if not 0 <= pct <= 100:
                raise CommandError("--rollout must be between 0 and 100.")
            flag.rollout_percentage = pct

        if opts.get("roles") is not None:
            flag.allowed_roles = [r.strip() for r in opts["roles"].split(",") if r.strip()]

        flag.save()
        invalidate_cache()  # so the change is live immediately, not after the 30s TTL
        self.stdout.write(self.style.SUCCESS(f"Updated flag '{key}'."))
        self._print(flag)

    def _print(self, flag):
        self.stdout.write(
            "  " + " | ".join([
                f"key={flag.key}",
                f"active={flag.is_active}",
                f"kill={flag.kill}",
                f"rollout={flag.rollout_percentage}%",
                f"roles={flag.allowed_roles or 'any'}",
            ])
        )
