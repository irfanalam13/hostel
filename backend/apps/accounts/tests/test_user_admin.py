"""Admin user management (UserViewSet, UserHostelViewSet).

Role-gate behaviour (owner-only, superuser override) is already covered by
apps/common/tests/test_rbac.py — these tests focus on CRUD correctness and
hostel-scoping instead: queryset isolation, auto-linking on create, validation,
partial updates, and cross-hostel object access (404, not just 403).
"""
import pytest

from apps.accounts.models import UserHostel

USERS = "/api/auth/users/"
USER_HOSTELS = "/api/auth/user-hostels/"

pytestmark = pytest.mark.django_db


def _items(resp):
    data = resp.data
    return data["results"] if isinstance(data, dict) and "results" in data else data


def test_owner_user_list_excludes_other_hostels(auth_client, owner, hostel, other_hostel, make_user):
    make_user(role="WARDEN", hostel=other_hostel, username="foreignstaff")

    resp = auth_client(owner, hostel).get(USERS)
    assert resp.status_code == 200
    usernames = [u["username"] for u in _items(resp)]
    assert "foreignstaff" not in usernames
    assert owner.username in usernames


def test_superuser_user_list_includes_all_hostels(auth_client, superuser, hostel, other_hostel, make_user):
    make_user(role="WARDEN", hostel=hostel, username="staffa")
    make_user(role="WARDEN", hostel=other_hostel, username="staffb")

    resp = auth_client(superuser, hostel).get(USERS)
    assert resp.status_code == 200
    usernames = [u["username"] for u in _items(resp)]
    assert "staffa" in usernames
    assert "staffb" in usernames


def test_owner_create_user_auto_links_to_request_hostel(auth_client, owner, hostel):
    resp = auth_client(owner, hostel).post(
        USERS,
        {
            "username": "newstaff",
            "email": "newstaff@example.com",
            "password": "StrongPass!234",
            "role": "WARDEN",
            "first_name": "N",
        },
    )
    assert resp.status_code == 201
    assert UserHostel.objects.filter(
        user__username="newstaff", hostel=hostel, is_active=True
    ).exists()


def test_create_user_rejects_short_password(auth_client, owner, hostel):
    resp = auth_client(owner, hostel).post(
        USERS,
        {
            "username": "shortpw",
            "email": "shortpw@example.com",
            "password": "short",
            "role": "WARDEN",
        },
    )
    assert resp.status_code == 400


def test_owner_partial_update_changes_role(auth_client, owner, hostel, warden):
    resp = auth_client(owner, hostel).patch(f"{USERS}{warden.id}/", {"role": "MANAGER"})
    assert resp.status_code == 200
    warden.refresh_from_db()
    assert warden.role == "MANAGER"


def test_owner_cannot_reach_user_in_other_hostel_via_url(auth_client, owner, hostel, other_hostel, make_user):
    foreign_user = make_user(role="WARDEN", hostel=other_hostel)

    resp = auth_client(owner, hostel).patch(f"{USERS}{foreign_user.id}/", {"role": "OWNER"})
    assert resp.status_code == 404


def test_owner_can_list_user_hostel_links_scoped_to_hostel(auth_client, owner, hostel, other_hostel, make_user):
    make_user(role="WARDEN", hostel=other_hostel)

    resp = auth_client(owner, hostel).get(USER_HOSTELS)
    assert resp.status_code == 200
    hostel_ids = {link["hostel"] for link in _items(resp)}
    assert hostel_ids == {hostel.id}


def test_owner_can_create_user_hostel_link(auth_client, owner, hostel, make_user):
    existing_user = make_user(role="WARDEN")  # not yet linked to `hostel`

    resp = auth_client(owner, hostel).post(
        USER_HOSTELS, {"user": existing_user.id, "hostel": str(hostel.id), "is_active": True}
    )
    assert resp.status_code == 201


def test_superuser_sees_all_user_hostel_links(auth_client, superuser, hostel, other_hostel, make_user):
    make_user(role="WARDEN", hostel=hostel)
    make_user(role="WARDEN", hostel=other_hostel)

    resp = auth_client(superuser, hostel).get(USER_HOSTELS)
    assert resp.status_code == 200
    hostel_ids = {link["hostel"] for link in _items(resp)}
    assert hostel.id in hostel_ids
    assert other_hostel.id in hostel_ids
