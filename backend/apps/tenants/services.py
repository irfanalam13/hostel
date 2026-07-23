"""Workspace domain services.

Everything that *changes* tenant state funnels through here so the rules stay
in one place:

* availability checks + username suggestions (DB-touching, so not in
  ``validators.py``)
* transactional workspace provisioning (tenant + owner link + defaults +
  audit trail — all-or-nothing)
* lifecycle transitions (activate / suspend / archive / restore / soft
  delete) with audit logging and cache invalidation

Cache invalidation on save/delete is wired via signals in ``apps.py``, so
services only need to mutate and save.
"""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .cache import invalidate_alias_cache, invalidate_tenant_cache
from .models import Hostel, WorkspaceAlias, WorkspaceStatus, generate_workspace_username
from .validators import (
    clean_workspace_username,
    normalize_workspace_username,
    reserved_workspace_names,
    workspace_username_limits,
    WORKSPACE_USERNAME_RE,
)

logger = logging.getLogger(__name__)

# Seeded into ``Hostel.settings`` for every new workspace. The project's RBAC
# is role-based (accounts.User.role), so "default roles / permission groups"
# are recorded as workspace configuration rather than a parallel Group table.
DEFAULT_WORKSPACE_SETTINGS = {
    "roles": ["OWNER", "MANAGER", "ACCOUNTANT", "WARDEN", "STAFF", "RESIDENT"],
    "permission_groups": {
        "management": ["OWNER", "MANAGER"],
        "finance": ["OWNER", "MANAGER", "ACCOUNTANT"],
        "operations": ["OWNER", "MANAGER", "WARDEN", "STAFF"],
    },
    "features": {"payments": True, "attendance": True, "complaints": True, "notices": True},
    "branding": {"logo_url": "", "primary_color": ""},
}

# Default departments seeded for every new workspace so it has a usable org
# structure the moment it exists; owners rename, deactivate or extend these
# later (they are ordinary tenant-scoped ``staff.Department`` rows).
DEFAULT_DEPARTMENTS = [
    "Administration",
    "Front Desk",
    "Housekeeping",
    "Maintenance",
    "Security",
    "Accounts",
    "Kitchen & Mess",
]


def _default_plan(plan_name: str):
    """Resolve the plan a new workspace should start on.

    Prefers the requested plan (by slug then name), then the cheapest public
    plan, then any plan at all. Returns ``None`` when no plans are seeded yet —
    subscription seeding is then skipped (best-effort); ``Hostel.plan_name``
    still carries the canonical fallback the entitlement engine reads.
    """
    from .models import Plan

    name = (plan_name or "").strip()
    if name:
        plan = (
            Plan.objects.filter(slug__iexact=name).first()
            or Plan.objects.filter(name__iexact=name).first()
        )
        if plan is not None:
            return plan
    return (
        Plan.objects.filter(is_public=True)
        .order_by("sort_order", "price_monthly", "name")
        .first()
        or Plan.objects.order_by("sort_order").first()
    )


def is_workspace_username_available(username: str, *, exclude_pk=None) -> bool:
    """DB-level availability. Assumes the value is already normalized+valid.

    Aliases (usernames retired by a rename, kept for 301 redirects) count as
    taken — except an alias owned by ``exclude_pk`` itself, which that
    workspace may reclaim by renaming back.
    """
    qs = Hostel.objects.filter(slug=username)
    alias_qs = WorkspaceAlias.objects.filter(slug=username)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
        alias_qs = alias_qs.exclude(hostel_id=exclude_pk)
    return not qs.exists() and not alias_qs.exists()


def suggest_workspace_usernames(base: str, *, limit: int = 4) -> list[str]:
    """Available alternatives for a taken/invalid username, best first."""
    min_len, max_len = workspace_username_limits()
    seed = normalize_workspace_username(base)
    # Strip to legal characters so even messy input yields suggestions.
    seed = "".join(ch for ch in seed if ch.isalnum() or ch == "-").strip("-") or "hostel"
    year = timezone.localdate().year

    candidates = [
        f"{seed}hostel",
        f"{seed}-hostel",
        f"{seed}{year}",
        f"{seed}-hq",
        f"{seed}-app",
    ] + [f"{seed}-{i}" for i in range(2, 12)]

    suggestions: list[str] = []
    reserved = reserved_workspace_names()
    for cand in candidates:
        cand = cand[:max_len].rstrip("-")
        if len(cand) < min_len or not WORKSPACE_USERNAME_RE.match(cand):
            continue
        if cand in reserved or cand in suggestions:
            continue
        if is_workspace_username_available(cand):
            suggestions.append(cand)
        if len(suggestions) >= limit:
            break
    return suggestions


