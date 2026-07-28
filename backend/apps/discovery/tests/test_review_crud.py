"""Consumer-facing review CRUD: create (with verification), update, delete,
flag — and the auth/eligibility boundaries around them."""
import pytest

from apps.discovery.models import Review, ReviewFlag
from conftest import ResidentFactory

pytestmark = pytest.mark.django_db

REVIEWS_URL = "/api/discovery/reviews/"


def _data(resp):
    body = resp.json()
    return body["data"] if isinstance(body, dict) and "data" in body else body


def test_anonymous_cannot_create_review(api, published_hostel):
    resp = api.post(REVIEWS_URL, {"hostel": published_hostel.slug, "rating": 5, "body": "Nice."})
    assert resp.status_code == 401


def test_verified_consumer_review_auto_publishes(api, published_hostel, consumer_client, consumer_user):
    ResidentFactory(hostel=published_hostel, phone="9800011122", full_name="Aashish Karki")
    resp = consumer_client.post(
        REVIEWS_URL, {"hostel": published_hostel.slug, "rating": 5, "title": "Loved it", "body": "Great stay."}
    )
    assert resp.status_code == 201, resp.content
    data = _data(resp)
    assert data["status"] == "published"

    review = Review.objects.get(hostel=published_hostel, author=consumer_user)
    assert review.status == Review.Status.PUBLISHED
    assert review.verification_method == Review.VerificationMethod.AUTO_PHONE_MATCH


def test_unverified_consumer_review_stays_pending(api, published_hostel, consumer_client, consumer_user):
    resp = consumer_client.post(
        REVIEWS_URL, {"hostel": published_hostel.slug, "rating": 4, "body": "Decent."}
    )
    assert resp.status_code == 201, resp.content
    review = Review.objects.get(hostel=published_hostel, author=consumer_user)
    assert review.status == Review.Status.PENDING


def test_cannot_review_the_same_hostel_twice(api, published_hostel, consumer_client):
    ResidentFactory(hostel=published_hostel, phone="9800011122")
    body = {"hostel": published_hostel.slug, "rating": 5, "body": "First."}
    first = consumer_client.post(REVIEWS_URL, body)
    assert first.status_code == 201, first.content

    second = consumer_client.post(REVIEWS_URL, {**body, "body": "Second."})
    assert second.status_code == 400


def test_cannot_review_an_unlisted_hostel(api, hostel, consumer_client):
    # `hostel` has no published website — not in visible_hostels_queryset().
    resp = consumer_client.post(REVIEWS_URL, {"hostel": hostel.slug, "rating": 5, "body": "..."})
    assert resp.status_code == 400


def test_rating_out_of_range_rejected(api, published_hostel, consumer_client):
    resp = consumer_client.post(
        REVIEWS_URL, {"hostel": published_hostel.slug, "rating": 6, "body": "Too high."}
    )
    assert resp.status_code == 400


def test_author_can_update_own_review(api, published_hostel, consumer_client, consumer_user):
    ResidentFactory(hostel=published_hostel, phone="9800011122")
    create = consumer_client.post(
        REVIEWS_URL, {"hostel": published_hostel.slug, "rating": 5, "body": "Original."}
    )
    review_id = _data(create)["id"]

    resp = consumer_client.patch(f"{REVIEWS_URL}{review_id}/", {"rating": 3, "body": "Updated."})
    assert resp.status_code == 200, resp.content
    review = Review.objects.get(pk=review_id)
    assert review.rating == 3
    assert review.body == "Updated."
    assert review.edit_count == 1


def test_non_author_cannot_update_review(api, published_hostel, consumer_client, make_user, platform_hostel):
    from apps.discovery.models import ConsumerProfile
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    ResidentFactory(hostel=published_hostel, phone="9800011122")
    create = consumer_client.post(
        REVIEWS_URL, {"hostel": published_hostel.slug, "rating": 5, "body": "Mine."}
    )
    review_id = _data(create)["id"]

    other = make_user(role="CONSUMER", hostel=platform_hostel)
    ConsumerProfile.objects.create(user=other, full_name="Someone Else", phone="9822233344")
    other_client = APIClient()
    refresh = RefreshToken.for_user(other)
    refresh["hostel_id"] = str(platform_hostel.id)
    refresh["hostel_code"] = platform_hostel.code
    refresh["role"] = "CONSUMER"
    other_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")

    resp = other_client.patch(f"{REVIEWS_URL}{review_id}/", {"rating": 1, "body": "Hijacked."})
    assert resp.status_code == 403


