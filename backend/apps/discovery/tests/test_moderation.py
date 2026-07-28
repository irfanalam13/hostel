"""Tenant-staff moderation queue (approve/reject pending reviews, owner
replies) and the platform-side flagged queue (unflag/remove)."""
import pytest

from apps.discovery.models import Review, ReviewFlag

pytestmark = pytest.mark.django_db

PENDING_URL = "/api/discovery/moderation/pending/"


def _pending_review(hostel, author):
    return Review.objects.create(hostel=hostel, author=author, rating=3, body="Needs a look.")


def _data(resp):
    body = resp.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


def test_manager_can_see_and_approve_pending_review(api, auth_client, manager, hostel, consumer_user):
    review = _pending_review(hostel, consumer_user)
    client = auth_client(manager, hostel)

    listed = client.get(PENDING_URL)
    assert listed.status_code == 200, listed.content
    assert any(r["id"] == str(review.id) for r in _data(listed))

    approve = client.post(f"/api/discovery/moderation/reviews/{review.id}/approve/")
    assert approve.status_code == 200, approve.content
    review.refresh_from_db()
    assert review.status == Review.Status.PUBLISHED
    assert review.verification_method == Review.VerificationMethod.STAFF_APPROVED
    assert review.verified_by_id == manager.id


def test_manager_can_reject_pending_review(api, auth_client, manager, hostel, consumer_user):
    review = _pending_review(hostel, consumer_user)
    client = auth_client(manager, hostel)

    resp = client.post(f"/api/discovery/moderation/reviews/{review.id}/reject/")
    assert resp.status_code == 200, resp.content
    review.refresh_from_db()
    assert review.status == Review.Status.REJECTED


def test_staff_cannot_moderate_another_hostels_review(
    api, auth_client, manager, hostel, other_hostel, consumer_user
):
    review = _pending_review(other_hostel, consumer_user)
    client = auth_client(manager, hostel)

    resp = client.post(f"/api/discovery/moderation/reviews/{review.id}/approve/")
    assert resp.status_code == 404


def test_role_without_moderate_permission_is_forbidden(api, auth_client, hostel, consumer_user, make_user):
    _pending_review(hostel, consumer_user)
    staff = make_user(role="STAFF", hostel=hostel)
    client = auth_client(staff, hostel)

    resp = client.get(PENDING_URL)
    assert resp.status_code == 403


def test_owner_can_respond_to_a_review(api, auth_client, owner, hostel, consumer_user):
    review = Review.objects.create(
        hostel=hostel, author=consumer_user, rating=5, body="Loved it.",
        status=Review.Status.PUBLISHED,
    )
    client = auth_client(owner, hostel)

    resp = client.post(f"/api/discovery/reviews/{review.id}/respond/", {"body": "Thanks for staying!"})
    assert resp.status_code == 200, resp.content
    review.refresh_from_db()
    assert review.owner_response.body == "Thanks for staying!"
    assert review.owner_response.responded_by_id == owner.id


def test_platform_admin_can_see_and_unflag(api, auth_client, superuser, hostel, consumer_user, platform_hostel):
    review = Review.objects.create(
        hostel=hostel, author=consumer_user, rating=1, body="Bad.",
        status=Review.Status.FLAGGED, flag_count=3,
    )
    ReviewFlag.objects.create(review=review, reason=ReviewFlag.Reason.SPAM, status=ReviewFlag.Status.OPEN)
    client = auth_client(superuser, platform_hostel)

    listed = client.get("/api/platform/discovery/flagged/")
    assert listed.status_code == 200, listed.content
    assert any(r["id"] == str(review.id) for r in _data(listed))

    unflag = client.post(f"/api/platform/discovery/reviews/{review.id}/unflag/")
    assert unflag.status_code == 200, unflag.content
    review.refresh_from_db()
    assert review.status == Review.Status.PUBLISHED
    assert review.flag_count == 0
    assert not review.flags.filter(status=ReviewFlag.Status.OPEN).exists()


def test_platform_admin_can_remove_a_review(api, auth_client, superuser, hostel, consumer_user, platform_hostel):
    review = Review.objects.create(
        hostel=hostel, author=consumer_user, rating=1, body="Bad.", status=Review.Status.FLAGGED,
    )
    client = auth_client(superuser, platform_hostel)

    resp = client.post(f"/api/platform/discovery/reviews/{review.id}/remove/")
    assert resp.status_code == 200, resp.content
    review.refresh_from_db()
    assert review.status == Review.Status.REMOVED


def test_non_superuser_cannot_access_platform_queue(api, auth_client, owner, hostel):
    client = auth_client(owner, hostel)
    resp = client.get("/api/platform/discovery/flagged/")
    assert resp.status_code == 403