def _audit(hostel, actor, action, message, meta=None):
    """Best-effort audit-trail entry (never fails the business operation)."""
    try:
        from apps.auditlog.models import AuditEvent

        AuditEvent.objects.create(
            hostel_id=hostel.pk,
            actor=actor if getattr(actor, "is_authenticated", False) else None,
            action=action,
            entity_type="workspace",
            entity_id=str(hostel.pk),
            message=message,
            meta={"slug": hostel.slug, "status": hostel.status, **(meta or {})},
        )
    except Exception:
        logger.exception("workspace audit write failed (hostel=%s)", hostel.pk)


@transaction.atomic
def provision_workspace(
    *,
    owner,
    hostel_name: str,
    workspace_username: str | None = None,
    phone: str = "",
    address: str = "",
    owner_name: str = "",
    timezone_name: str = "",
    currency: str = "",
    language: str = "",
    plan_name: str = "basic",
) -> Hostel:
    """Create a complete, isolated workspace in a single transaction.

    Creates the tenant, generates/validates the permanent workspace username,
    links the owner, seeds default settings/configuration, and writes the
    initial audit + activity records. Any failure rolls back everything.

    Raises ``django.core.exceptions.ValidationError`` for a bad or taken
    username (callers translate to API errors).
    """
    from django.core.exceptions import ValidationError

    if workspace_username:
        slug = clean_workspace_username(workspace_username)
        # ``select_for_update``-grade races are closed by the DB unique
        # constraint; this check exists to give a friendly error first.
        if not is_workspace_username_available(slug):
            raise ValidationError(
                {"workspace_username": "This workspace username is already taken."},
                code="taken",
            )
    else:
        slug = generate_workspace_username(hostel_name)

    trial_days = int(getattr(settings, "TENANT_TRIAL_DAYS", 14))
    hostel = Hostel.objects.create(
        name=hostel_name,
        slug=slug,
        phone=phone or "",
        address=address or "",
        owner=owner,
        owner_name=owner_name or getattr(owner, "username", "") or "",
        status=WorkspaceStatus.TRIAL if trial_days else WorkspaceStatus.ACTIVE,
        trial_ends_at=timezone.localdate() + timedelta(days=trial_days) if trial_days else None,
        timezone=timezone_name or "Asia/Kathmandu",
        currency=currency or "NPR",
        language=language or "en",
        plan_name=plan_name,
        settings=DEFAULT_WORKSPACE_SETTINGS,
    )

    # Owner membership link (the core access grant for every scoped endpoint).
    from apps.accounts.models import UserHostel

    UserHostel.objects.create(user=owner, hostel=hostel, is_active=True)

    # Default public website: scaffold + publish now so the workspace URL works
    # from the moment it exists (Prompt 03 also scaffolds lazily on first hit —
    # this makes "a default website" part of workspace *creation* per Prompt 01).
    # Best-effort: a website-app hiccup must never fail workspace provisioning.
    try:
        from apps.website.services import get_or_scaffold_website

        get_or_scaffold_website(hostel)
    except Exception:
        logger.exception("default website scaffold failed (hostel=%s)", hostel.pk)

    # Default subscription. Reuse the subscription lifecycle service so the
    # Subscription row + immutable SubscriptionEvent + entitlement cache are
    # written exactly as any later plan change would be — no duplicate
    # provisioning logic. Savepoint-isolated best-effort: if no plans are seeded
    # yet (fresh install) or the subscriptions app errors, the workspace still
    # provisions and `plan_name` remains the canonical entitlement fallback.
    try:
        with transaction.atomic():
            plan = _default_plan(plan_name)
            if plan is not None:
                from apps.subscriptions.lifecycle import assign_plan

                sub_status = "trial" if hostel.status == WorkspaceStatus.TRIAL else "active"
                assign_plan(
                    hostel,
                    plan,
                    actor=owner,
                    status=sub_status,
                    end_date=hostel.trial_ends_at,
                    reason="Workspace provisioned",
                )
    except Exception:
        logger.exception("default subscription seed failed (hostel=%s)", hostel.pk)

    # Default departments — savepoint-isolated so a staff-app hiccup can never
    # fail an otherwise-successful signup. ``ignore_conflicts`` keeps re-runs
    # idempotent against the (hostel, name) uniqueness constraint.
    try:
        with transaction.atomic():
            from apps.staff.models import Department

            Department.objects.bulk_create(
                [Department(hostel=hostel, name=name) for name in DEFAULT_DEPARTMENTS],
                ignore_conflicts=True,
            )
    except Exception:
        logger.exception("default departments seed failed (hostel=%s)", hostel.pk)

    # Initial audit log + activity entry.
    _audit(hostel, owner, "create", "Workspace created",
           meta={"workspace_url": hostel.workspace_url})

    return hostel