def test_author_can_delete_own_review(api, published_hostel, consumer_client):
    ResidentFactory(hostel=published_hostel, phone="9800011122")
    create = consumer_client.post(
        REVIEWS_URL, {"hostel": published_hostel.slug, "rating": 5, "body": "Delete me."}
    )
    review_id = _data(create)["id"]

    resp = consumer_client.delete(f"{REVIEWS_URL}{review_id}/")
    assert resp.status_code == 204
    assert not Review.objects.filter(pk=review_id).exists()


def test_delete_then_resubmit_is_allowed(api, published_hostel, consumer_client):
    ResidentFactory(hostel=published_hostel, phone="9800011122")
    body = {"hostel": published_hostel.slug, "rating": 5, "body": "First try."}
    first = consumer_client.post(REVIEWS_URL, body)
    review_id = _data(first)["id"]
    consumer_client.delete(f"{REVIEWS_URL}{review_id}/")

    second = consumer_client.post(REVIEWS_URL, {**body, "body": "Second try."})
    assert second.status_code == 201, second.content


def test_flag_a_review(api, published_hostel, consumer_client):
    ResidentFactory(hostel=published_hostel, phone="9800011122")
    create = consumer_client.post(
        REVIEWS_URL, {"hostel": published_hostel.slug, "rating": 1, "body": "Spammy."}
    )
    review_id = _data(create)["id"]

    resp = consumer_client.post(f"{REVIEWS_URL}{review_id}/flag/", {"reason": "spam", "note": ""})
    assert resp.status_code == 201, resp.content
    assert ReviewFlag.objects.filter(review_id=review_id, reason="spam").exists()


def test_mine_returns_404_when_no_review_yet(api, published_hostel, consumer_client):
    resp = consumer_client.get(f"{REVIEWS_URL}mine/", {"hostel": published_hostel.slug})
    assert resp.status_code == 404


def test_mine_returns_pending_review_with_status(api, published_hostel, consumer_client):
    create = consumer_client.post(
        REVIEWS_URL, {"hostel": published_hostel.slug, "rating": 4, "body": "Unverified."}
    )
    assert create.status_code == 201, create.content

    resp = consumer_client.get(f"{REVIEWS_URL}mine/", {"hostel": published_hostel.slug})
    assert resp.status_code == 200, resp.content
    data = _data(resp)
    assert data["status"] == "pending"


def test_mine_requires_hostel_param(api, consumer_client):
    resp = consumer_client.get(f"{REVIEWS_URL}mine/")
    assert resp.status_code == 400


def test_review_auto_flags_at_threshold(api, published_hostel, consumer_client, make_user, platform_hostel):
    from apps.discovery.models import ConsumerProfile
    from rest_framework.test import APIClient
    from rest_framework_simplejwt.tokens import RefreshToken

    ResidentFactory(hostel=published_hostel, phone="9800011122")
    create = consumer_client.post(
        REVIEWS_URL, {"hostel": published_hostel.slug, "rating": 1, "body": "Under fire."}
    )
    review_id = _data(create)["id"]

    for i in range(3):
        reporter = make_user(role="CONSUMER", hostel=platform_hostel, username=f"reporter{i}")
        ConsumerProfile.objects.create(user=reporter, full_name=f"Reporter {i}", phone=f"98111000{i:02d}")
        client = APIClient()
        refresh = RefreshToken.for_user(reporter)
        refresh["hostel_id"] = str(platform_hostel.id)
        refresh["hostel_code"] = platform_hostel.code
        refresh["role"] = "CONSUMER"
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
        resp = client.post(f"{REVIEWS_URL}{review_id}/flag/", {"reason": "fake"})
        assert resp.status_code == 201

    review = Review.objects.get(pk=review_id)
    assert review.flag_count == 3
    assert review.status == Review.Status.FLAGGED
