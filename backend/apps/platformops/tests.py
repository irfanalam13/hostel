"""Phase 11 — operations governance: feature flags, maintenance, incidents."""
import pytest
from django.utils import timezone

from apps.auditlog.models import AuditEvent
from apps.platformops import flags, services
from apps.platformops.models import (
    Announcement,
    Audience,
    FeatureFlag,
    FeatureFlagOverride,
    Incident,
    MaintenanceWindow,
)

# --------------------------------------------------------------------------- #
# Feature-flag engine
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_flag_missing_is_false():
    assert flags.is_enabled("does-not-exist") is False


@pytest.mark.django_db
def test_kill_switch_forces_off():
    FeatureFlag.objects.create(key="f", is_active=True, rollout_percentage=100, kill=True)
    assert flags.is_enabled("f") is False


@pytest.mark.django_db
def test_rollout_bounds():
    FeatureFlag.objects.create(key="all", is_active=True, rollout_percentage=100)
    FeatureFlag.objects.create(key="none", is_active=True, rollout_percentage=0)
    assert flags.is_enabled("all") is True
    assert flags.is_enabled("none") is False


@pytest.mark.django_db
def test_inactive_flag_off_even_with_rollout():
    FeatureFlag.objects.create(key="f", is_active=False, rollout_percentage=100)
    assert flags.is_enabled("f") is False


@pytest.mark.django_db
def test_hostel_targeting(hostel, other_hostel):
    FeatureFlag.objects.create(
        key="f", is_active=True, rollout_percentage=100,
        allowed_hostels=[str(hostel.id)],
    )
    assert flags.is_enabled("f", hostel=hostel) is True
    assert flags.is_enabled("f", hostel=other_hostel) is False


@pytest.mark.django_db
def test_blocked_hostel_wins(hostel):
    FeatureFlag.objects.create(
        key="f", is_active=True, rollout_percentage=100,
        blocked_hostels=[str(hostel.id)],
    )
    assert flags.is_enabled("f", hostel=hostel) is False


@pytest.mark.django_db
def test_override_beats_everything(hostel):
    flag = FeatureFlag.objects.create(key="f", is_active=False, rollout_percentage=0)
    FeatureFlagOverride.objects.create(flag=flag, hostel_id=hostel.id, enabled=True)
    assert flags.is_enabled("f", hostel=hostel) is True


@pytest.mark.django_db
def test_expired_override_ignored(hostel):
    flag = FeatureFlag.objects.create(key="f", is_active=True, rollout_percentage=100)
    FeatureFlagOverride.objects.create(
        flag=flag, hostel_id=hostel.id, enabled=False,
        expires_at=timezone.now() - timezone.timedelta(hours=1),
    )
    # expired disable override is ignored -> falls through to active+rollout
    assert flags.is_enabled("f", hostel=hostel) is True


@pytest.mark.django_db
def test_scheduled_override_not_live_until_start(hostel):
    flag = FeatureFlag.objects.create(key="f", is_active=False)
    FeatureFlagOverride.objects.create(
        flag=flag, hostel_id=hostel.id, enabled=True,
        starts_at=timezone.now() + timezone.timedelta(hours=1),
    )
    # scheduled for the future -> not applied yet
    assert flags.is_enabled("f", hostel=hostel) is False


@pytest.mark.django_db
def test_revoked_override_not_applied(hostel):
    flag = FeatureFlag.objects.create(key="f", is_active=False)
    FeatureFlagOverride.objects.create(
        flag=flag, hostel_id=hostel.id, enabled=True, is_active=False,
    )
    assert flags.is_enabled("f", hostel=hostel) is False


@pytest.mark.django_db
def test_reap_expired_overrides(hostel):
    flag = FeatureFlag.objects.create(key="f", is_active=True)
    FeatureFlagOverride.objects.create(
        flag=flag, hostel_id=hostel.id,
        expires_at=timezone.now() - timezone.timedelta(minutes=1),
    )
    FeatureFlagOverride.objects.create(flag=flag, hostel_id=hostel.id)  # no expiry
    assert services.reap_expired_overrides()["deleted"] == 1
    assert FeatureFlagOverride.objects.count() == 1


# --------------------------------------------------------------------------- #
# Maintenance windows -> DR integration
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_maintenance_flips_dr_mode(superuser):
    from apps.backups import dr
    from apps.backups.models import DRMode

    window = MaintenanceWindow.objects.create(
        title="db upgrade", scheduled_start=timezone.now(),
        scheduled_end=timezone.now() + timezone.timedelta(hours=1),
        enforce_read_only=True,
    )
    services.start_maintenance(window, user=superuser)
    assert dr.get_mode() == DRMode.MAINTENANCE
    services.complete_maintenance(window, user=superuser)
    assert dr.get_mode() == DRMode.NORMAL
    window.refresh_from_db()
    assert window.status == MaintenanceWindow.Status.COMPLETED


# --------------------------------------------------------------------------- #
# Operator API (super-admin only) + audit
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_flag_api_requires_superuser(auth_client, owner, hostel):
    client = auth_client(owner, hostel=hostel)
    resp = client.get("/api/platform/ops/feature-flags/", HTTP_X_HOSTEL_CODE=hostel.code)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_superuser_creates_flag_and_audits(auth_client, make_user, hostel):
    su = make_user(role="ADMIN", is_superuser=True, hostel=hostel)
    client = auth_client(su, hostel=hostel)
    resp = client.post("/api/platform/ops/feature-flags/",
                       {"key": "beta-ui", "is_active": True, "rollout_percentage": 50},
                       format="json", HTTP_X_HOSTEL_CODE=hostel.code)
    assert resp.status_code == 201, resp.content
    assert FeatureFlag.objects.filter(key="beta-ui").exists()
    assert AuditEvent.objects.filter(
        action=AuditEvent.Action.FEATURE_FLAG, entity_type="feature_flag"
    ).exists()