# --------------------------------------------------------------------------- #
# Workspace rename (Prompt 04 — the managed exception to slug permanence)
# --------------------------------------------------------------------------- #
@transaction.atomic
def rename_workspace_username(hostel: Hostel, new_username: str, actor=None) -> Hostel:
    """Change the workspace username, transactionally and reversibly:

    * validates + availability-checks the new username (aliases included)
    * keeps the OLD username as a ``WorkspaceAlias`` → the middleware answers
      the old URL with a permanent 301 redirect to the new one
    * updates routing (the slug IS the route), invalidates every cache entry
      for both names, and records the change in the audit log

    Renaming back to one of this workspace's own aliases reclaims it (the
    alias is deleted and the current name becomes the alias instead).
    """
    from django.core.exceptions import ValidationError

    old_slug = hostel.slug
    new_slug = clean_workspace_username(new_username)
    if new_slug == old_slug:
        raise ValidationError({"workspace_username": "That is already this workspace's username."})
    if not is_workspace_username_available(new_slug, exclude_pk=hostel.pk):
        raise ValidationError({"workspace_username": "This workspace username is already taken."})

    # Reclaiming one of our own retired names: drop that alias first.
    WorkspaceAlias.objects.filter(hostel=hostel, slug=new_slug).delete()

    # Keep the old URL alive forever (301) — and off the market.
    if old_slug:
        WorkspaceAlias.objects.get_or_create(hostel=hostel, slug=old_slug)

    # Hostel.save() deliberately restores the slug (permanence guard), so the
    # managed rename path writes through a queryset update instead.
    Hostel.objects.filter(pk=hostel.pk).update(slug=new_slug, updated_at=timezone.now())

    # Invalidate cached lookups under the OLD identity, then refresh.
    invalidate_tenant_cache(hostel)
    hostel.refresh_from_db()
    invalidate_tenant_cache(hostel)
    # Alias entries for both names may be cached (incl. negative results).
    invalidate_alias_cache(old_slug)
    invalidate_alias_cache(new_slug)

    _audit(hostel, actor, "update", "Workspace username changed",
           meta={"old": old_slug, "new": new_slug,
                 "old_url_redirects": True})
    return hostel


# --------------------------------------------------------------------------- #
# Lifecycle transitions
# --------------------------------------------------------------------------- #
def _transition(hostel: Hostel, actor, *, status=None, message="", extra_fields=None):
    fields = dict(extra_fields or {})
    if status is not None:
        hostel.status = status
        fields["status"] = status
    for attr, value in fields.items():
        setattr(hostel, attr, value)
    hostel.save(update_fields=list(fields) + ["updated_at"])
    invalidate_tenant_cache(hostel)
    _audit(hostel, actor, "update", message)
    return hostel


def activate_workspace(hostel, actor=None):
    return _transition(
        hostel, actor, status=WorkspaceStatus.ACTIVE, message="Workspace activated",
        extra_fields={"is_active": True},
    )


def suspend_workspace(hostel, actor=None, reason=""):
    hostel = _transition(
        hostel, actor, status=WorkspaceStatus.SUSPENDED, message="Workspace suspended",
    )
    if reason:
        _audit(hostel, actor, "update", f"Suspension reason: {reason}"[:255])
    return hostel


def archive_workspace(hostel, actor=None):
    return _transition(
        hostel, actor, status=WorkspaceStatus.ARCHIVED, message="Workspace archived",
        extra_fields={"is_active": False},
    )


def restore_workspace(hostel, actor=None):
    """Bring a suspended/archived/soft-deleted workspace back to active."""
    return _transition(
        hostel, actor, status=WorkspaceStatus.ACTIVE, message="Workspace restored",
        extra_fields={"is_active": True, "is_deleted": False, "deleted_at": None},
    )


def soft_delete_workspace(hostel, actor=None):
    """Soft delete: data stays, the workspace disappears from routing."""
    return _transition(
        hostel, actor, status=WorkspaceStatus.ARCHIVED, message="Workspace deleted (soft)",
        extra_fields={"is_active": False, "is_deleted": True, "deleted_at": timezone.now()},
    )
