"""PlatformAccountsView — the super-admin cross-tenant account directory."""
import pytest

URL = "/api/platform/accounts/"

pytestmark = pytest.mark.django_db


def test_superuser_sees_accounts_with_hostel_and_plan(superuser, owner, hostel, auth_client):
    resp = auth_client(superuser, hostel).get(URL)
    assert resp.status_code == 200
    payload = resp.json()
    row = next(r for r in payload["data"]["accounts"] if r["id"] == str(owner.id))

    assert row["username"] == owner.username
    assert row["role"] == "OWNER"
    assert len(row["memberships"]) == 1
    membership = row["memberships"][0]
    assert membership["hostel_id"] == str(hostel.id)
    assert membership["plan_name"] == hostel.plan_name


def test_consumer_accounts_are_excluded(superuser, make_user, hostel, auth_client):
    make_user(role="CONSUMER")
    resp = auth_client(superuser, hostel).get(URL)
    assert resp.status_code == 200
    assert all(r["role"] != "CONSUMER" for r in resp.json()["data"]["accounts"])


def test_search_filters_by_username(superuser, owner, hostel, auth_client):
    resp = auth_client(superuser, hostel).get(URL, {"search": owner.username})
    assert resp.status_code == 200
    results = resp.json()["data"]["accounts"]
    assert len(results) == 1
    assert results[0]["id"] == str(owner.id)


def test_tenant_owner_cannot_see_account_directory(owner, hostel, auth_client):
    resp = auth_client(owner, hostel).get(URL)
    assert resp.status_code == 403


def test_anonymous_denied(api):
    assert api.get(URL).status_code in (401, 403)
