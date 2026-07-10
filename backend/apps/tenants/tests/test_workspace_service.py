"""Workspace provisioning + lifecycle services."""
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import UserHostel
from apps.auditlog.models import AuditEvent
from apps.tenants import services
from apps.tenants.models import Hostel, WorkspaceStatus

pytestmark = pytest.mark.django_db


@pytest.fixture
def owner_user(make_user):
    return make_user(role="OWNER")


# --- Provisioning ------------------------------------------------------------
def test_provision_creates_complete_workspace(owner_user):
    hostel = services.provision_workspace(
        owner=owner_user, hostel_name="Everest International Hostel",
        workspace_username="everest",
    )
    assert hostel.slug == "everest"
    assert hostel.owner == owner_user
    assert hostel.status == WorkspaceStatus.TRIAL
    assert hostel.trial_ends_at is not None
    assert hostel.code.startswith("HTL-")
    # Owner membership link
    assert UserHostel.objects.filter(user=owner_user, hostel=hostel, is_active=True).exists()
    # Default settings / configuration seeded
    assert hostel.settings["roles"]
    assert hostel.settings["permission_groups"]
    # Initial audit/activity record
    assert AuditEvent.objects.filter(
        hostel_id=hostel.pk, action="create", entity_type="workspace"
    ).exists()
    # A default public website is scaffolded + published at creation, so the
    # workspace URL works immediately (Prompt 01 acceptance / Prompt 07 QA).
    assert hasattr(hostel, "website")
    assert hostel.website.is_published
    assert hostel.website.sections.exists()


def test_provision_autogenerates_username_from_name(owner_user):
    hostel = services.provision_workspace(
        owner=owner_user, hostel_name="Everest International Hostel"
    )
    assert hostel.slug == "everest-international-hostel"
    assert hostel.workspace_url.startswith("http")
    assert hostel.slug in hostel.workspace_url


def test_provision_rejects_taken_username(owner_user, make_user):
    services.provision_workspace(
        owner=owner_user, hostel_name="First", workspace_username="everest"
    )
    with pytest.raises(ValidationError):
        services.provision_workspace(
            owner=make_user(role="OWNER"), hostel_name="Second",
            workspace_username="everest",
        )


def test_provision_rejects_reserved_username(owner_user):
    with pytest.raises(ValidationError):
        services.provision_workspace(
            owner=owner_user, hostel_name="X", workspace_username="admin"
        )


def test_duplicate_slug_impossible_at_db_level(hostel):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Hostel.objects.create(name="Clone", slug=hostel.slug)


def test_provision_rolls_back_everything_on_failure(owner_user):
    """Transactionality: if any step fails, no tenant/link/audit survives."""
    before_hostels = Hostel.objects.count()
    with mock.patch(
        "apps.accounts.models.UserHostel.objects.create",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError):
            services.provision_workspace(
                owner=owner_user, hostel_name="Doomed", workspace_username="doomed"
            )
    assert Hostel.objects.count() == before_hostels
    assert not Hostel.objects.filter(slug="doomed").exists()
    assert not AuditEvent.objects.filter(message="Workspace created",
                                         meta__slug="doomed").exists()


def test_username_collision_gets_suffix(owner_user, make_user):
    a = services.provision_workspace(owner=owner_user, hostel_name="Sunrise")
    b = services.provision_workspace(owner=make_user(role="OWNER"), hostel_name="Sunrise")
    assert a.slug == "sunrise"
    assert b.slug != a.slug
    assert b.slug.startswith("sunrise")


# --- Slug permanence ---------------------------------------------------------
def test_workspace_username_is_permanent(hostel):
    original = hostel.slug
    hostel.slug = "sneaky-rename"
    hostel.name = "Renamed Hostel"
    hostel.save()
    hostel.refresh_from_db()
    assert hostel.slug == original          # slug restored
    assert hostel.name == "Renamed Hostel"  # display name freely editable


# --- Suggestions -------------------------------------------------------------
def test_suggestions_for_taken_username(owner_user):
    services.provision_workspace(
        owner=owner_user, hostel_name="Everest", workspace_username="everest"
    )
    suggestions = services.suggest_workspace_usernames("everest")
    assert suggestions
    assert "everest" not in suggestions
    for s in suggestions:
        assert services.is_workspace_username_available(s)


def test_suggestions_from_messy_input(db):
    suggestions = services.suggest_workspace_usernames("Ever est@!")
    assert suggestions  # still produces valid, available names


# --- Lifecycle ---------------------------------------------------------------
def test_lifecycle_transitions(hostel, owner):
    services.suspend_workspace(hostel, actor=owner, reason="non-payment")
    hostel.refresh_from_db()
    assert hostel.status == WorkspaceStatus.SUSPENDED
    assert not hostel.is_operational

    services.activate_workspace(hostel, actor=owner)
    hostel.refresh_from_db()
    assert hostel.status == WorkspaceStatus.ACTIVE
    assert hostel.is_operational

    services.archive_workspace(hostel, actor=owner)
    hostel.refresh_from_db()
    assert hostel.status == WorkspaceStatus.ARCHIVED
    assert hostel.is_archived and not hostel.is_active

    services.restore_workspace(hostel, actor=owner)
    hostel.refresh_from_db()
    assert hostel.status == WorkspaceStatus.ACTIVE
    assert hostel.is_active and not hostel.is_deleted


def test_soft_delete_preserves_data(hostel, owner, resident):
    services.soft_delete_workspace(hostel, actor=owner)
    hostel.refresh_from_db()
    assert hostel.is_deleted and hostel.deleted_at is not None
    # Data is never physically removed.
    assert Hostel.objects.filter(pk=hostel.pk).exists()
    resident.refresh_from_db()  # child rows untouched


def test_lifecycle_writes_audit_trail(hostel, owner):
    services.suspend_workspace(hostel, actor=owner)
    assert AuditEvent.objects.filter(
        hostel_id=hostel.pk, entity_type="workspace", message="Workspace suspended"
    ).exists()
