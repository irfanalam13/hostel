"""Role-based access control across the canonical endpoints.

Roles: ADMIN/OWNER, MANAGER, ACCOUNTANT, WARDEN/STAFF, RESIDENT.

Covered (Phase 10 §2):
  * each role reaching allowed endpoints
  * each role blocked from restricted endpoints
  * admin (superuser) override
"""
import pytest

RESIDENTS = "/api/residents/"
DASH_SUMMARY = "/api/billing/dashboard/summary/"
USERS = "/api/auth/users/"

pytestmark = pytest.mark.django_db


# --- IsStaff: residents endpoint -------------------------------------------
@pytest.mark.parametrize("role", ["OWNER", "MANAGER", "ACCOUNTANT", "WARDEN", "STAFF"])
def test_staff_roles_can_list_residents(api, auth_client, make_user, hostel, role):
    user = make_user(role=role, hostel=hostel)
    resp = auth_client(user, hostel).get(RESIDENTS)
    assert resp.status_code == 200


def test_resident_role_blocked_from_residents_endpoint(auth_client, resident_user, hostel):
    # A RESIDENT is a hostel member but not staff -> IsStaff denies.
    resp = auth_client(resident_user, hostel).get(RESIDENTS)
    assert resp.status_code == 403


def test_resident_role_cannot_create_resident(auth_client, resident_user, hostel):
    resp = auth_client(resident_user, hostel).post(RESIDENTS, {"full_name": "X"})
    assert resp.status_code == 403


# --- IsOwnerOrManager: billing dashboard -----------------------------------
@pytest.mark.parametrize("role", ["OWNER", "MANAGER"])
def test_owner_manager_see_dashboard(auth_client, make_user, hostel, role):
    user = make_user(role=role, hostel=hostel)
    assert auth_client(user, hostel).get(DASH_SUMMARY).status_code == 200


@pytest.mark.parametrize("role", ["ACCOUNTANT", "WARDEN", "RESIDENT"])
def test_lower_roles_blocked_from_dashboard(auth_client, make_user, hostel, role):
    user = make_user(role=role, hostel=hostel)
    assert auth_client(user, hostel).get(DASH_SUMMARY).status_code == 403


# --- IsOwner: user administration ------------------------------------------
def test_owner_can_list_users(auth_client, owner, hostel):
    assert auth_client(owner, hostel).get(USERS).status_code == 200


@pytest.mark.parametrize("role", ["MANAGER", "ACCOUNTANT", "WARDEN", "RESIDENT"])
def test_non_owner_cannot_list_users(auth_client, make_user, hostel, role):
    user = make_user(role=role, hostel=hostel)
    assert auth_client(user, hostel).get(USERS).status_code == 403


# --- superuser override -----------------------------------------------------
def test_superuser_overrides_membership_and_role(auth_client, superuser, hostel):
    # Not linked to the hostel and role=ADMIN, but is_superuser bypasses the
    # membership guard and satisfies IsOwner.
    client = auth_client(superuser, hostel)
    assert client.get(RESIDENTS).status_code == 200
    assert client.get(USERS).status_code == 200