@pytest.mark.django_db
def test_incident_update_transitions_and_timelines(auth_client, make_user, hostel):
    su = make_user(role="ADMIN", is_superuser=True, hostel=hostel)
    client = auth_client(su, hostel=hostel)
    created = client.post("/api/platform/ops/incidents/",
                          {"title": "API down", "severity": "sev1", "is_public": True},
                          format="json", HTTP_X_HOSTEL_CODE=hostel.code)
    assert created.status_code == 201, created.content
    payload = created.json()
    incident_id = payload.get("data", payload)["id"]

    resp = client.post(f"/api/platform/ops/incidents/{incident_id}/updates/",
                       {"status": "resolved", "message": "fixed"}, format="json",
                       HTTP_X_HOSTEL_CODE=hostel.code)
    assert resp.status_code == 201, resp.content

    incident = Incident.objects.get(pk=incident_id)
    assert incident.status == Incident.Status.RESOLVED
    assert incident.resolved_at is not None
    # opening entry + resolved entry
    assert incident.updates.count() == 2


# --------------------------------------------------------------------------- #
# Status feed
# --------------------------------------------------------------------------- #

@pytest.mark.django_db
def test_override_builder_flow(auth_client, make_user, hostel):
    su = make_user(role="ADMIN", is_superuser=True, hostel=hostel)
    client = auth_client(su, hostel=hostel)
    flag = FeatureFlag.objects.create(key="beta", is_active=False)

    # create override targeting a tenant, with a scheduling window
    created = client.post(
        "/api/platform/ops/overrides/",
        {
            "flag": str(flag.id),
            "hostel_id": str(hostel.id),
            "enabled": True,
            "reason": "pilot",
            "expires_at": (timezone.now() + timezone.timedelta(days=7)).isoformat(),
        },
        format="json", HTTP_X_HOSTEL_CODE=hostel.code,
    )
    assert created.status_code == 201, created.content
    body = created.json()
    ov = body.get("data", body)
    assert ov["schedule_state"] == "active"
    assert ov["hostel_label"]
    override_id = ov["id"]
    assert flags.is_enabled("beta", hostel=hostel) is True

    # list filtered by flag
    listed = client.get(f"/api/platform/ops/overrides/?flag={flag.id}",
                        HTTP_X_HOSTEL_CODE=hostel.code)
    assert listed.status_code == 200

    # revoke -> no longer applied, record kept, audited
    revoked = client.post(f"/api/platform/ops/overrides/{override_id}/revoke/",
                         HTTP_X_HOSTEL_CODE=hostel.code)
    assert revoked.status_code == 200
    assert FeatureFlagOverride.objects.filter(id=override_id, is_active=False).exists()
    assert flags.is_enabled("beta", hostel=hostel) is False
    assert AuditEvent.objects.filter(
        action=AuditEvent.Action.FEATURE_FLAG, entity_type="feature_flag_override"
    ).exists()


@pytest.mark.django_db
def test_override_requires_target(auth_client, make_user, hostel):
    su = make_user(role="ADMIN", is_superuser=True, hostel=hostel)
    client = auth_client(su, hostel=hostel)
    flag = FeatureFlag.objects.create(key="beta")
    resp = client.post("/api/platform/ops/overrides/", {"flag": str(flag.id), "enabled": True},
                       format="json", HTTP_X_HOSTEL_CODE=hostel.code)
    assert resp.status_code == 400


@pytest.mark.django_db
def test_lookups_superuser_only(auth_client, make_user, owner, hostel):
    su = make_user(role="ADMIN", is_superuser=True, hostel=hostel)
    assert auth_client(owner, hostel=hostel).get(
        "/api/platform/ops/lookup/hostels/", HTTP_X_HOSTEL_CODE=hostel.code
    ).status_code == 403

    resp = auth_client(su, hostel=hostel).get(
        "/api/platform/ops/lookup/hostels/", {"q": hostel.name[:3]}, HTTP_X_HOSTEL_CODE=hostel.code
    )
    assert resp.status_code == 200
    data = resp.json()
    results = data.get("data", data)["results"]
    assert any(r["id"] == str(hostel.id) for r in results)

    users = auth_client(su, hostel=hostel).get(
        "/api/platform/ops/lookup/users/", {"q": su.email[:4]}, HTTP_X_HOSTEL_CODE=hostel.code
    )
    assert users.status_code == 200


@pytest.mark.django_db
def test_status_feed_filters_audience_and_resolves_flags(auth_client, owner, hostel):
    Announcement.objects.create(title="everyone", audience=Audience.ALL, is_active=True)
    Announcement.objects.create(title="admins-only", audience=Audience.ADMINS, is_active=True)
    FeatureFlag.objects.create(key="on", is_active=True, rollout_percentage=100)

    client = auth_client(owner, hostel=hostel)
    resp = client.get("/api/ops/status/", HTTP_X_HOSTEL_CODE=hostel.code)
    assert resp.status_code == 200, resp.content
    body = resp.json()
    data = body.get("data", body)
    titles = {a["title"] for a in data["announcements"]}
    # OWNER is an admin bucket -> sees both
    assert "everyone" in titles and "admins-only" in titles
    assert data["flags"]["on"] is True
